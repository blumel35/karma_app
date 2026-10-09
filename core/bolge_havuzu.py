# core/bolge_havuzu.py
# -*- coding: utf-8 -*-
"""
Bölge Havuzu — yönetici için SALT-OKUNUR bölge akışı (09.10.2026).

Meltem: "bölge havuzu" = bir ilçeye düşen bütün kayıtların tek listede
görüldüğü ana havuz (Startkey ilanı, alıcı talebi, Zeta paylaşımı, Zeta
portföyü, yatırım talebi...). Bu sürüm yalnızca GÖSTERİR: hiçbir bildirim
göndermez, hiçbir tabloya yazmaz. "Bu kayıt için kime bildirim giderdi?"
sorusunu simüle eder (alıcı listesi + mesaj önizlemesi).

DIŞ BESLEME KANALI (Meltem: "ileride müşteriden gelen diğer taleplerde
satıcı alıcı bu bölüme bağlanacak, bu sistemin dış beslenme kanalı
olacak"): müşteri formlarından gelen kayıtlar `musteri_talepleri`
tablosuna `talep_tipi` ile yazılıyor. Bugün yalnızca `yatirim_alici`
(Yatırım Alıcısı İhtiyaç Formu) var. Yeni bir form (satıcı, ev sahibi,
kiracı, alıcı...) eklendiğinde YAPILACAK TEK ŞEY MUSTERI_FORM_KANALLARI
sözlüğüne bir satır eklemektir — sekme, sayım, ilçe eşleştirme, dönem
filtresi ve alıcı simülasyonu otomatik gelir.

KAYNAK KAYDI (KAYNAKLAR): her kayıt türü bir "adaptör"dür: (ilçe, kesim
zamanı) -> normalize edilmiş kayıt listesi. Normalize kayıt alanları:
    id, tur, baslik, alt, zaman(datetime|None), yeni(bool), sahip,
    fiyat(str), mahalle, ilce, link, alanlar(list[(etiket, değer)])

İLÇE EŞLEŞTİRME: yapılandırılmış tablolarda `ilce` / `ilceler` alanı,
müşteri formlarında serbest metin olan `oncelikli_bolge` /
`alternatif_bolge` içinde ilçe adının geçmesi (Türkçe büyük/küçük harf
duyarsız). Hiçbir ilçeyle eşleşmeyen form kaydı "(İlçe belirsiz)"
kovasında tutulur — kaybolmaz.
"""

import re
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

from core.supabase_client import get_client

supabase = get_client()

ILCE_BELIRSIZ = "(İlçe belirsiz)"
DONEMLER = {"Son 24 saat": 1, "Son 7 gün": 7, "Son 30 gün": 30}
ZETA_PAYLASIM_KAYNAKLARI = {"zeta", "ofis"}
ZETA_PORTFOY_KAYNAKLARI = {"zeta1", "zeta2"}
MAX_SATIR = 3000     # tek tablodan en fazla bu kadar son kayıt okunur

# Seçilen kayıtlardan paylaşılabilir pano linki: tür -> pano biçimi.
# Yatırım talepleri/müşteri formları kişisel veri (ad, telefon) taşıdığı için
# herkese açık link şimdilik KAPALI.
LINK_BICIMI = {"startkey": "pazar", "talep": "talep", "paylasim": "portfoy", "zeta": "portfoy"}

# ── DIŞ KANAL KAYDI ─────────────────────────────────────────────────
# talep_tipi -> sekme. Yeni form = yeni satır.
MUSTERI_FORM_KANALLARI = {
    "yatirim_alici": {"ad": "Yatırım talebi", "kisa": "yatırım talebi", "renk": "teal"},
    # "satici_formu":   {"ad": "Satıcı formu",   "kisa": "satıcı formu",   "renk": "amber"},
    # "alici_formu":    {"ad": "Alıcı formu",    "kisa": "alıcı formu",    "renk": "rose"},
    # "ev_sahibi":      {"ad": "Ev sahibi formu","kisa": "ev sahibi formu","renk": "slate"},
    # "kiraci":         {"ad": "Kiracı formu",   "kisa": "kiracı formu",   "renk": "slate"},
}


# ── YARDIMCILAR ─────────────────────────────────────────────────────
def tr_kucuk(metin):
    return str(metin or "").replace("İ", "i").replace("I", "ı").casefold().strip()


def _zaman(*degerler):
    """RFC822 metin (kayit_tarihi) ya da ISO (created_at, ilk_gorulme_tarihi)
    -> tz-aware UTC datetime; çözülemezse None."""
    for d in degerler:
        if not d:
            continue
        if isinstance(d, datetime):
            return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
        s = str(d).strip()
        try:
            t = parsedate_to_datetime(s)
            if t is not None:
                return t if t.tzinfo else t.replace(tzinfo=timezone.utc)
        except (TypeError, ValueError, IndexError):
            pass
        try:
            t = datetime.fromisoformat(s.replace("Z", "+00:00"))
            return t if t.tzinfo else t.replace(tzinfo=timezone.utc)
        except ValueError:
            if len(s) >= 10:
                try:
                    return datetime.strptime(s[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
                except ValueError:
                    pass
    return None


def guvenli_url(u):
    """Tabloda tıklanabilir link için: yalnızca http(s) adresleri."""
    u = str(u or "").strip()
    return u if re.match(r"^https?://", u, re.I) else ""


def zaman_etiketi(t, simdi=None):
    if not t:
        return ""
    simdi = simdi or datetime.now(timezone.utc)
    fark = simdi - t
    dk = int(fark.total_seconds() // 60)
    if dk < 1:
        return "az önce"
    if dk < 60:
        return f"{dk} dk önce"
    if dk < 60 * 24:
        return f"{dk // 60} sa önce"
    return f"{dk // (60 * 24)} gün önce"


def para(deger):
    try:
        n = int(float(deger))
    except (TypeError, ValueError):
        return ""
    return f"{n:,}".replace(",", ".") + " TL"


def _sayfalar(tablo, secim="*", filtreler=None, tarih_alani=None, kesim_iso=None, in_alani=None):
    """Sayfalı okuma (PostgREST 1000 satır sınırı). id azalan; MAX_SATIR'da durur."""
    sonuc, bas, boy = [], 0, 1000
    while len(sonuc) < MAX_SATIR:
        sorgu = supabase.table(tablo).select(secim)
        for alan, deger in (filtreler or {}).items():
            sorgu = sorgu.eq(alan, deger)
        if in_alani:
            sorgu = sorgu.in_(in_alani[0], list(in_alani[1]))
        if tarih_alani and kesim_iso:
            sorgu = sorgu.gte(tarih_alani, kesim_iso)
        resp = sorgu.order("id", desc=True).range(bas, bas + boy - 1).execute()
        satirlar = resp.data or []
        sonuc.extend(satirlar)
        if len(satirlar) < boy:
            break
        bas += boy
    return sonuc


def _kaynak_etiketi(v):
    """Kaydın nereden geldiği: mail sistemi mi, danışmanın uygulamadan
    girdiği Zeta paylaşımı mı, resmi Zeta portföyü mü."""
    if tr_kucuk(v.get("kaynak")) in ZETA_PORTFOY_KAYNAKLARI:
        return "Zeta portföyü"
    if (v.get("kaynak_klasor") or "") == "danisman_panel":
        return "Zeta paylaşımı (uygulamadan)"
    return "Mail sistemi"


def _ilceler_of(v):
    liste = [i for i in (v.get("ilceler") or []) if i]
    if v.get("ilce") and v["ilce"] not in liste:
        liste.insert(0, v["ilce"])
    return liste


# ── İŞLEM TİPİ / BİNA YAŞI / KAT ────────────────────────────────────
def islem_normal(*degerler):
    """'Satılık' / 'Kiralık' / '—' (Belirsiz, boş, tanınmayan)."""
    for d in degerler:
        m = tr_kucuk(d)
        if "kiral" in m:
            return "Kiralık"
        if "satı" in m or "satil" in m or "satis" in m or "satış" in m:
            return "Satılık"
    return "—"


def yas_metni(ham):
    """Yapılandırılmış bina yaşı (Revy: '0', '5', '5-10', '21 Ve Üzeri',
    'Sıfır'...) -> '5 yaş' / '5-10 yaş' / '21+ yaş' / 'sıfır'."""
    m = tr_kucuk(ham)
    if not m or m in ("nan", "none", "belirtilmemiş"):
        return ""
    if "sıfır" in m:
        return "sıfır"
    if m.isdigit():
        return "sıfır" if int(m) == 0 else f"{int(m)} yaş"
    ar = re.fullmatch(r"(\d{1,2})\s*[-–]\s*(\d{1,2})", m)
    if ar:
        return f"{ar.group(1)}-{ar.group(2)} yaş"
    ve = re.match(r"(\d{1,2})\s*(?:ve|\+)\s*(?:üzeri|üstü|\+)?", m)
    if ve and ("üz" in m or "üst" in m or "+" in m):
        return f"{ve.group(1)}+ yaş"
    return str(ham).strip()


def yas_kat_birlestir(yas, kat):
    return " / ".join(x for x in [yas, tr_kucuk(kat) if kat else ""] if x) or "—"


_RE_ARALIK = re.compile(r"(\d{1,2})\s*[-–]\s*(\d{1,2})\s*(?:yaş|yas)")
_RE_AZAMI = re.compile(
    r"(?:en fazla|maksimum|max\.?|en çok|en az)?\s*(\d{1,2})\s*(?:yaş|yas)\w*\s*"
    r"(?:ve altı|altı|geçmeyen|üstü olmayan|kadar|dan küçük)"
)
_RE_AZAMI_ON = re.compile(r"(?:en fazla|maksimum|max\.?|en çok)\s*(\d{1,2})\s*(?:yaş|yas)")
_RE_YAS = re.compile(r"(?:bina\s*yaşı\s*[:\-]?\s*)?(\d{1,2})\s*(?:yaş|yas)")
_RE_YAS_BINA = re.compile(r"bina\s*yaşı\s*[:\-]?\s*(\d{1,2})\b")
_RE_KAT_NO = re.compile(r"(\d{1,2})\s*\.?\s*kat(?!lı|ı\s*karşılığı|\s*karşılığı|\s*mülk)")
_KAT_SOZ = [
    ("zemin kat", "zemin kat"), ("bahçe kat", "bahçe katı"), ("giriş kat", "giriş katı"),
    ("ara kat", "ara kat"), ("çatı kat", "çatı katı"), ("en üst kat", "en üst kat"),
    ("yüksek giriş", "yüksek giriş"), ("bahçe dubleks", "bahçe dubleks"),
]
_TIP_SOZ = [("müstakil", "müstakil"), ("dubleks", "dubleks"), ("dublex", "dubleks"),
            ("tripleks", "tripleks"), ("villa", "villa")]


def metinden_yas_kat(*metinler):
    """Mail / form serbest metninden bina yaşı + kat/tip çıkarımı (en iyi
    çaba — metinde yoksa '—'). Örn: '5 yaş / zemin kat', '≤10 yaş',
    '0-5 yaş / müstakil dubleks'. Mail kayıtlarında bu bilgi için ayrı bir
    sütun yok; bu yüzden metinden okunur ve detayda 'metinden' diye belirtilir."""
    m = tr_kucuk(" ".join(str(x) for x in metinler if x))[:4000]
    if not m:
        return "—"
    yas = ""
    a = _RE_ARALIK.search(m)
    if a:
        yas = f"{a.group(1)}-{a.group(2)} yaş"
    else:
        az = _RE_AZAMI.search(m) or _RE_AZAMI_ON.search(m)
        if az:
            yas = f"≤{az.group(1)} yaş"
        else:
            b = _RE_YAS_BINA.search(m) or _RE_YAS.search(m)
            if b:
                yas = "sıfır" if int(b.group(1)) == 0 else f"{b.group(1)} yaş"
            elif re.search(r"\bsıfır\s*(?:bina|daire|konut)|\byeni\s*bina|\bsıfır\b.*\bbina", m):
                yas = "sıfır"
    kat = ""
    for aranan, etiket in _KAT_SOZ:
        if aranan in m:
            kat = etiket
            break
    if not kat:
        n = _RE_KAT_NO.search(m)
        if n:
            kat = f"{n.group(1)}. kat"
    tipler = []
    for aranan, etiket in _TIP_SOZ:
        if aranan in m and etiket not in tipler:
            tipler.append(etiket)
    kat_tip = " ".join(x for x in [kat] + tipler if x)
    return " / ".join(x for x in [yas, kat_tip] if x) or "—"


# ── ADAPTÖRLER ──────────────────────────────────────────────────────
def _startkey(kesim, simdi):
    satirlar = _sayfalar(
        "izmir_pazar_ilanlar", "*",
        filtreler={"marka": "startkey", "aktif": True},
        tarih_alani="ilk_gorulme_tarihi", kesim_iso=kesim.isoformat(),
    )
    sonuc = []
    for v in satirlar:
        t = _zaman(v.get("ilk_gorulme_tarihi"))
        if not t or t < kesim:
            continue
        parca = [str(v.get(a)).strip() for a in ("mulk_tipi", "oda_sayisi") if v.get(a)]
        baslik = " · ".join(parca) or "Startkey ilanı"
        mah = (v.get("mahalle") or "").strip()
        alt = " · ".join(x for x in [mah, para(v.get("fiyat"))] if x)
        sonuc.append({
            "id": f"startkey:{v.get('id')}", "tur": "startkey", "baslik": baslik,
            "alt": alt, "zaman": t, "yeni": (simdi - t) <= timedelta(hours=24),
            "sahip": "", "kaynak": "Startkey ilanı (Revy)", "fiyat": para(v.get("fiyat")), "mahalle": mah,
            "ilce": (v.get("ilce") or "").strip(), "ilceler": [(v.get("ilce") or "").strip()],
            "link": v.get("ilan_linki") or "",
            "ham": v,
            "islem": islem_normal(v.get("islem_tipi")),
            "yas_kat": yas_kat_birlestir(yas_metni(v.get("bina_yasi")), v.get("kat")),
            "alanlar": [
                ("İşlem", islem_normal(v.get("islem_tipi"))),
                ("Bina yaşı", str(v.get("bina_yasi") or "")), ("Bulunduğu kat", str(v.get("kat") or "")),
                ("m²", str(v.get("m2") or "")),
                ("İlçe / mahalle", " / ".join(x for x in [(v.get("ilce") or ""), mah] if x)),
                ("Fiyat", para(v.get("fiyat"))),
                ("Mülk", baslik),
                ("İlk görülme", t.astimezone().strftime("%d.%m.%Y %H:%M")),
            ],
        })
    return sonuc


def _alici_talepleri(kesim, simdi):
    satirlar = _sayfalar(
        "alici_talepleri", "*",
        filtreler={"kategori": "alici_talebi", "parse_status": "parsed"},
    )
    sonuc = []
    for v in satirlar:
        # 09.10.2026 (Meltem): alıcı talebi / paylaşım bölge havuzunda MAİL
        # SİSTEMİNDEN gelen kayıtlar olmalı — Zeta paylaşımları tek başına
        # yetersiz, zamanla ön plana alınacak. Bu yüzden kaynak süzgeci YOK;
        # her kaydın kaynağı "Kaynak" alanında etiketli.
        t = _zaman(v.get("kayit_tarihi"), v.get("created_at"))
        if not t or t < kesim:
            continue
        sahip = (v.get("talep_eden_danisan") or "").strip()
        sonuc.append({
            "id": f"talep:{v.get('id')}", "tur": "talep",
            "baslik": v.get("ozet") or "Alıcı talebi",
            "alt": " · ".join(x for x in [v.get("bolge_mahalle") or "", v.get("oda_sayisi_m2") or "",
                                          ("bütçe " + para(v.get("max_butce"))) if para(v.get("max_butce")) else ""] if x),
            "zaman": t, "yeni": (simdi - t) <= timedelta(hours=24), "sahip": sahip, "kaynak": _kaynak_etiketi(v),
            "fiyat": para(v.get("max_butce")), "mahalle": v.get("bolge_mahalle") or "",
            "ilce": v.get("ilce") or "", "ilceler": _ilceler_of(v), "link": "",
            "ham": v,
            "islem": islem_normal(v.get("islem_tipi"), v.get("ozet")),
            "yas_kat": metinden_yas_kat(v.get("ozel_kriterler"), v.get("ozet"), v.get("mail_icerigi")),
            "alanlar": [
                ("Bina yaşı / kat (metinden)", metinden_yas_kat(v.get("ozel_kriterler"), v.get("ozet"), v.get("mail_icerigi"))),
                ("Kaynak", _kaynak_etiketi(v)), ("Talep eden", sahip), ("İşlem / mülk", " · ".join(x for x in [v.get("islem_tipi") or "", v.get("mulk_tipi") or ""] if x)),
                ("Bölge", v.get("bolge_mahalle") or ""), ("Oda / m²", v.get("oda_sayisi_m2") or ""),
                ("Azami bütçe", para(v.get("max_butce"))), ("Notlar", v.get("ozel_kriterler") or ""),
            ],
        })
    return sonuc


def _portfoy_kaydi(v, tur, t, simdi):
    sahip = (v.get("talep_eden_danisan") or "").strip()
    zeta = tur == "zeta"
    mah = (v.get("mahalle") or v.get("bolge_mahalle") or "").strip()
    if zeta:
        # Resmi Zeta portföyü (Revy'den senkronize): yapılandırılmış alanlar var.
        yas_kat = yas_kat_birlestir(yas_metni(v.get("bina_yasi")), v.get("kat"))
        alt = " · ".join(x for x in [mah, str(v.get("oda_sayisi_m2") or ""), para(v.get("fiyat"))] if x)
        alanlar = [
            ("Kaynak", _kaynak_etiketi(v)), ("Danışman", sahip),
            ("İşlem / mülk", " · ".join(x for x in [v.get("islem_tipi") or "", v.get("mulk_tipi") or "", v.get("mulk_turu") or ""] if x)),
            ("İlçe / mahalle", " / ".join(x for x in [v.get("ilce") or "", mah] if x)),
            ("Oda", v.get("oda_sayisi_m2") or ""), ("m²", str(v.get("m2") or "")),
            ("Fiyat", para(v.get("fiyat"))), ("Bina yaşı", str(v.get("bina_yasi") or "")),
            ("Bulunduğu kat", str(v.get("kat") or "")), ("Site içinde", str(v.get("site_icerisinde") or "")),
            ("Kullanım durumu", str(v.get("kullanim_durumu") or "")),
            ("Yayında (gün)", str(v.get("ilan_suresi") or "")),
        ]
    else:
        yas_kat = metinden_yas_kat(v.get("ozellikler"), v.get("ozet"), v.get("mail_icerigi"))
        alt = " · ".join(x for x in [mah, v.get("oda_sayisi_m2") or "", para(v.get("fiyat"))] if x)
        alanlar = [
            ("Bina yaşı / kat (metinden)", yas_kat),
            ("Kaynak", _kaynak_etiketi(v)), ("Paylaşan", sahip),
            ("İşlem / mülk", " · ".join(x for x in [v.get("islem_tipi") or "", v.get("mulk_tipi") or ""] if x)),
            ("Bölge", v.get("bolge_mahalle") or ""), ("Oda / m²", v.get("oda_sayisi_m2") or ""),
            ("Fiyat", para(v.get("fiyat"))), ("Notlar", v.get("ozellikler") or ""),
        ]
    return {
        "id": f"{tur}:{v.get('id')}", "tur": tur,
        "baslik": v.get("ozet") or ("Zeta portföyü" if zeta else "Portföy paylaşımı"),
        "alt": alt, "zaman": t, "yeni": bool(t and (simdi - t) <= timedelta(hours=24)), "sahip": sahip,
        "kaynak": _kaynak_etiketi(v), "fiyat": para(v.get("fiyat")), "mahalle": mah,
        "ilce": v.get("ilce") or "", "ilceler": _ilceler_of(v),
        "link": v.get("ilan_linki") or "",
        "ham": v,
        "islem": islem_normal(v.get("islem_tipi"), v.get("ozet")),
        "yas_kat": yas_kat,
        "alanlar": alanlar,
    }


def _portfoyler(kesim, simdi):
    """İki tür:
    - Paylaşım: mail sistemi + Zeta paylaşımı (dönem süzgeci uygulanır).
    - Zeta portföyü: portallarda yayındaki RESMİ ilanlar (kaynak zeta1/zeta2,
      aktif). Bunlar 'yeni gelen olay' değil, ofisin AKTİF STOKU olduğu için
      dönem süzgeci UYGULANMAZ; 'YENİ' rozeti son 24 saatte eklenenlere."""
    zeta_satirlar = _sayfalar(
        "portfoyler", "*", in_alani=("kaynak", ZETA_PORTFOY_KAYNAKLARI),
    )
    zeta = []
    for v in zeta_satirlar:
        if v.get("aktif") is False:
            continue
        t = _zaman(v.get("kayit_tarihi"), v.get("olusturma_tarihi"), v.get("created_at"))
        zeta.append(_portfoy_kaydi(v, "zeta", t, simdi))

    paylasim = []
    for v in _sayfalar("portfoyler", "*"):
        if tr_kucuk(v.get("kaynak")) in ZETA_PORTFOY_KAYNAKLARI:
            continue
        t = _zaman(v.get("kayit_tarihi"), v.get("created_at"))
        if not t or t < kesim:
            continue
        paylasim.append(_portfoy_kaydi(v, "paylasim", t, simdi))
    return paylasim, zeta


def _form_metin_ilceleri(metin, ilce_listesi):
    m = tr_kucuk(metin)
    return [i for i in ilce_listesi if m and tr_kucuk(i) in m]


def _musteri_formlari(kesim, simdi, ilce_listesi):
    """Dış besleme kanalı: musteri_talepleri (talep_tipi ile ayrışır)."""
    satirlar = _sayfalar(
        "musteri_talepleri", "*", in_alani=("talep_tipi", MUSTERI_FORM_KANALLARI.keys()),
    )
    sonuc = {k: [] for k in MUSTERI_FORM_KANALLARI}
    for v in satirlar:
        tip = v.get("talep_tipi")
        if tip not in sonuc:
            continue
        t = _zaman(v.get("created_at"), v.get("kayit_tarihi"))
        if not t or t < kesim:
            continue
        b1, b2 = v.get("oncelikli_bolge") or "", v.get("alternatif_bolge") or ""
        ilceler = _form_metin_ilceleri(b1, ilce_listesi)
        for i in _form_metin_ilceleri(b2, ilce_listesi):
            if i not in ilceler:
                ilceler.append(i)
        bmin, bmax = para(v.get("butce_min")), para(v.get("butce_max"))
        butce = " – ".join(x for x in [bmin, bmax] if x)
        ad = (v.get("musteri_adi") or "İsimsiz").strip()
        alanlar = [
            ("Müşteri", ad), ("Mülk türü", v.get("mulk_turu") or ""),
            ("Öncelikli bölge", b1), ("Alternatif bölge", b2), ("Bütçe", butce),
            ("Formu ilgilendiren danışman", v.get("danisman") or ""),
        ]
        det = v.get("detaylar")
        if isinstance(det, dict) and isinstance(det.get("alanlar"), list):
            for a in det["alanlar"][:40]:
                if isinstance(a, dict):
                    e, d = a.get("etiket") or a.get("label"), a.get("deger") or a.get("value")
                    if e and d:
                        alanlar.append((str(e), str(d)))
                elif isinstance(a, (list, tuple)) and len(a) >= 2 and a[0] and a[1]:
                    alanlar.append((str(a[0]), str(a[1])))
        form_metni = " ".join(f"{e} {d}" for e, d in alanlar)
        yas_kat = metinden_yas_kat(form_metni)
        alanlar.insert(5, ("Bina yaşı / kat (metinden)", yas_kat))
        sonuc[tip].append({
            "islem": "Satılık", "yas_kat": yas_kat, "kaynak": "Müşteri formu",
            "id": f"{tip}:{v.get('id')}", "tur": tip, "baslik": f"{ad} · {v.get('mulk_turu') or '—'}",
            "alt": " · ".join(x for x in [b1, butce] if x),
            "zaman": t, "yeni": (simdi - t) <= timedelta(hours=24),
            "sahip": (v.get("danisman") or "").strip(), "fiyat": butce, "mahalle": b1,
            "ilce": ilceler[0] if ilceler else "", "ilceler": ilceler, "link": "",
            "alanlar": alanlar,
        })
    return sonuc


# ── ANA GİRİŞ ───────────────────────────────────────────────────────
def sekme_tanimlari():
    """Gösterim sırası: [(anahtar, ad, kısa, renk)]. Dış kanallar sona eklenir."""
    t = [
        ("startkey", "Startkey ilanı", "Startkey ilanı", "indigo"),
        ("talep", "Alıcı talebi", "alıcı talebi", "violet"),
        ("paylasim", "Paylaşım", "paylaşım", "orange"),
        ("zeta", "Zeta portföyü", "Zeta portföyü", "sky"),
    ]
    for k, c in MUSTERI_FORM_KANALLARI.items():
        t.append((k, c["ad"], c["kisa"], c["renk"]))
    return t


def havuzu_yukle(gun, ilce_listesi, simdi=None):
    """{tur: [kayıt, ...]} — tüm ilçeler, son `gun` gün. Hata veren
    kaynak tüm sayfayı çökertmez: {tur: [...]} yanında hatalar sözlüğü döner."""
    simdi = simdi or datetime.now(timezone.utc)
    kesim = simdi - timedelta(days=gun)
    havuz = {k: [] for k, *_ in sekme_tanimlari()}
    hatalar = {}

    def dene(ad, fn):
        try:
            return fn()
        except Exception as e:     # noqa: BLE001 — sayfa kaynak hatasında da açılsın
            hatalar[ad] = str(e)
            return None

    r = dene("Startkey ilanı", lambda: _startkey(kesim, simdi))
    if r is not None:
        havuz["startkey"] = r
    r = dene("Alıcı talebi", lambda: _alici_talepleri(kesim, simdi))
    if r is not None:
        havuz["talep"] = r
    r = dene("Portföyler", lambda: _portfoyler(kesim, simdi))
    if r is not None:
        havuz["paylasim"], havuz["zeta"] = r
    r = dene("Müşteri formları", lambda: _musteri_formlari(kesim, simdi, ilce_listesi))
    if r is not None:
        for k, liste in r.items():
            havuz[k] = liste
    for liste in havuz.values():
        liste.sort(key=lambda x: x["zaman"] or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    return havuz, hatalar


def ilceye_gore(havuz, ilce):
    """İlçe seçimine göre süz. ilce=None -> hepsi. ILCE_BELIRSIZ -> hiçbir
    ilçeyle eşleşmeyenler. Kayıt birden çok ilçeye bağlıysa her birinde görünür."""
    sonuc = {}
    for tur, liste in havuz.items():
        if ilce is None:
            sonuc[tur] = list(liste)
        elif ilce == ILCE_BELIRSIZ:
            sonuc[tur] = [k for k in liste if not [i for i in k["ilceler"] if i]]
        else:
            h = tr_kucuk(ilce)
            sonuc[tur] = [k for k in liste if any(tr_kucuk(i) == h for i in k["ilceler"])]
    return sonuc


def ilce_sayilari(havuz):
    """{ilçe: {tur: adet}} + ilçe belirsiz kovası."""
    sayi = {}
    for tur, liste in havuz.items():
        for k in liste:
            ilceler = [i for i in k["ilceler"] if i] or [ILCE_BELIRSIZ]
            for i in ilceler:
                sayi.setdefault(i, {}).setdefault(tur, 0)
                sayi[i][tur] += 1
    return sayi


def mesaj_onizleme(tur, kayit):
    kisa = {t[0]: t[2] for t in sekme_tanimlari()}.get(tur, "kayıt")
    parca = kayit["baslik"] + (f" · {kayit['fiyat']}" if kayit.get("fiyat") and tur in ("startkey", "zeta") else "")
    on = "Bölgende yeni " + kisa
    return f"{on}: {parca}"


def alicilar(tur, kayit, takipciler, ilce):
    """Bu kayıt için bildirim kimlere giderdi — YALNIZCA SİMÜLASYON.
    takipciler: admin sayfasının `_takipci_kayitlari()` çıktısı.
    Startkey: ilçe + mahalle kapsamındaki Startkey takipçileri + ilçe uzmanları.
    Diğer türler: ilçe uzmanları (kayıt sahibi hariç). Kayıt sahibine asla gitmez."""
    sahip = tr_kucuk(kayit.get("sahip"))
    mah = (kayit.get("mahalle") or "").strip()
    sonuc = {}

    def ekle(ad, neden, bildirim):
        if tr_kucuk(ad) == sahip:
            return
        s = sonuc.setdefault(ad, {"ad": ad, "nedenler": [], "bildirim": False})
        if neden not in s["nedenler"]:
            s["nedenler"].append(neden)
        if bildirim:           # en az bir kapsamda bildirim açıksa gider
            s["bildirim"] = True

    for t in takipciler:
        if tr_kucuk(t["ilce"]) != tr_kucuk(ilce):
            continue
        if t["tur"] == "uzmanlik":
            ekle(t["ad"], "ilçe uzmanı", t["bildirim"])
        elif t["tur"] == "startkey" and tur == "startkey":
            if not t["mahalleler"]:
                ekle(t["ad"], "Startkey takibi (tüm ilçe)", t["bildirim"])
            elif mah and mah in t["mahalleler"]:
                ekle(t["ad"], "Startkey takibi (bu mahalle)", t["bildirim"])
    return sorted(sonuc.values(), key=lambda x: tr_kucuk(x["ad"]))
