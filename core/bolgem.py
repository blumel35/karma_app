"""
core/bolgem.py

"Radarım" ekranı (eski adı Bölgem; danışmanın kendi kayıtları + bölgelerindeki tüm kayıtlar tek panelde) — veri katmanı.
SALT OKUNUR. Bölge Havuzu (core/bolge_havuzu.py) okuyucularını yeniden kullanır;
yeni puan/eşleşme mantığı YOK (eşleşme bilinçli olarak kapsam dışı, 11.10.2026).

Sıra (Meltem'in istediği): Alıcı taleplerim · Portföylerim · Alıcı talebi · Paylaşım ·
Zeta portföyü · Startkey ilanı · FSBO ilanı · Yatırım talebim.

Veri kapsamı (12.10.2026 kararları):
  - Alıcı taleplerim / Portföylerim / Yatırım talebim: danışmanın KENDİ kayıtları, TÜM ilçelerden ve DÖNEMDEN
    BAĞIMSIZ (ad varyantlarıyla sunucu tarafında süzülür). Portföylerim = kendi paylaşımları + kendi Zeta portföyü.
  - Ekip kayıtları (Alıcı talebi / Paylaşım / Zeta / Startkey / FSBO): ilçe kapsamı = Uzmanlık Bölgelerim (en fazla 5)
    + kendi kayıtlarının bulunduğu ilçeler. Alıcı talebi/Paylaşım/Startkey/FSBO dönemle süzülür, Zeta aktif stoktur.
    Startkey/FSBO yalnız kapsamdaki ilçeler için SUNUCU tarafında okunur (üst sınıra takılmaz).
  - Yatırım talebi: YALNIZ atanan danışmana görünür (musteri_talepleri sunucu tarafında kişiye süzülür; başkasının
    kişisel verisi hiç okunmaz).
"""
from datetime import datetime, timedelta, timezone

from core import bolge_havuzu as bh

# (anahtar, ad, kısa, renk) — gösterim sırası
TURLER = [
    ("taleplerim", "Alıcı taleplerim", "alıcı talebim", "violet"),
    ("portfoylerim", "Portföylerim", "portföyüm", "sky"),
    ("talep", "Alıcı talebi", "alıcı talebi", "violet"),
    ("paylasim", "Paylaşım", "paylaşım", "orange"),
    ("zeta", "Zeta portföyü", "Zeta portföyü", "sky"),
    ("startkey", "Startkey ilanı", "Startkey ilanı", "indigo"),
    ("fsbo", "FSBO ilanı", "FSBO ilanı", "emerald"),
    ("yatirim", "Yatırım talebim", "yatırım talebim", "teal"),
]
DONEMLER = {"Son 24 saat": 1, "Son 7 gün": 7, "Son 30 gün": 30, "Son 90 gün": 90}
BOLGE_DISI = "(İlçesi belli değil)"
TUM_BOLGELER = "(Tümü)"

_TR_SIRA = "abcçdefgğhıijklmnoöprsştuüvyz"


def tr_sira(metin):
    """Türkçe alfabe sırası için anahtar."""
    m = bh.tr_kucuk(metin)
    return [(_TR_SIRA.index(c) if c in _TR_SIRA else 100 + ord(c)) for c in m]


def _utc_simdi():
    return datetime.now(timezone.utc)


# ── YÜKLEME (önbelleğe sayfa tarafında alınır) ───────────────────────────
def ortak_yukle(gun, simdi=None):
    """Ekip geneli: alıcı talebi, paylaşım, Zeta portföyü (bayat dahil, işaretli).
    Dönüş: ({'talep','paylasim','zeta'}, hatalar)."""
    simdi = simdi or _utc_simdi()
    kesim = simdi - timedelta(days=gun)
    hatalar, veri = {}, {"talep": [], "paylasim": [], "zeta": []}
    try:
        veri["talep"] = bh._alici_talepleri(kesim, simdi)
    except Exception as e:      # noqa: BLE001
        hatalar["Alıcı talebi"] = str(e)
    try:
        veri["paylasim"], veri["zeta"] = bh._portfoyler(kesim, simdi)
    except Exception as e:      # noqa: BLE001
        hatalar["Portföyler"] = str(e)
    return veri, hatalar


def pazar_yukle(gun, ilceler, simdi=None):
    """Startkey + FSBO ilanları — yalnız verilen ilçeler (sunucu tarafı süzgeç)."""
    simdi = simdi or _utc_simdi()
    kesim = simdi - timedelta(days=gun)
    ilceler = [i for i in ilceler if i]
    hatalar, veri = {}, {"startkey": [], "fsbo": []}
    for anahtar, ad, fn in (("startkey", "Startkey ilanı", bh._startkey), ("fsbo", "FSBO ilanı", bh._fsbo)):
        try:
            veri[anahtar] = fn(kesim, simdi, ilceler)
        except Exception as e:      # noqa: BLE001
            hatalar[ad] = str(e)
    return veri, hatalar


def kendi_yukle(danisman_adlari, simdi=None):
    """Danışmanın KENDİ alıcı talepleri ve portföy paylaşımları — tüm zamanlar, tüm ilçeler.
    (Kendi Zeta portföyü ekip stokundan, ortak_yukle'den gelir.)  Dönüş: ({'talep','paylasim'}, hatalar)"""
    simdi = simdi or _utc_simdi()
    eski = simdi - timedelta(days=3650)
    adlar = [a for a in danisman_adlari if a and str(a).strip()]
    hatalar, veri = {}, {"talep": [], "paylasim": []}
    if not adlar:
        return veri, hatalar
    try:
        veri["talep"] = bh._alici_talepleri(eski, simdi, danisman_adlari=adlar)
    except Exception as e:      # noqa: BLE001
        hatalar["Alıcı taleplerim"] = str(e)
    try:
        veri["paylasim"] = bh._paylasimlar_kisi(adlar, eski, simdi)
    except Exception as e:      # noqa: BLE001
        hatalar["Portföy paylaşımlarım"] = str(e)
    return veri, hatalar


def yatirim_yukle(danisman_adlari, ilce_listesi, simdi=None):
    """Danışmanın KENDİ yatırım talepleri (dönemden bağımsız; hepsi). Sunucu tarafında kişiye süzülür."""
    simdi = simdi or _utc_simdi()
    adlar = [a for a in danisman_adlari if a and str(a).strip()]
    if not adlar:
        return [], {}
    try:
        r = bh._musteri_formlari(simdi - timedelta(days=3650), simdi, list(ilce_listesi), danisman_adlari=adlar)
        return r.get("yatirim_alici", []), {}
    except Exception as e:      # noqa: BLE001
        return [], {"Yatırım talebi": str(e)}


# ── KİŞİ / BÖLGE YARDIMCILARI ────────────────────────────────────────────
def benim_mi(kayit, adlar):
    """Kaydın sahibi (talep eden / paylaşan danışman) bu kişinin ad varyantlarından biri mi."""
    sahip = bh.tr_kucuk(kayit.get("sahip"))
    return bool(sahip) and sahip in {bh.tr_kucuk(a) for a in adlar if a}


def _ilce_kumesi(ilceler):
    return {bh.tr_kucuk(i) for i in ilceler if i}


def bolgede_mi(kayit, ilce_kumesi):
    """Kaydın ilçelerinden biri küme içinde mi (küme boşsa hayır)."""
    return any(bh.tr_kucuk(i) in ilce_kumesi for i in kayit.get("ilceler") or [] if i)


def kendi_kayitlar(ortak, kendi, yatirim, adlar):
    """Kişinin kendi üç listesi (ilçe/dönem süzgeci yok). Kendi Zeta ilanları (bayat dahil, işaretli) ekip
    stokundan alınır."""
    zeta_kendi = [k for k in ortak["zeta"] if benim_mi(k, adlar)]
    return {
        "taleplerim": _sirala(kendi["talep"]),
        "portfoylerim": _sirala(kendi["paylasim"] + zeta_kendi),
        "yatirim": _sirala(list(yatirim)),
    }


def kapsam_ilceleri(bolgeler, kendi_listeler, ilce_listesi=None, ust_sinir=12):
    """Ekip kayıtlarının gösterileceği ilçeler: Uzmanlık bölgeleri (sıra korunur) + kendi kayıtlarının
    bulunduğu ilçeler (kayıt sayısı çoksa önce). Dönüş: (ilçeler, ek_ilceler)"""
    gorulen = {bh.tr_kucuk(i): i for i in bolgeler if i}
    sayim = {}
    for liste in kendi_listeler.values():
        for k in liste:
            for i in {i for i in k.get("ilceler") or [] if i and bh.tr_kucuk(i) in bh._ILCE_ANAHTAR}:
                sayim[i] = sayim.get(i, 0) + 1
    ek = []
    for i, _n in sorted(sayim.items(), key=lambda x: (-x[1], tr_sira(x[0]))):
        if bh.tr_kucuk(i) not in gorulen and len(gorulen) < ust_sinir:
            gorulen[bh.tr_kucuk(i)] = i
            ek.append(i)
    return list(gorulen.values()), ek


def _sirala(liste):
    return sorted(liste, key=lambda x: x["zaman"] or datetime.min.replace(tzinfo=timezone.utc), reverse=True)


def kayitlari_kur(ortak, pazar, kendi_liste, ilceler):
    """Ekranın listeleri. Dönüş: ({tür: [kayıt]}, bilgi)
    Ekip listeleri (talep/paylasim/zeta) kapsamdaki ilçelerle sınırlı; kendi listeleri (kendi_kayitlar çıktısı)
    ilçe/dönem fark etmeksizin tam. Bayat (yayından kalkmış olabilecek) Zeta ilanları ekip listesinde yok."""
    kume = _ilce_kumesi(ilceler)
    zeta_hepsi = ortak["zeta"]
    zeta_taze = [k for k in zeta_hepsi if not k.get("bayat")]
    bayat_bolgede = [k for k in zeta_hepsi if k.get("bayat") and bolgede_mi(k, kume)]
    liste = {
        "talep": _sirala([k for k in ortak["talep"] if bolgede_mi(k, kume)]),
        "paylasim": _sirala([k for k in ortak["paylasim"] if bolgede_mi(k, kume)]),
        "zeta": _sirala([k for k in zeta_taze if bolgede_mi(k, kume)]),
        "startkey": _sirala(pazar["startkey"]),
        "fsbo": _sirala(pazar["fsbo"]),
        **kendi_liste,
    }
    liste = {k: liste[k] for k, *_ in TURLER}
    return liste, {"bayat_bolgede": len(bayat_bolgede)}


def ilceye_gore(liste, secim, ilceler):
    """secim: TUM_BOLGELER | BOLGE_DISI | bir ilçe adı.
    TUM_BOLGELER: ekip listeleri zaten bölgelerle sınırlı, kendi listeleri tam.
    BOLGE_DISI: yalnız kendi kayıtları, bölgelerin dışında kalanlar.
    İlçe: tüm listeler o ilçeyle süzülür."""
    kume = _ilce_kumesi(ilceler)
    ekip = ("talep", "paylasim", "zeta", "startkey", "fsbo")
    if secim == TUM_BOLGELER:
        return {k: list(v) for k, v in liste.items()}
    if secim == BOLGE_DISI:
        sonuc = {k: [] for k in liste}
        for k in ("taleplerim", "portfoylerim", "yatirim"):
            sonuc[k] = [x for x in liste[k] if not bolgede_mi(x, kume)]
        return sonuc
    h = bh.tr_kucuk(secim)
    sonuc = {}
    for k, v in liste.items():
        sonuc[k] = [x for x in v if any(bh.tr_kucuk(i) == h for i in x.get("ilceler") or [] if i)]
    return sonuc


def ilce_sayilari(liste, ilceler):
    """{ilçe: {tür: adet}} — yalnız kişinin ilçeleri + bölge dışı kovası (yalnız kendi kayıtları).
    Bir kayıt birden çok ilçeyi kapsıyorsa her birinde sayılır."""
    sayi = {i: {k: 0 for k, *_ in TURLER} for i in ilceler}
    anahtar = {bh.tr_kucuk(i): i for i in ilceler}
    for tur, kayitlar in liste.items():
        for k in kayitlar:
            for i in {bh.tr_kucuk(x) for x in k.get("ilceler") or [] if x}:
                if i in anahtar:
                    sayi[anahtar[i]][tur] += 1
    dis = {k: 0 for k, *_ in TURLER}
    for tur in ("taleplerim", "portfoylerim", "yatirim"):
        dis[tur] = sum(1 for k in liste[tur] if not bolgede_mi(k, set(anahtar)))
    return sayi, dis


# ── GÖSTERİM YARDIMCILARI ────────────────────────────────────────────────
def bayat_sayisi(ortak, ilce_listesi):
    """Verilen ilçelerde, Revy senkronunda görünmediği için ekip listesinden çıkarılan Zeta ilanı sayısı."""
    kume = _ilce_kumesi(ilce_listesi)
    return sum(1 for k in ortak["zeta"] if k.get("bayat") and bolgede_mi(k, kume))


def kaynak_metni(k):
    """Takip için 'ne + ne zaman': 'Startkey maili · 09.10.2026'. Tarihin anlamı kaynağa göre değişir:
    mail/paylaşım = kayıt tarihi, Zeta portföyü = kayıt tarihi, Startkey/FSBO ilanı = sisteme ilk girdiği tarih."""
    tur = k.get("tur")
    tarih = bh.tarih_metni(k.get("zaman"))
    if tur in ("startkey", "fsbo"):
        etiket = "Startkey ilanı" if tur == "startkey" else "FSBO ilanı"
        return f"{etiket} · ilk görüldü {tarih}" if tarih else etiket
    if tur == "zeta":
        etiket = "Zeta portföyü"
    elif tur == "yatirim_alici":
        etiket = "Müşteri formu"
    else:
        etiket = k.get("kaynak") or "—"
        if etiket == "Mail sistemi":
            etiket = "Startkey maili" if bh.tr_kucuk((k.get("ham") or {}).get("kaynak")) == "startkey" else "Mail"
        elif etiket.startswith("Zeta paylaşımı"):
            etiket = "Zeta paylaşımı"
    return f"{etiket} · {tarih}" if tarih else etiket
