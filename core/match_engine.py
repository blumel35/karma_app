"""
core/match_engine.py
─────────────────────────────────────────────────────────────────────────
Alıcı Talebi → Portföy eşleşme motoru (MVP).

Bu modül SADECE tek yönlü çalışır: bir alıcı talebi verildiğinde, uygun
portföyleri bulur, puanlar ve gerekçeleriyle döner. Ters yön (Portföy →
Alıcı) bilinçli olarak bu sürümde YOK — sonraki aşamada aynı motorun
aynası olarak eklenecek.

── METODOLOJİ (bu dosyayı değiştirirken bu kararları bozma) ──────────────
1. Uyum Skoru ≠ Fırsat Önceliği. Kapalı/linksiz olmak skoru ARTIRMAZ,
   sadece sonuç sıralamasında öne alır.
2. Hard filter: işlem tipi ve mülk tipi uyumsuzsa kayıt TAMAMEN elenir.
   AMA taraflardan biri "Belirsiz"/boş ise ELENMEZ — gerekçeye not düşülür.
   Mail'den gelen veride "Belirsiz" çok sık olduğu için sessizce eleme
   yapmak yanlış kararlar doğurur.
3. mulk_tipi eş anlamlıları: gerçek veride portfoyler.mulk_tipi bazen
   "İşyeri" bazen "Ticari" olarak giriliyor (AYNI TABLODA, tutarsız).
   Bu ikisi normalize edilmeden karşılaştırılırsa işyeri taleplerinin
   büyük kısmı sessizce elenir. _mulk_normalize() bunu düzeltir.
4. SADECE aktif=true portföyler değerlendirilir. Pasif/ilandan kalkmış
   kayıtlar (aktif=false) bu MVP'nin KAPSAMI DIŞINDA — çünkü Supabase
   şemasında pasife düşme SEBEBİNİ tutan bir alan yok (satıldı mı,
   yetki mi bitti, fiyat revizyonu mu — ayırt edemiyoruz). Bunları
   "fırsat sinyali" gibi göstermek yanlış güven yaratır. İleride ayrı
   bir "İlan Hafızası / Pasif Fırsat Kontrolü" modülü olarak ele alınacak.
5. ilceler gerçek bir Postgres text[] — Supabase client bunu zaten
   Python listesi olarak döndürür, JSON/string parse GEREKMEZ.
   AMA portfoyler.ilceler pratikte neredeyse hep boş []! Lokasyon
   eşleşmesinde portföy tarafı için SADECE portfoy.ilce kullanılır,
   talep tarafı için talep.ilceler (liste) + talep.ilce birlikte.
6. oda_sayisi_m2 ve max_butce/fiyat serbest metin — regex ile SADECE
   net desenler kabul edilir (örn. "3+1", "120 m²"). Çıplak bir sayı
   ("100" gibi) m² SAYILMAZ — geçmişte "100 kiralık konut" gibi hatalı
   yorumlara yol açtığı için bilinçli olarak sıkı tutuluyor.
7. Parser bir alanı çözemezse HATA FIRLATMAZ — o bileşen için "veri yok"
   puanına düşer. Kirli veri normal kabul edilir, motoru çökertmez.

── KULLANIM ──────────────────────────────────────────────────────────────
    from core.match_engine import eslesen_portfoyleri_bul

    sonuclar = eslesen_portfoyleri_bul(talep_dict, portfoy_listesi)
    for s in sonuclar:
        print(s["skor"], s["seviye"], s["grup"], s["gerekce"])
        print(s["portfoy"]["ozet"])
"""

import re

# ─────────────────────────────────────────────────────────────────────────
# NORMALİZASYON YARDIMCILARI
# ─────────────────────────────────────────────────────────────────────────

def _lower_tr(deger):
    """Python'ın standart .lower()'ı Türkçe büyük İ/I harflerini yanlış
    küçültebiliyor (birleşik karakter sorunu) — bu yüzden elle çeviriyoruz."""
    s = (deger or "").strip()
    return s.replace("İ", "i").replace("I", "ı").lower().strip()


_ISLEM_ESANLAM = {
    "satılık": "satilik",
    "satilik": "satilik",
    "kiralık": "kiralik",
    "kiralik": "kiralik",
    "belirsiz": "belirsiz",
}

# Gerçek veride portfoyler.mulk_tipi tutarsız: bazı kayıtlar "İşyeri",
# bazıları (AYNI TABLODA) "Ticari" olarak girilmiş. İkisi de aynı kavramı
# (konut dışı ticari gayrimenkul) ifade ediyor — normalize edilmezse
# hard filter bunları birbirinden farklı sayıp yanlışlıkla eler.
_MULK_ESANLAM = {
    "konut": "konut",
    "arsa": "arsa",
    "işyeri": "isyeri",
    "isyeri": "isyeri",
    "ticari": "isyeri",
}


def _mulk_normalize(deger):
    d = _lower_tr(deger)
    return _MULK_ESANLAM.get(d, d)


def _islem_normalize(deger):
    d = _lower_tr(deger)
    return _ISLEM_ESANLAM.get(d, d)


def _belirsiz_mi(deger):
    d = (deger or "").strip().lower()
    return d in ("", "belirsiz", "fark etmez", "farketmez")


def _sayi_ayikla(metin):
    """'22.000.000 TL', '32000TL', '9.900.000₺ (110.000₺/m2)', '10-15 milyon'
    gibi kirli metinlerden İLK anlamlı büyük sayıyı çıkarır.
    Parse edilemezse None döner (hata fırlatmaz — 'milyon/bin' gibi
    kelime-bazlı ifadeler MVP'de bilinçli olarak desteklenmiyor,
    bunlar 'veri yok' puanına düşer)."""
    if not metin:
        return None
    m = str(metin)
    eslesme = re.search(r"(\d{1,3}(?:[.,]\d{3})+|\d{4,})", m)
    if not eslesme:
        return None
    ham = eslesme.group(1).replace(".", "").replace(",", "")
    try:
        deger = float(ham)
    except ValueError:
        return None
    if deger < 1000:  # çok küçük değerler muhtemelen oda sayısı vb. yanlış yakalama
        return None
    return deger


_ODA_DESENI = re.compile(r"(\d)\s*\+\s*(\d)")
_M2_DESENI = re.compile(r"(\d+)\s*(?:m2|m²|metrekare)", re.IGNORECASE)


def _oda_secenekleri_cikar(metin):
    """Bir metinden TÜM '4+1' gibi oda desenlerinin ANA oda sayısını
    (ilk rakam) listeler. '2+1 veya 3+1' -> [2, 3], '3+1 - 4+1' -> [3, 4].
    Böylece talebin birden fazla kabul edilebilir oda seçeneği varsa
    hepsi değerlendirilir, sadece ilk eşleşme değil."""
    if not metin:
        return []
    return [int(m.group(1)) for m in _ODA_DESENI.finditer(str(metin))]


# ─────────────────────────────────────────────────────────────────────────
# 1) HARD FILTER
# ─────────────────────────────────────────────────────────────────────────
def lokasyon_hard_filter_gecer_mi(talep, portfoy):
    """Talebin 'ilceler' listesi doluysa (yani alıcı belirli ilçeler
    belirtmişse), o listenin DIŞINDAKİ bir ilçedeki portföy TAMAMEN elenir
    — sadece düşük puan almaz. Dry-run'da 'Buca talebine Karşıyaka sonucu
    çıkıyor' gibi güven kırıcı örnekler bulundu, bu yüzden lokasyon artık
    (talep ilçe belirtmişse) skor değil, sert filtre.
    Talep ilçe belirtmemişse (ilceler boş) ya da portföyün ilçesi bilinmiyorsa
    ELEME YAPILMAZ — belirsizlik durumunda dışlamak yerine düşük puanla
    (lokasyon_skoru'ndaki 'aynı il farklı ilçe' / 'belirsiz' dalları) devam
    edilir."""
    t_ilceler = talep.get("ilceler") or []
    t_ilceler_norm = {str(x).strip().lower() for x in t_ilceler if x}
    if not t_ilceler_norm:
        return True

    p_ilce = (portfoy.get("ilce") or "").strip().lower()
    if not p_ilce:
        return True

    return p_ilce in t_ilceler_norm


def pazar_ilani_normalize(row):
    """izmir_pazar_ilanlar satırını (Startkey ağı geneli, startkey_portfoy_listesi.py
    tarafından yazılan) mevcut skor fonksiyonlarının beklediği 'portfoyler'
    benzeri alan adlarına çevirir. Böylece lokasyon/bütçe/oda/kriter
    fonksiyonları HİÇ DEĞİŞMEDEN iki farklı tablo için de kullanılabiliyor.

    NOT: izmir_pazar_ilanlar'da 'portfoy_gorunurluk'/'kapali_oncelik' kavramı
    YOK — bunlar zaten canlı/linkli ilanlar, 'kapalı fırsat' olamazlar."""
    oda = row.get("oda_sayisi") or ""
    m2 = row.get("m2")
    oda_m2_metin = str(oda)
    if m2:
        try:
            oda_m2_metin += f", {int(float(m2))} m2"
        except (TypeError, ValueError):
            pass

    ozet_parcalari = [
        row.get("mahalle") or row.get("ilce") or "",
        str(oda) if oda else "",
        row.get("mulk_turu") or row.get("mulk_tipi") or "",
        row.get("islem_tipi") or "",
    ]
    ozet = " ".join(p for p in ozet_parcalari if p).strip() or "İlan"

    ozellikler = " ".join(filter(None, [
        row.get("esyali"), row.get("kullanim_durumu"), row.get("site_icerisinde"),
    ]))

    return {
        "il": row.get("il") or "İzmir",
        "ilce": row.get("ilce"),
        "ilceler": [],
        "islem_tipi": row.get("islem_tipi"),
        "mulk_tipi": row.get("mulk_tipi"),
        "oda_sayisi_m2": oda_m2_metin,
        "fiyat": row.get("fiyat"),
        "ozellikler": ozellikler,
        "ozet": ozet,
        "portfoy_gorunurluk": "startkey_agi",
        "link_sayisi": 1,
        "aktif": row.get("aktif", True),
        "ilan_linki": row.get("ilan_linki"),
        "marka": row.get("marka"),
        # ÖNEMLİ DÜZELTME: izmir_pazar_ilanlar tablosunda bu iki alan
        # gerçekten dolu geliyor (startkey_portfoy_listesi.py tarafından
        # "İlan sahibi" / "İlan tarihi" kaynağından yazılıyor), ama bu
        # normalize fonksiyonu eskiden onları hiç okumuyordu — bu yüzden
        # Startkey Ağı kaynaklı eşleşmelerde danışman/tarih hep "—"
        # görünüyordu.
        "talep_eden_danisan": row.get("talep_eden_danisan"),
        "ilan_tarihi": row.get("ilan_tarihi"),
        "ofis": row.get("ofis_norm") or row.get("ofis"),
    }


def hard_filter_gecer_mi(talep, portfoy):
    """(gecer: bool, red_sebebi: str|None) döner.
    İşlem tipi / mülk tipi uyumsuzsa False — AMA taraflardan biri
    Belirsiz/boşsa hiçbir zaman elenmez."""
    t_islem = _islem_normalize(talep.get("islem_tipi"))
    p_islem = _islem_normalize(portfoy.get("islem_tipi"))
    if not _belirsiz_mi(t_islem) and not _belirsiz_mi(p_islem) and t_islem != p_islem:
        return False, "işlem tipi uyumsuz"

    t_mulk = _mulk_normalize(talep.get("mulk_tipi"))
    p_mulk = _mulk_normalize(portfoy.get("mulk_tipi"))
    if not _belirsiz_mi(t_mulk) and not _belirsiz_mi(p_mulk) and t_mulk != p_mulk:
        return False, "mülk tipi uyumsuz"

    return True, None


def _belirsizlik_notlari(talep, portfoy):
    notlar = []
    t_islem = _islem_normalize(talep.get("islem_tipi"))
    p_islem = _islem_normalize(portfoy.get("islem_tipi"))
    if _belirsiz_mi(t_islem) or _belirsiz_mi(p_islem):
        notlar.append("işlem tipi belirsiz")

    t_mulk = _mulk_normalize(talep.get("mulk_tipi"))
    p_mulk = _mulk_normalize(portfoy.get("mulk_tipi"))
    if _belirsiz_mi(t_mulk) or _belirsiz_mi(p_mulk):
        notlar.append("mülk tipi belirsiz")
    return notlar


# ─────────────────────────────────────────────────────────────────────────
# 2) SKOR BİLEŞENLERİ (Lokasyon 40 / Bütçe-Fiyat 35 / Oda-m² 15 / Kriter 10)
# ─────────────────────────────────────────────────────────────────────────
def lokasyon_skoru(talep, portfoy):
    """portfoy.ilce esas alınır (portfoy.ilceler pratikte hep boş).
    talep.ilceler (liste) + talep.ilce birlikte değerlendirilir."""
    p_ilce = (portfoy.get("ilce") or "").strip()
    p_il = (portfoy.get("il") or "").strip()
    t_ilceler = talep.get("ilceler") or []
    t_ilceler_norm = {str(x).strip().lower() for x in t_ilceler if x}
    t_ilce = (talep.get("ilce") or "").strip()
    t_il = (talep.get("il") or "").strip()

    if not p_ilce or (not t_ilceler_norm and not t_ilce):
        return 5, "lokasyon belirsiz"

    if p_ilce.lower() in t_ilceler_norm or p_ilce.lower() == t_ilce.lower():
        return 40, f"aynı ilçe ({p_ilce})"

    if p_il and t_il and p_il.lower() == t_il.lower():
        return 10, "aynı il, farklı ilçe"

    return 0, "lokasyon uyumsuz"


def butce_fiyat_skoru(talep, portfoy):
    """Sadece 'bütçeyi aşıyor mu' değil, bütçenin NE KADAR altında kaldığını
    da dikkate alır — 22M bütçeli birine 5.9M'lik bir mülkü 'tam uyum'
    göstermek yanlış güven yaratıyordu (dry-run'da somut örnekle görüldü)."""
    butce = _sayi_ayikla(talep.get("max_butce"))
    fiyat = _sayi_ayikla(portfoy.get("fiyat"))

    if butce is None or fiyat is None:
        return 10, "bütçe/fiyat verisi eksik"

    if fiyat <= butce:
        oran = (fiyat / butce) if butce else 0
        if oran >= 0.70:
            return 35, "bütçe içinde"
        if oran >= 0.50:
            return 25, "bütçenin belirgin altında"
        if oran >= 0.30:
            return 15, "bütçenin oldukça altında"
        return 5, "bütçenin çok altında"

    fark_orani = (fiyat - butce) / butce
    if fark_orani <= 0.05:
        return 28, "bütçenin %5 üstünde"
    if fark_orani <= 0.10:
        return 18, "bütçenin %10 üstünde"
    if fark_orani <= 0.20:
        return 8, "bütçenin %20 üstünde"
    return 0, "bütçe aşımı yüksek"


def oda_m2_skoru(talep, portfoy):
    """Oda kısmı artık MESAFE bazlı: 4+1 isteyen birine 1+1 göstermek ile
    3+1 göstermek arasında fark gözetilir (eskiden ikisi de aynı 'yakın'
    puanını alıyordu — dry-run'da somut örnekle görüldü). Talebin birden
    fazla oda seçeneği varsa (örn. '2+1 veya 3+1') hepsi değerlendirilip
    en yakını kullanılır. m² kısmı değişmedi (net desen şartı aynı)."""
    t_metin = str(talep.get("oda_sayisi_m2") or "")
    p_metin = str(portfoy.get("oda_sayisi_m2") or "")
    notlar = []

    t_secenekler = _oda_secenekleri_cikar(t_metin)
    p_secenekler = _oda_secenekleri_cikar(p_metin)

    if t_secenekler and p_secenekler:
        p_ana = p_secenekler[0]
        fark = min(abs(t - p_ana) for t in t_secenekler)
        if fark == 0:
            oda_puan = 8
            notlar.append(f"{p_ana}+ oda tam uyumu")
        elif fark == 1:
            oda_puan = 5
            notlar.append("oda sayısı 1 fark")
        else:
            # Karar: 2+ oda farkı artık neredeyse hiç puan almasın — 3+1
            # arayana 1+1, ya da 1+1 arayana 3+1 göstermek gerçek pratikte
            # kabul edilebilir bir öneri değil (dry-run'da somut örneklerle
            # görüldü, bkz. "Menemen 1+1" ve "Karşıyaka 4+1" talepleri).
            oda_puan = 0
    else:
        oda_puan = 2

    puan = oda_puan

    t_m2 = _M2_DESENI.search(t_metin)
    p_m2 = _M2_DESENI.search(p_metin)
    if t_m2 and p_m2:
        t_deger, p_deger = int(t_m2.group(1)), int(p_m2.group(1))
        fark_oran = abs(t_deger - p_deger) / max(t_deger, p_deger, 1)
        if fark_oran <= 0.15:
            puan += 7
            notlar.append(f"{p_deger} m² uyumlu")
        else:
            puan += 3
    else:
        puan += 2

    return min(puan, 15), (" · ".join(notlar) if notlar else None)


_KRITER_KELIMELERI = [
    "asansör", "otopark", "eşyalı", "site", "bahçe", "deniz", "manzara",
    "balkon", "teras", "metro", "izban", "merkezi", "sıfır", "yeni", "ara kat",
]


def _kelime_gecer_mi(kelime, metin):
    """Basit 'k in metin' alt-string kontrolü yanlış pozitif üretiyordu —
    örn. 'bahçe' kriteri 'Güzelbahçe' ilçe adının İÇİNDE de eşleşiyordu.
    Kelime sınırı (\\b) ile sadece gerçek bağımsız kelime eşleşmesi sayılır."""
    return re.search(r"\b" + re.escape(kelime) + r"\b", metin) is not None


def ozel_kriter_skoru(talep, portfoy):
    """MVP'de NLP/embedding YOK — sadece basit kelime kesişimi (kelime
    sınırlı, alt-string değil)."""
    t_metin = f"{talep.get('ozel_kriterler','')} {talep.get('ozet','')}".lower()
    p_metin = f"{portfoy.get('ozellikler','')} {portfoy.get('ozet','')}".lower()
    ortak = [k for k in _KRITER_KELIMELERI if _kelime_gecer_mi(k, t_metin) and _kelime_gecer_mi(k, p_metin)]

    if len(ortak) >= 3:
        return 10, f"{', '.join(ortak[:3])} kriteri eşleşti"
    if len(ortak) >= 1:
        return 5, f"{', '.join(ortak)} kriteri eşleşti"
    return 0, None


# ─────────────────────────────────────────────────────────────────────────
# 3) ANA FONKSİYON
# ─────────────────────────────────────────────────────────────────────────
def eslesen_portfoyleri_bul(talep, portfoyler, pazar_ilanlari=None, max_sonuc=10):
    """
    talep         : alici_talepleri'nden tek bir kayıt (dict)
    portfoyler    : portfoyler tablosundan çekilmiş kayıt listesi (dict listesi)
    pazar_ilanlari: (opsiyonel) izmir_pazar_ilanlar'dan çekilmiş HAM satırlar —
                     bu fonksiyon içeride marka='startkey' filtresi uygular ve
                     pazar_ilani_normalize() ile portfoyler'le aynı şekle çevirir.
    max_sonuc     : toplamda döndürülecek en fazla sonuç sayısı

    Döner: [{"portfoy", "skor", "seviye", "gerekce", "grup"}, ...]
    "grup": "kapali_linksiz" | "startkey_agi" | "aktif_portfoy"

    SIRALAMA MANTIĞI (önemli):
    - "Kapalı/Linksiz Fırsatlar" HER ZAMAN önce gelir (stratejik öncelik —
      skor bu grubu ATLATAMAZ, çünkü bunlar başka yerde bulunamayan fırsatlar).
    - Bunun DIŞINDAKİ her şey (Startkey ağı ilanları + Zeta'nın kendi aktif
      portföyleri) KAYNAĞA GÖRE DEĞİL, SADECE SKORA GÖRE karışık sıralanır.
      Örn. bir Zeta portföyü %100, bir Startkey ağı ilanı %70 uyumsa,
      Zeta portföyü önce gelir — kaynak önceliği burada geçerli değil,
      sadece kapalı/linksiz için geçerli.

    NOT: aktif=false olan HİÇBİR kayıt (her iki tablodan da) bu fonksiyona
    hiç girmez (MVP kararı — bkz. modül başındaki metodoloji notu #4).
    """
    sonuclar = []

    for p in portfoyler:
        if p.get("aktif") is False:
            continue

        gecer, _ = hard_filter_gecer_mi(talep, p)
        if not gecer:
            continue
        if not lokasyon_hard_filter_gecer_mi(talep, p):
            continue

        gerekceler = list(_belirsizlik_notlari(talep, p))
        lok_puan, lok_not = lokasyon_skoru(talep, p)
        but_puan, but_not = butce_fiyat_skoru(talep, p)
        oda_puan, oda_not = oda_m2_skoru(talep, p)
        kri_puan, kri_not = ozel_kriter_skoru(talep, p)
        for n in (lok_not, but_not, oda_not, kri_not):
            if n:
                gerekceler.append(n)
        toplam = lok_puan + but_puan + oda_puan + kri_puan
        if toplam < 40:
            continue

        gorunurluk = p.get("portfoy_gorunurluk", "")
        link_sayisi = p.get("link_sayisi", 0) or 0
        grup = (
            "kapali_linksiz"
            if gorunurluk in ("kapali_portfoy", "kapali_adayi") and link_sayisi == 0
            else "aktif_portfoy"
        )
        sonuclar.append({
            "portfoy": p, "skor": toplam,
            "seviye": "güçlü" if toplam >= 70 else "olası",
            "gerekce": " · ".join(gerekceler) if gerekceler else "temel kriterler uyumlu",
            "grup": grup,
        })

    for ham in (pazar_ilanlari or []):
        if str(ham.get("marka") or "").strip().lower() != "startkey":
            continue
        if ham.get("aktif") is False:
            continue

        p = pazar_ilani_normalize(ham)
        gecer, _ = hard_filter_gecer_mi(talep, p)
        if not gecer:
            continue
        if not lokasyon_hard_filter_gecer_mi(talep, p):
            continue

        gerekceler = list(_belirsizlik_notlari(talep, p))
        lok_puan, lok_not = lokasyon_skoru(talep, p)
        but_puan, but_not = butce_fiyat_skoru(talep, p)
        oda_puan, oda_not = oda_m2_skoru(talep, p)
        kri_puan, kri_not = ozel_kriter_skoru(talep, p)
        for n in (lok_not, but_not, oda_not, kri_not):
            if n:
                gerekceler.append(n)
        toplam = lok_puan + but_puan + oda_puan + kri_puan
        if toplam < 40:
            continue

        sonuclar.append({
            "portfoy": p, "skor": toplam,
            "seviye": "güçlü" if toplam >= 70 else "olası",
            "gerekce": " · ".join(gerekceler) if gerekceler else "temel kriterler uyumlu",
            "grup": "startkey_agi",
        })

    # KARAR (bu turda basitleştirildi): grup önceliği YOK — kapalı/linksiz
    # fırsatlar, Startkey ağı ilanları ve Zeta portföyleri TEK bir havuzda,
    # SADECE skora göre sıralanır. "grup" etiketi sadece ekranda kaynağı
    # göstermek için tutuluyor, sıralamayı etkilemiyor. Böylece örn. %70
    # uyan bir kapalı fırsat, %95 uyan bir Zeta portföyünün önüne geçemez.
    sonuclar_sirali = sorted(sonuclar, key=lambda x: -x["skor"])
    return sonuclar_sirali[:max_sonuc]
