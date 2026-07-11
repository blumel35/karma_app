# core/portfoy_gorunurluk.py
# -*- coding: utf-8 -*-
"""
Portföy Görünürlük Sınıflandırması

Amaç:
- Portföy Merkezi'ndeki mail kaynaklı / manuel portföy kayıtlarını
  "kapalı", "ilandaki", "maille paylaşılmış", "çoklu link", "teyit gerekli"
  olarak sınıflandırmak.
- İlan linki alanı boş olsa bile mail içeriği / özet / özel kriterlerden
  gerçek ilan linklerini yakalamak.
- Mail imzası, avatar, görsel ve sosyal medya linklerini ilan linki saymamak.
- Startkey/Revy merkezi ilan tablosu ile mükerrerlik / eşleşme kontrolüne zemin hazırlamak.

Bu dosya DB'ye yazmaz.
Backfill veya sayfa entegrasyonu bu fonksiyonların ürettiği sözlüğü Supabase'e yazar.
"""

from __future__ import annotations

import re
from urllib.parse import urlparse, urlunparse
from difflib import SequenceMatcher
from typing import Any, Dict, Iterable, List, Optional, Tuple


# ─────────────────────────────────────────────
# Görünürlük sınıfları
# ─────────────────────────────────────────────

GORUNURLUK_KAPALI = "kapali_portfoy"
GORUNURLUK_ILANDA = "ilandaki_portfoy"
GORUNURLUK_MAIL_PAYLASIM = "maille_paylasilmis_ilan"
GORUNURLUK_COKLU = "coklu_ilan_maili"
GORUNURLUK_TEYIT = "teyit_gerekli"

GORUNURLUK_ETIKET = {
    GORUNURLUK_KAPALI: "🔒 Kapalı Portföy",
    GORUNURLUK_ILANDA: "↗ İlandaki Portföy",
    GORUNURLUK_MAIL_PAYLASIM: "✉ Maille Paylaşılmış İlan",
    GORUNURLUK_COKLU: "🔗 Çoklu İlan Maili",
    GORUNURLUK_TEYIT: "? Teyit Gerekli",
}

GORUNURLUK_ONCELIK = {
    GORUNURLUK_KAPALI: 1,
    GORUNURLUK_TEYIT: 2,
    GORUNURLUK_MAIL_PAYLASIM: 3,
    GORUNURLUK_ILANDA: 4,
    GORUNURLUK_COKLU: 5,
}


# ─────────────────────────────────────────────
# URL sınıflandırma ayarları
# ─────────────────────────────────────────────

# Gerçek ilan/portal sayılacak domain anahtarları
PORTAL_DOMAIN_KEYWORDS = {
    "sahibinden": "sahibinden",
    "hepsiemlak": "hepsiemlak",
    "emlakjet": "emlakjet",
    "zingat": "zingat",
    "milliyetemlak": "milliyetemlak",
    "hurriyetemlak": "hurriyetemlak",
    "startkey": "startkey",
    "revy": "revy",
}

# Mail imzası / avatar / sosyal medya / görsel gibi ilan linki olmayan URL'ler
IGNORED_URL_DOMAIN_KEYWORDS = {
    "avatars.mds.yandex.net",
    "yandex.net/get-mail-signature",
    "mail-signature",
    "googleusercontent.com",
    "gravatar.com",
    "facebook.com",
    "fb.com",
    "instagram.com",
    "linkedin.com",
    "youtube.com",
    "youtu.be",
    "x.com",
    "twitter.com",
    "tiktok.com",
    "whatsapp.com",
    "wa.me",
}

IGNORED_URL_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".webp",
    ".svg",
    ".ico",
    ".pdf",  # broşür olabilir ama ilan linki değildir; gerekirse ileride ayrı ele alınır
}

URL_RE = re.compile(
    r"""
    (?:
        https?://[^\s<>"')\]]+
        |
        www\.[^\s<>"')\]]+
    )
    """,
    re.IGNORECASE | re.VERBOSE,
)

TRAILING_PUNCT = ".,;:!?)\"]}'”’"


# ─────────────────────────────────────────────
# Genel yardımcılar
# ─────────────────────────────────────────────

def _safe_str(v: Any) -> str:
    if v is None:
        return ""
    return str(v).strip()


def _lower_tr(v: Any) -> str:
    s = _safe_str(v)
    return (
        s.replace("İ", "i")
        .replace("I", "ı")
        .lower()
        .strip()
    )


def _digits(v: Any) -> str:
    return re.sub(r"\D+", "", _safe_str(v))


def sayisal_fiyat(v: Any) -> Optional[int]:
    d = _digits(v)
    if not d:
        return None
    try:
        return int(d)
    except Exception:
        return None


def normalize_text(v: Any) -> str:
    s = _lower_tr(v)
    s = re.sub(r"https?://\S+|www\.\S+", " ", s)
    s = re.sub(r"[^a-z0-9çğıöşü\s]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def benzerlik(a: Any, b: Any) -> float:
    aa = normalize_text(a)
    bb = normalize_text(b)
    if not aa or not bb:
        return 0.0
    return SequenceMatcher(None, aa, bb).ratio()


# ─────────────────────────────────────────────
# URL çıkarma / normalize etme
# ─────────────────────────────────────────────

def temizle_url(url: str) -> str:
    u = _safe_str(url)
    while u and u[-1] in TRAILING_PUNCT:
        u = u[:-1]
    if u.startswith("www."):
        u = "https://" + u
    return u.strip()


def normalize_url(url: str) -> str:
    """
    URL karşılaştırması için sadeleştirir.
    Query string / fragment atılır.
    Domain lowercase yapılır.
    Sonda / kaldırılır.
    """
    u = temizle_url(url)
    if not u:
        return ""

    try:
        p = urlparse(u)
        scheme = p.scheme or "https"
        netloc = (p.netloc or "").lower()

        if netloc.startswith("www."):
            netloc = netloc[4:]

        path = re.sub(r"/+", "/", p.path or "").rstrip("/")

        return urlunparse((scheme, netloc, path, "", "", ""))
    except Exception:
        return u.lower().rstrip("/")


def url_domain(url: str) -> str:
    try:
        p = urlparse(temizle_url(url))
        netloc = (p.netloc or "").lower()
        if netloc.startswith("www."):
            netloc = netloc[4:]
        return netloc
    except Exception:
        return ""


def domain_tipi_bul(url: str) -> str:
    d = url_domain(url)
    for key, label in PORTAL_DOMAIN_KEYWORDS.items():
        if key in d:
            return label
    return "diger"


def url_ignored_mi(url: str) -> bool:
    """
    Mail imzası, avatar, görsel dosya, sosyal medya vb.
    ilan linki olmayan URL'leri eler.
    """
    u = normalize_url(url).lower()
    d = url_domain(u).lower()

    if not u:
        return True

    for bad in IGNORED_URL_DOMAIN_KEYWORDS:
        if bad in u or bad in d:
            return True

    parsed_path = urlparse(u).path.lower()
    for ext in IGNORED_URL_EXTENSIONS:
        if parsed_path.endswith(ext):
            return True

    return False


def url_ilan_linki_mi(url: str) -> bool:
    """
    Gerçek ilan/portal linki sayılabilecek URL'leri belirler.
    Bilerek konservatif tutuldu: bilinmeyen domainleri ilan saymaz.
    """
    if url_ignored_mi(url):
        return False

    domain_tipi = domain_tipi_bul(url)

    if domain_tipi in {
        "sahibinden",
        "hepsiemlak",
        "emlakjet",
        "zingat",
        "milliyetemlak",
        "hurriyetemlak",
        "startkey",
        "revy",
    }:
        return True

    return False


def ilan_id_cikar(url: str) -> str:
    """
    Portal linkinden mümkünse ilan ID çıkarır.
    Özellikle sahibinden linklerinde sondaki uzun sayıyı yakalar.
    """
    u = normalize_url(url)
    if not u:
        return ""

    nums = re.findall(r"\d{6,}", u)
    if nums:
        return nums[-1]

    return ""


def metinlerden_url_cikar(*metinler: Any) -> List[Dict[str, Any]]:
    """
    Verilen metinlerden gerçek ilan/portal URL'lerini çıkarır.
    Mail imzası, avatar, görsel, sosyal medya vb. linkleri yok sayar.
    Tekrarlı normalize URL'leri tekilleştirir.
    """
    bulunan: List[Dict[str, Any]] = []
    seen = set()

    for metin in metinler:
        text = _safe_str(metin)
        if not text:
            continue

        for m in URL_RE.finditer(text):
            raw = temizle_url(m.group(0))
            norm = normalize_url(raw)

            if not norm:
                continue

            if url_ignored_mi(norm):
                continue

            if not url_ilan_linki_mi(norm):
                continue

            if norm in seen:
                continue

            seen.add(norm)

            bulunan.append({
                "url": raw,
                "normalized_url": norm,
                "domain": url_domain(norm),
                "domain_tipi": domain_tipi_bul(norm),
                "ilan_id": ilan_id_cikar(norm),
            })

    return bulunan


def portfoy_metinleri(kayit: Dict[str, Any]) -> List[str]:
    """
    Link ve sınıflandırma için taranacak alanlar.
    """
    alanlar = [
        "ilan_linki",
        "primary_ilan_linki",
        "mail_icerigi",
        "mail_konusu",
        "ozet",
        "ozel_kriterler",
        "not_alani",
        "bolge",
        "bolge_mahalle",
    ]
    return [_safe_str(kayit.get(a, "")) for a in alanlar if _safe_str(kayit.get(a, ""))]


# ─────────────────────────────────────────────
# Merkezi ilan eşleştirme
# ─────────────────────────────────────────────

def merkezi_ilan_link_seti(merkezi_ilanlar: Iterable[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """
    izmir_pazar_ilanlar gibi merkezi ilan listesinden normalize URL index'i üretir.
    """
    index: Dict[str, Dict[str, Any]] = {}

    for row in merkezi_ilanlar or []:
        link = (
            row.get("ilan_linki")
            or row.get("link")
            or row.get("url")
            or row.get("primary_ilan_linki")
            or ""
        )
        norm = normalize_url(link)
        if norm and url_ilan_linki_mi(norm):
            index[norm] = row

    return index


def linkten_merkezi_eslesme(
    linkler: List[Dict[str, Any]],
    merkezi_ilanlar: Optional[Iterable[Dict[str, Any]]] = None,
) -> Tuple[bool, Optional[Dict[str, Any]], str]:
    """
    Önce normalize URL, sonra ilan_id ile eşleştirir.
    """
    if not merkezi_ilanlar:
        return False, None, ""

    merkezi_liste = list(merkezi_ilanlar or [])
    url_index = merkezi_ilan_link_seti(merkezi_liste)

    # 1. Normalize URL birebir
    for l in linkler:
        norm = l.get("normalized_url") or ""
        if norm and norm in url_index:
            row = url_index[norm]
            return True, row, _safe_str(row.get("id") or row.get("ilan_id") or row.get("revy_id") or "")

    # 2. İlan ID eşleşmesi
    link_ids = {l.get("ilan_id") for l in linkler if l.get("ilan_id")}
    if link_ids:
        for row in merkezi_liste:
            row_link = (
                row.get("ilan_linki")
                or row.get("link")
                or row.get("url")
                or ""
            )
            row_id = _safe_str(row.get("ilan_id") or row.get("revy_id") or "")
            row_link_id = ilan_id_cikar(row_link)

            if row_id and row_id in link_ids:
                return True, row, _safe_str(row.get("id") or row_id)
            if row_link_id and row_link_id in link_ids:
                return True, row, _safe_str(row.get("id") or row.get("ilan_id") or row.get("revy_id") or "")

    return False, None, ""


def fuzzy_merkezi_eslesme(
    kayit: Dict[str, Any],
    merkezi_ilanlar: Optional[Iterable[Dict[str, Any]]] = None,
) -> Tuple[bool, Optional[Dict[str, Any]], str, float]:
    """
    Link yoksa zayıf/orta güvenli eşleştirme.
    İlçe + fiyat + oda/m2 + özet benzerliği üzerinden kaba skor üretir.

    Bu fonksiyon kapalı portföyü yanlışlıkla ilandaki portföye çevirmemek için
    konservatif tutuldu.
    """
    if not merkezi_ilanlar:
        return False, None, "", 0.0

    k_ilce = normalize_text(kayit.get("ilce") or "")
    k_mahalle = normalize_text(kayit.get("mahalle") or "")
    k_fiyat = sayisal_fiyat(kayit.get("fiyat"))
    k_oda = normalize_text(kayit.get("oda_sayisi_m2") or "")
    k_ozet = normalize_text(
        " ".join([
            _safe_str(kayit.get("ozet")),
            _safe_str(kayit.get("ozel_kriterler")),
            _safe_str(kayit.get("mail_konusu")),
        ])
    )

    best_row = None
    best_score = 0.0

    for row in merkezi_ilanlar or []:
        score = 0.0

        r_ilce = normalize_text(row.get("ilce") or "")
        r_mahalle = normalize_text(row.get("mahalle") or "")
        r_fiyat = sayisal_fiyat(row.get("fiyat"))
        r_oda = normalize_text(row.get("oda_sayisi") or row.get("oda_sayisi_m2") or "")
        r_ozet = normalize_text(
            " ".join([
                _safe_str(row.get("baslik")),
                _safe_str(row.get("ozet")),
                _safe_str(row.get("aciklama")),
                _safe_str(row.get("mulk_turu")),
            ])
        )

        if k_ilce and r_ilce and k_ilce == r_ilce:
            score += 30

        if k_mahalle and r_mahalle and (
            k_mahalle == r_mahalle or k_mahalle in r_mahalle or r_mahalle in k_mahalle
        ):
            score += 20

        if k_fiyat and r_fiyat:
            fark_oran = abs(k_fiyat - r_fiyat) / max(k_fiyat, r_fiyat)
            if fark_oran <= 0.02:
                score += 25
            elif fark_oran <= 0.05:
                score += 18
            elif fark_oran <= 0.10:
                score += 10

        if k_oda and r_oda:
            if k_oda == r_oda:
                score += 15
            elif benzerlik(k_oda, r_oda) >= 0.70:
                score += 8

        if k_ozet and r_ozet:
            sim = benzerlik(k_ozet, r_ozet)
            if sim >= 0.70:
                score += 15
            elif sim >= 0.50:
                score += 8

        if score > best_score:
            best_score = score
            best_row = row

    if best_row and best_score >= 70:
        return True, best_row, _safe_str(
            best_row.get("id") or best_row.get("ilan_id") or best_row.get("revy_id") or ""
        ), best_score

    return False, None, "", best_score


# ─────────────────────────────────────────────
# Ana sınıflandırma
# ─────────────────────────────────────────────

def manuel_kapali_mi(kayit: Dict[str, Any]) -> bool:
    kaynak = _lower_tr(kayit.get("kaynak") or "")
    gor = _lower_tr(kayit.get("portfoy_gorunurluk") or "")
    kapali_flag = bool(kayit.get("kapali_portfoy") or kayit.get("kapali_oncelik"))

    kapali_kaynaklar = {
        "ofis_gizli",
        "manuel_kapali",
        "kapali",
        "kapali_portfoy",
        "gizli_portfoy",
    }

    return (
        kapali_flag
        or kaynak in kapali_kaynaklar
        or gor in {GORUNURLUK_KAPALI, "kapali", "kapalı"}
    )


def siniflandir_portfoy(
    kayit: Dict[str, Any],
    merkezi_ilanlar: Optional[Iterable[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Portföy kaydını görünürlük açısından sınıflandırır.

    Dönen sözlük doğrudan Supabase update için kullanılabilir.
    """
    metinler = portfoy_metinleri(kayit)
    linkler = metinlerden_url_cikar(*metinler)

    link_sayisi = len(linkler)
    coklu = link_sayisi > 1
    primary = linkler[0]["normalized_url"] if linkler else ""

    link_eslesti, link_row, link_merkezi_id = linkten_merkezi_eslesme(linkler, merkezi_ilanlar)

    fuzzy_eslesti = False
    fuzzy_row = None
    fuzzy_merkezi_id = ""
    fuzzy_score = 0.0

    if not linkler and merkezi_ilanlar:
        fuzzy_eslesti, fuzzy_row, fuzzy_merkezi_id, fuzzy_score = fuzzy_merkezi_eslesme(
            kayit, merkezi_ilanlar
        )

    merkezi_eslesme = bool(link_eslesti or fuzzy_eslesti)
    merkezi_row = link_row or fuzzy_row
    merkezi_id = link_merkezi_id or fuzzy_merkezi_id

    # Manuel kapalı en güçlü sinyaldir.
    if manuel_kapali_mi(kayit):
        gorunurluk = GORUNURLUK_KAPALI
        guven = "yuksek"
        kapali_oncelik = True
        manuel_teyit = True
        paylasim_onayi = False

    elif coklu:
        gorunurluk = GORUNURLUK_COKLU
        guven = "orta"
        kapali_oncelik = False
        manuel_teyit = False
        paylasim_onayi = True

    elif linkler and merkezi_eslesme:
        gorunurluk = GORUNURLUK_MAIL_PAYLASIM
        guven = "yuksek"
        kapali_oncelik = False
        manuel_teyit = False
        paylasim_onayi = True

    elif linkler and not merkezi_eslesme:
        gorunurluk = GORUNURLUK_ILANDA
        guven = "orta"
        kapali_oncelik = False
        manuel_teyit = False
        paylasim_onayi = True

    elif not linkler and merkezi_eslesme:
        gorunurluk = GORUNURLUK_TEYIT
        guven = "orta" if fuzzy_score >= 70 else "dusuk"
        kapali_oncelik = False
        manuel_teyit = False
        paylasim_onayi = False

    else:
        gorunurluk = GORUNURLUK_KAPALI
        guven = "orta"
        kapali_oncelik = True
        manuel_teyit = False
        paylasim_onayi = False

    return {
        "portfoy_gorunurluk": gorunurluk,
        "portal_linkleri": linkler,
        "primary_ilan_linki": primary,
        "link_sayisi": link_sayisi,
        "merkezi_ilan_id": merkezi_id or None,
        "merkezi_ilan_eslesme": merkezi_eslesme,
        "siniflandirma_guveni": guven,
        "manuel_teyit": manuel_teyit,
        "paylasim_onayi_var": paylasim_onayi,
        "coklu_ilan_maili": coklu,
        "kapali_oncelik": kapali_oncelik,
        "_debug": {
            "fuzzy_score": fuzzy_score,
            "merkezi_eslesme_var": bool(merkezi_row),
            "linkler": [x.get("normalized_url") for x in linkler],
        }
    }


def supabase_update_payload(sonuc: Dict[str, Any]) -> Dict[str, Any]:
    """
    Debug alanını çıkarır. Supabase update için temiz payload verir.
    """
    return {k: v for k, v in sonuc.items() if not k.startswith("_")}


def gorunurluk_label(gorunurluk: str) -> str:
    return GORUNURLUK_ETIKET.get(gorunurluk or "", "? Teyit Gerekli")


def gorunurluk_rozet_html(gorunurluk: str) -> str:
    """
    Portföy kartlarında küçük rozet olarak kullanılabilir.
    """
    label = gorunurluk_label(gorunurluk)

    palette = {
        GORUNURLUK_KAPALI: ("#fff7ed", "#9a3412", "#fed7aa"),
        GORUNURLUK_ILANDA: ("#e0f2fe", "#0369a1", "#bae6fd"),
        GORUNURLUK_MAIL_PAYLASIM: ("#eef2ff", "#3730a3", "#c7d2fe"),
        GORUNURLUK_COKLU: ("#fef3c7", "#92400e", "#fde68a"),
        GORUNURLUK_TEYIT: ("#f1f5f9", "#475569", "#cbd5e1"),
    }

    bg, fg, border = palette.get(gorunurluk, palette[GORUNURLUK_TEYIT])

    return (
        f'<span style="background:{bg};color:{fg};border:1px solid {border};'
        f'padding:2px 8px;border-radius:999px;font-size:10px;font-weight:700;'
        f'white-space:nowrap;display:inline-block;">{label}</span>'
    )
