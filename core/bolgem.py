"""
core/bolgem.py

"Bölgem" ekranı (danışmanın kendi bölgelerindeki tüm kayıtlar tek panelde) — veri katmanı.
SALT OKUNUR. Bölge Havuzu (core/bolge_havuzu.py) okuyucularını yeniden kullanır;
yeni puan/eşleşme mantığı YOK (eşleşme bilinçli olarak kapsam dışı, 11.10.2026).

Sıra (Meltem'in istediği): Alıcı taleplerim · Portföylerim · Alıcı talebi · Paylaşım ·
Zeta portföyü · Startkey ilanı · FSBO ilanı · Yatırım talebim.

Veri kapsamı:
  - Alıcı talebi / Paylaşım / Zeta portföyü: ekibin kayıtları, danışmanın bölgelerine (ilçelerine) göre
    süzülür. Tüm danışmanlar için ORTAK önbellekten gelir (kişiye özel bir şey içermez).
  - Startkey / FSBO ilanı: yalnız danışmanın ilçeleri için SUNUCU tarafında okunur (üst sınıra takılmaz).
  - Alıcı taleplerim / Portföylerim: danışmanın kendi kayıtları (ad varyantlarıyla); bölge dışı olanlar dahil.
    Portföylerim = kendi Zeta portföyü (Revy ilanları) + kendi portföy paylaşımları.
  - Yatırım talebim: musteri_talepleri'nden YALNIZ o danışmana ait kayıtlar (sunucu tarafında süzülür;
    başkasının kişisel verisi hiç okunmaz).
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
BOLGE_DISI = "(Bölgelerim dışı)"
TUM_BOLGELER = "(Tüm bölgelerim)"

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


def kayitlari_kur(ortak, pazar, yatirim, ilceler, adlar):
    """Ekranın listeleri. Dönüş: ({tür: [kayıt]}, bilgi)
    Ekip listeleri (talep/paylasim/zeta) bölgelerle sınırlı; kendi listeleri (taleplerim/portfoylerim)
    bölge dışı olanlar dahil TÜM kendi kayıtlarıdır. Bayat (yayından kalkmış olabilecek) Zeta ilanları
    ekip listesinde yok; kişinin kendi ilanlarında uyarı işaretiyle görünür."""
    kume = _ilce_kumesi(ilceler)
    zeta_hepsi = ortak["zeta"]
    zeta_taze = [k for k in zeta_hepsi if not k.get("bayat")]
    bayat_bolgede = [k for k in zeta_hepsi if k.get("bayat") and bolgede_mi(k, kume)]
    sirala = lambda l: sorted(l, key=lambda x: x["zaman"] or datetime.min.replace(tzinfo=timezone.utc), reverse=True)  # noqa: E731
    liste = {
        "taleplerim": sirala([k for k in ortak["talep"] if benim_mi(k, adlar)]),
        "portfoylerim": sirala([k for k in ortak["paylasim"] + zeta_hepsi if benim_mi(k, adlar)]),
        "talep": sirala([k for k in ortak["talep"] if bolgede_mi(k, kume)]),
        "paylasim": sirala([k for k in ortak["paylasim"] if bolgede_mi(k, kume)]),
        "zeta": sirala([k for k in zeta_taze if bolgede_mi(k, kume)]),
        "startkey": sirala(pazar["startkey"]),
        "fsbo": sirala(pazar["fsbo"]),
        "yatirim": sirala(list(yatirim)),
    }
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
