"""
core/eslesme_havuzu.py

Bölge Havuzu "Eşleşme" sekmesi — SALT OKUNUR, bildirim göndermez (10.10.2026).

İki yön:
  A) Zeta portföyü  → uygun alıcı talepleri (Zeta GD'leri + mail sistemi)
  B) Alıcı talebi   → uygun portföyler (Zeta portföyü, paylaşım, Startkey ilanı)

PUANLAMA core/match_engine.py'deki MEVCUT bileşenlerle yapılır (ilçe 40 /
bütçe-fiyat 35 / oda-m² 15 / özel kriter 10; işlem ve mülk tipi uyumsuzsa
eleme; talep ilçe belirtmişse dışındaki ilçe elenir). Burada yeni puan
kuralı YOK — yalnız aynı bileşenler iki yönde çağrılır. match_engine.py'ye
dokunulmaz (cift_skorla(), eslesen_portfoyleri_bul()'un iç döngüsüyle
aynı sonucu verir; test: tests/denklik).

Veri penceresi (bilinçli):
  - Alıcı talepleri adayı: son 60 gün (panelin genel penceresiyle aynı).
  - Zeta portföyü: aktif stok (dönem süzgeci yok).
  - Startkey ilanı: aktif stok (en fazla bolge_havuzu.MAX_SATIR kayıt).
  - Paylaşım (portföyler tablosu, Zeta dışı): son 60 gün.
  Ekrandaki "Dönem" yalnız KAYNAK tarafı olan alıcı talebini süzer.
"""
from datetime import datetime, timedelta, timezone

from core import bolge_havuzu as bh
from core.match_engine import (
    hard_filter_gecer_mi, lokasyon_hard_filter_gecer_mi, _belirsizlik_notlari,
    lokasyon_skoru, butce_fiyat_skoru, oda_m2_skoru, ozel_kriter_skoru,
    pazar_ilani_normalize,
)

ADAY_PENCERESI_GUN = 60
GUCLU_ESIK = 70
OLASI_ESIK = 40
MAX_KAYNAK = 200        # bir ekranda hesaplanacak en fazla kaynak kayıt
# Olay niteliğindeki kayıtların (alıcı talebi, paylaşım) eşleşmede yaşayabileceği süre.
# Kiralık talepler hızlı kapandığı için kısa; satılık talepler uzun yaşar. Tahmini
# varsayılanlar — ekrandaki "Eşleşme kuralları"ndan değiştirilebilir. İşlem tipi
# anlaşılamayan kayıt satılık süresine tabidir. Aktif stok (Zeta portföyü, Startkey) süresizdir.
KIRALIK_OMUR_GUN = 14
SATILIK_OMUR_GUN = 45

_TALEP_ALANLARI = ("islem_tipi", "mulk_tipi", "il", "ilce", "max_butce",
                   "oda_sayisi_m2", "ozel_kriterler", "ozet")
_PORTFOY_ALANLARI = ("islem_tipi", "mulk_tipi", "il", "ilce", "fiyat",
                     "oda_sayisi_m2", "ozellikler", "ozet", "aktif",
                     "portfoy_gorunurluk", "link_sayisi")


def _ilce_anahtar(metin):
    """match_engine'in kendi karşılaştırmasıyla AYNI: strip().lower()."""
    return (metin or "").strip().lower()


# ── MOTOR ───────────────────────────────────────────────────────────────
def cift_skorla(talep, portfoy, min_skor=OLASI_ESIK):
    """(skor, gerekçe_metni) ya da None (elendi / eşik altı).
    eslesen_portfoyleri_bul()'un portfoyler döngüsüyle aynı bileşenler ve aynı
    sonuç; tek fark: eşiğe ulaşması artık mümkün değilse kalan (pahalı, regex'li)
    bileşenler hesaplanmadan erken çıkılır — eşik üstü sonuçlar etkilenmez."""
    if portfoy.get("aktif") is False:
        return None
    gecer, _ = hard_filter_gecer_mi(talep, portfoy)
    if not gecer:
        return None
    if not lokasyon_hard_filter_gecer_mi(talep, portfoy):
        return None
    esik = max(min_skor, OLASI_ESIK)
    gerekceler = list(_belirsizlik_notlari(talep, portfoy))
    lok, lok_not = lokasyon_skoru(talep, portfoy)
    but, but_not = butce_fiyat_skoru(talep, portfoy)
    if lok + but + 15 + 10 < esik:          # oda en çok 15, kriter en çok 10
        return None
    oda, oda_not = oda_m2_skoru(talep, portfoy)
    if lok + but + oda + 10 < esik:
        return None
    kri, kri_not = ozel_kriter_skoru(talep, portfoy)
    toplam = lok + but + oda + kri
    if toplam < esik:
        return None
    for n in (lok_not, but_not, oda_not, kri_not):
        if n:
            gerekceler.append(n)
    return toplam, (" · ".join(gerekceler) if gerekceler else "temel kriterler uyumlu")


# ── VERİ ────────────────────────────────────────────────────────────────
def _talep_kaydi(k):
    ham = k.get("ham") or {}
    motor = {a: ham.get(a) for a in _TALEP_ALANLARI}
    # Motorun sert ilçe filtresi talep["ilceler"] listesine bakar; listeyi
    # ilce alanıyla birleştirilmiş (bh._ilceler_of) haliyle veriyoruz.
    motor["ilceler"] = [i for i in (k.get("ilceler") or []) if i]
    return {
        "kid": k["id"], "tur": "talep", "motor": motor, "baslik": k["baslik"],
        "alt": k.get("alt") or "", "sahip": k.get("sahip") or "", "kaynak": k.get("kaynak") or "",
        "fiyat": k.get("fiyat") or str(ham.get("max_butce") or "").strip(), "ilceler": motor["ilceler"],
        "zaman": k.get("zaman"),
        "link": "", "yas_kat": k.get("yas_kat") or "", "islem": k.get("islem") or "",
        "ham": ham,
    }


def _portfoy_kaydi(k, etiket):
    ham = k.get("ham") or {}
    if k["tur"] == "startkey":
        motor = pazar_ilani_normalize(ham)
    else:
        motor = {a: ham.get(a) for a in _PORTFOY_ALANLARI}
        motor["ilceler"] = []   # motor yalnız portfoy.ilce'ye bakar (bkz. match_engine notu #5)
    return {
        "kid": k["id"], "tur": k["tur"], "motor": motor, "baslik": k["baslik"],
        "alt": k.get("alt") or "", "sahip": k.get("sahip") or "", "kaynak": etiket,
        "fiyat": k.get("fiyat") or "", "ilceler": [i for i in (k.get("ilceler") or []) if i],
        "zaman": k.get("zaman"), "link": k.get("link") or "",
        "yas_kat": k.get("yas_kat") or "", "islem": k.get("islem") or "",
        "ham": ham, "bayat": bool(k.get("bayat")),
    }


def veri_yukle(simdi=None):
    """Eşleşme için kayıtlar. Dönüş: ({'talep','zeta','paylasim','startkey'}, hatalar, bilgi).
    Bir kaynak okunamazsa diğerleri yine gelir (hatalar sözlüğünde görünür)."""
    simdi = simdi or datetime.now(timezone.utc)
    kesim = simdi - timedelta(days=ADAY_PENCERESI_GUN)
    veri = {"talep": [], "zeta": [], "paylasim": [], "startkey": []}
    hatalar = {}
    bilgi = {"bayat_zeta": 0}

    def dene(ad, fn):
        try:
            return fn()
        except Exception as e:      # noqa: BLE001
            hatalar[ad] = str(e)
            return None

    r = dene("Alıcı talebi", lambda: bh._alici_talepleri(kesim, simdi))
    if r is not None:
        veri["talep"] = [_talep_kaydi(k) for k in r]
    r = dene("Portföyler", lambda: bh._portfoyler(kesim, simdi))
    if r is not None:
        paylasim, zeta = r
        veri["paylasim"] = [_portfoy_kaydi(k, "Paylaşım") for k in paylasim]
        tum_zeta = [_portfoy_kaydi(k, "Zeta portföyü") for k in zeta]
        # Revy'den kalkıp hâlâ aktif görünen (bayat) ilanlar eşleştirmeye girmez.
        veri["zeta"] = [k for k in tum_zeta if not k["bayat"]]
        bilgi["bayat_zeta"] = len(tum_zeta) - len(veri["zeta"])
    # Startkey: aktif stok — tarih süzgeci yok (çok eski tarih = süzgeçsiz)
    r = dene("Startkey ilanı", lambda: bh._startkey(simdi - timedelta(days=3650), simdi))
    if r is not None:
        veri["startkey"] = [_portfoy_kaydi(k, "Startkey ilanı") for k in r]
    return veri, hatalar, bilgi


# ── İNDEKS / EŞLEŞTİRME ─────────────────────────────────────────────────
def _ilce_indeksi(kayitlar):
    """{ilçe_anahtarı: [kayıt]} + ilçesiz kayıtlar (motor onları elemez)."""
    idx, ilcesiz = {}, []
    for k in kayitlar:
        i = _ilce_anahtar(k["motor"].get("ilce"))
        if i:
            idx.setdefault(i, []).append(k)
        else:
            ilcesiz.append(k)
    return idx, ilcesiz


def _portfoy_adaylari(talep_kaydi, idx, ilcesiz, hepsi):
    """Talebin ilçelerine göre aday portföyler; ilçe belirtilmemişse hepsi."""
    ilceler = {_ilce_anahtar(i) for i in talep_kaydi["motor"].get("ilceler") or []}
    if not ilceler:
        return hepsi
    sonuc = list(ilcesiz)
    for i in ilceler:
        sonuc.extend(idx.get(i, []))
    return sonuc


def _guclu_mu(skor):
    return skor >= GUCLU_ESIK


def talepten_portfoylere(talepler, adaylar, ust_n=5, min_skor=OLASI_ESIK):
    """Her alıcı talebi için en iyi portföyler.
    Dönüş: [{'kaynak': talep, 'aday': portföy, 'skor', 'gerekce', 'guclu'}]"""
    idx, ilcesiz = _ilce_indeksi(adaylar)
    cikti = []
    for t in talepler:
        bulunan = []
        for p in _portfoy_adaylari(t, idx, ilcesiz, adaylar):
            s = cift_skorla(t["motor"], p["motor"], min_skor)
            if s and s[0] >= min_skor:
                bulunan.append((s[0], s[1], p))
        bulunan.sort(key=lambda x: -x[0])
        for skor, gerekce, p in bulunan[:ust_n]:
            cikti.append({"kaynak": t, "aday": p, "skor": skor, "gerekce": gerekce, "guclu": _guclu_mu(skor)})
    return cikti


def portfoyden_taleplere(portfoyler, talepler, ust_n=5, min_skor=OLASI_ESIK):
    """Her portföy için en iyi alıcı talepleri (ters yön)."""
    cikti = []
    for p in portfoyler:
        p_ilce = _ilce_anahtar(p["motor"].get("ilce"))
        bulunan = []
        for t in talepler:
            # Ön eleme: talep ilçe belirtmiş ve portföy ilçesi bilinen başka ilçeyse
            # motor zaten eler; burada ucuz bir ön kontrolle gereksiz hesabı atlıyoruz.
            t_ilceler = {_ilce_anahtar(i) for i in t["motor"].get("ilceler") or []}
            if t_ilceler and p_ilce and p_ilce not in t_ilceler:
                continue
            s = cift_skorla(t["motor"], p["motor"], min_skor)
            if s and s[0] >= min_skor:
                bulunan.append((s[0], s[1], t))
        bulunan.sort(key=lambda x: -x[0])
        for skor, gerekce, t in bulunan[:ust_n]:
            cikti.append({"kaynak": p, "aday": t, "skor": skor, "gerekce": gerekce, "guclu": _guclu_mu(skor)})
    return cikti


# ── EKRAN FİLTRELERİ ────────────────────────────────────────────────────
def _ilce_uyar(kayit, ilce):
    """bh.ilceye_gore ile aynı anlam: ilce None -> hepsi; ILCE_BELIRSIZ -> ilçesizler."""
    if ilce is None:
        return True
    ilceler = [i for i in kayit["ilceler"] if i]
    if ilce == bh.ILCE_BELIRSIZ:
        return not ilceler
    h = bh.tr_kucuk(ilce)
    return any(bh.tr_kucuk(i) == h for i in ilceler)


def omre_gore(kayitlar, simdi, kira_gun=KIRALIK_OMUR_GUN, satis_gun=SATILIK_OMUR_GUN):
    """İşlem tipine göre süresi dolmamış kayıtlar (tarihsiz kayıt elenmez)."""
    sonuc = []
    for k in kayitlar:
        z = k.get("zaman")
        if not z:
            sonuc.append(k)
            continue
        sinir = kira_gun if k.get("islem") == "Kiralık" else satis_gun
        if (simdi - z) <= timedelta(days=sinir):
            sonuc.append(k)
    return sonuc


def hesapla(veri, yon, ilce, gun, ust_n=5, min_skor=OLASI_ESIK, simdi=None,
            kira_gun=KIRALIK_OMUR_GUN, satis_gun=SATILIK_OMUR_GUN):
    """Ekranın tek giriş noktası.
    yon: 'zeta_talep' (Zeta portföyü → alıcılar) | 'talep_portfoy' (talep → portföyler)
    Dönüş: (çiftler, kaynak_sayisi, kirpildi)"""
    simdi = simdi or datetime.now(timezone.utc)
    talepler = omre_gore(veri["talep"], simdi, kira_gun, satis_gun)
    paylasimlar = omre_gore(veri["paylasim"], simdi, kira_gun, satis_gun)
    if yon == "zeta_talep":
        kaynaklar = [k for k in veri["zeta"] if _ilce_uyar(k, ilce)]
        kirpildi = len(kaynaklar) > MAX_KAYNAK
        kaynaklar = kaynaklar[:MAX_KAYNAK]
        return portfoyden_taleplere(kaynaklar, talepler, ust_n, min_skor), len(kaynaklar), kirpildi
    kesim = simdi - timedelta(days=gun)
    kaynaklar = [k for k in talepler
                 if _ilce_uyar(k, ilce) and k["zaman"] and k["zaman"] >= kesim]
    kirpildi = len(kaynaklar) > MAX_KAYNAK
    kaynaklar = kaynaklar[:MAX_KAYNAK]
    adaylar = veri["zeta"] + paylasimlar + veri["startkey"]
    return talepten_portfoylere(kaynaklar, adaylar, ust_n, min_skor), len(kaynaklar), kirpildi


# ── GÖSTERİM: gruplu kart verisi ────────────────────────────────────────
_CSS_ONBELLEK = {}


def kart_css():
    """Orijinal kartların stilleri — pano_export'taki ŞABLONLARDAN çıkarılır
    (kopya yok; kart tasarımı değişirse burası kendiliğinden güncellenir).
    Shadow DOM içinde kullanılacağı için :root/html/body seçicileri uyarlanır."""
    if _CSS_ONBELLEK:
        return dict(_CSS_ONBELLEK)
    import re
    from core import pano_export as pe

    def cikar(html):
        m = re.search(r"<style>(.*?)</style>", html, re.S)
        css = m.group(1) if m else ""
        css = css.replace(":root", ":host").replace("html {", ".x-html {").replace("body {", ".x-body {")
        # Orijinal sayfa gövdesi min-height:100vh ister; iframe içinde bu, iframe yüksekliğini
        # sonsuz büyütür (yükseklik ↔ vh geri beslemesi). Kart listesinde gerekmez.
        css = re.sub(r"min-height:\s*100vh;?", "", css)
        return css

    _CSS_ONBELLEK["talep"] = cikar(pe.pano_html_olustur([], "x", "talep", baslik_goster=False).getvalue().decode("utf-8"))
    _CSS_ONBELLEK["pazar"] = cikar(pe.pazar_ilan_pano_html_olustur([], "x", baslik_goster=False).getvalue().decode("utf-8"))
    return dict(_CSS_ONBELLEK)


def kart_html(kayit):
    """{'css': 'talep'|'pazar', 'html': orijinal kart HTML'i} — uygulamadaki
    Talep/Portföy/Zeta Portföyleri/Startkey İlanları ekranlarının kullandığı
    aynı şablonlar."""
    from core import pano_export as pe
    ham = kayit.get("ham") or {}
    try:
        if kayit["tur"] == "startkey":
            return {"css": "pazar", "html": pe._pazar_ilan_kart_html(ham)}
        if kayit["tur"] == "talep":
            return {"css": "talep", "html": pe._kart_html(ham, "talep")}
        return {"css": "talep", "html": pe._kart_html(ham, "portfoy")}
    except Exception as e:      # noqa: BLE001 — tek kartın hatası listeyi bozmasın
        return {"css": "talep", "html": f"<div>Kart oluşturulamadı: {type(e).__name__}</div>"}


def _kisi(kayit):
    from core.rapor_export import _isim_ayikla
    return _isim_ayikla(kayit.get("sahip") or "") or ""


def _tarih_metni(kayit):
    """Kartta görünenle aynı biçim: gg.aa.yyyy ss:dd (mail/portföy), Startkey'de ilk görülme günü."""
    from core import pano_export as pe
    ham = kayit.get("ham") or {}
    if kayit["tur"] == "startkey":
        g = str(ham.get("ilk_gorulme_tarihi") or "")[:10]
        if len(g) == 10 and g[4] == "-":
            return f"{g[8:10]}.{g[5:7]}.{g[0:4]}"
        return ""
    return pe._tarih_saat_kisalt(ham.get("kayit_tarihi")) or (
        kayit["zaman"].strftime("%d.%m.%Y %H:%M") if kayit.get("zaman") else "")


def _meta(kayit):
    return " · ".join(x for x in (_tarih_metni(kayit), _kisi(kayit)) if x)


def gruplari_kur(ciftler):
    """Düz çift listesini kaynak bazında gruplar; gruplar en iyi skora göre,
    adaylar skora göre sıralıdır. Dönüş: bileşenin beklediği sözlük listesi
    (kart HTML'leri DAHİL) + süzme için 'sahip' anahtarı."""
    gruplar, sira = {}, []
    for c in ciftler:
        kid = c["kaynak"]["kid"]
        if kid not in gruplar:
            gruplar[kid] = {"kaynak": c["kaynak"], "ciftler": []}
            sira.append(kid)
        gruplar[kid]["ciftler"].append(c)
    cikti = []
    for kid in sira:
        g = gruplar[kid]
        k = g["kaynak"]
        adaylar_ = sorted(g["ciftler"], key=lambda c: -c["skor"])
        ilce = ", ".join(i for i in k["ilceler"] if i)
        cikti.append({
            "en_iyi": adaylar_[0]["skor"],
            "sahip": _kisi(k),
            "arama": " ".join([k["baslik"], k.get("alt") or "", ilce, _kisi(k)]).lower(),
            "kaynak": {
                "baslik": k["baslik"],
                "chips": [x for x in (ilce, k.get("fiyat"), k.get("kaynak"), _meta(k)) if x],
                "link": bh.guvenli_url(k.get("link")),
                "kart": kart_html(k),
            },
            "adaylar": [{
                "oran": c["skor"], "guclu": c["guclu"], "baslik": c["aday"]["baslik"],
                "gerekce": c["gerekce"], "kaynak": c["aday"].get("kaynak") or "",
                "link": bh.guvenli_url(c["aday"].get("link")), "meta": _meta(c["aday"]),
                "kart": kart_html(c["aday"]),
            } for c in adaylar_],
        })
    cikti.sort(key=lambda g: -g["en_iyi"])
    return cikti
