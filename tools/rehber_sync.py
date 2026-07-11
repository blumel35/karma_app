"""
rehber_sync.py
startkey.com.tr → Supabase sync.

Bu revizyonun amacı:
- Startkey ofis sayfalarındaki danışmanları, "agent" class'ına bağımlı kalmadan
  profil linkleri üzerinden güvenli çekmek.
- Zeta gibi tek HTML container içinde birden fazla danışman bulunan sayfalarda
  sadece ilk danışmanın çekilmesi sorununu önlemek.
- Eksik/parsiyel çekim olduğunda mevcut aktif danışmanları yanlışlıkla pasife
  almamak.

Kullanım:
    python rehber_sync.py

Test:
    python rehber_sync.py --dry-run --ofis Zeta

Zorunlu ortam değişkenleri:
    SUPABASE_URL
    SUPABASE_SERVICE_KEY  veya  SUPABASE_KEY
"""

import argparse
import os
import re
import sys
import time
from datetime import datetime, timezone
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


# ═══════════════════════════════════════════════════════════════════════════════
# AYARLAR
# ═══════════════════════════════════════════════════════════════════════════════

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_KEY", "")

BASE_URL = "https://www.startkey.com.tr"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
    )
}

REQUEST_TIMEOUT = 35
SLEEP_PAGE = 0.35
SLEEP_OFFICE = 0.50

# Yeni çekilen danışman sayısı mevcut aktif sayının bu oranının altındaysa
# "parsiyel çekim olabilir" kabul edip ayrılanları pasife alma.
SAFE_DEACTIVATE_MIN_RATIO = 0.60

AKS_HARITASI = {
    "bayraklı":    ("İzmir", "İzmir Merkez"),
    "bornova":     ("İzmir", "İzmir Merkez"),
    "buca":        ("İzmir", "İzmir Merkez"),
    "gaziemir":    ("İzmir", "İzmir Merkez"),
    "karabağlar":  ("İzmir", "İzmir Merkez"),
    "konak":       ("İzmir", "İzmir Merkez"),
    "karşıyaka":   ("İzmir", "Kuzey Aksı"),
    "çiğli":       ("İzmir", "Kuzey Aksı"),
    "menemen":     ("İzmir", "Kuzey Aksı"),
    "foça":        ("İzmir", "Kuzey Aksı"),
    "aliağa":      ("İzmir", "Kuzey Aksı"),
    "dikili":      ("İzmir", "Kuzey Aksı"),
    "bergama":     ("İzmir", "Kuzey Aksı"),
    "güzelbahçe":  ("İzmir", "Yarımada / Batı Aksı"),
    "narlıdere":   ("İzmir", "Yarımada / Batı Aksı"),
    "balçova":     ("İzmir", "Yarımada / Batı Aksı"),
    "urla":        ("İzmir", "Yarımada / Batı Aksı"),
    "çeşme":       ("İzmir", "Yarımada / Batı Aksı"),
    "menderes":    ("İzmir", "Güney Aksı"),
    "torbalı":     ("İzmir", "Güney Aksı"),
    "selçuk":      ("İzmir", "Güney Aksı"),
    "tire":        ("İzmir", "Doğu / Dış Aks"),
    "ödemiş":      ("İzmir", "Doğu / Dış Aks"),
}

UNVAN_IPUCLARI = (
    "broker",
    "owner",
    "gayrimenkul danışmanı",
    "danışman",
    "ofis müdürü",
    "ofis asistanı",
    "asistan",
    "koordinasyon",
    "koordinatör",
    "müdür",
)

# Startkey sayfasında bazı kişi kartlarında gerçek unvan yerine
# bölüm başlığı yakalanabiliyor. Bunları standart unvana çeviriyoruz.
UNVAN_BOLUM_BASLIKLARI = {
    "danismanlarimiz",
}


# ═══════════════════════════════════════════════════════════════════════════════
# GENEL YARDIMCILAR
# ═══════════════════════════════════════════════════════════════════════════════

def now_iso():
    """UTC zamanını timezone-aware ISO formatında döndürür."""
    return datetime.now(timezone.utc).isoformat()


def temizle(deger):
    if deger is None:
        return ""
    s = str(deger).replace("\xa0", " ").strip()
    s = re.sub(r"\s+", " ", s)
    return "" if s.lower() in ("nan", "none", "nat", "null") else s


def normalize_key(s):
    s = temizle(s).lower()
    tr_map = str.maketrans("ığüşöçİĞÜŞÖÇ", "igusocigusoc")
    s = s.translate(tr_map)
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def unvan_temizle(unvan):
    """
    Danışman kartlarında gerçek unvan yerine yakalanan bölüm başlıklarını
    kullanıcıya gösterilecek temiz unvana çevirir.
    """
    u = temizle(unvan)
    if not u:
        return "Gayrimenkul Danışmanı"

    if normalize_key(u) in UNVAN_BOLUM_BASLIKLARI:
        return "Gayrimenkul Danışmanı"

    return u


def text_lines(el):
    if el is None:
        return []
    raw = list(el.stripped_strings)
    out = []
    seen = set()
    for item in raw:
        t = temizle(item)
        if not t:
            continue
        if t in seen:
            continue
        seen.add(t)
        out.append(t)
    return out


def get(url, retries=3):
    for attempt in range(retries):
        try:
            r = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            r.raise_for_status()
            return BeautifulSoup(r.text, "html.parser")
        except Exception as e:
            if attempt == retries - 1:
                print(f"  HATA: {url} → {e}")
                return None
            time.sleep(2)


def supabase_client():
    from supabase import create_client

    if not SUPABASE_URL or not SUPABASE_KEY:
        print("HATA: SUPABASE_URL / SUPABASE_SERVICE_KEY tanımlı değil.")
        print("Örnek:")
        print("  set SUPABASE_URL=https://xxxx.supabase.co")
        print("  set SUPABASE_SERVICE_KEY=xxxxx")
        sys.exit(1)

    return create_client(SUPABASE_URL, SUPABASE_KEY)


def telefon_formatla(raw):
    """Startkey'ten gelen +null vb. telefonları temiz ve tek formatta döndür."""
    s = temizle(raw)
    if not s:
        return ""

    s = s.replace("+null", "").replace("null", "")
    digits = re.sub(r"\D", "", s)

    if not digits:
        return ""

    if digits.startswith("0090"):
        digits = digits[2:]

    if digits.startswith("90") and len(digits) >= 12:
        ulke = "90"
        kalan = digits[2:]
    elif digits.startswith("0") and len(digits) >= 11:
        ulke = "90"
        kalan = digits[1:]
    elif len(digits) == 10:
        ulke = "90"
        kalan = digits
    else:
        # Son 10 hane Türkiye GSM/sabit numara kabul edilir.
        ulke = "90"
        kalan = digits[-10:] if len(digits) > 10 else digits

    if len(kalan) == 10:
        return f"+{ulke} ({kalan[:3]}) {kalan[3:6]}-{kalan[6:]}"
    return f"+{ulke} {kalan}"


def mail_bul(el):
    if el is None:
        return ""

    for a in el.find_all("a", href=True):
        href = a.get("href", "")
        if "mailto:" in href:
            return temizle(href.split("mailto:", 1)[1].split("?", 1)[0])

    text = el.get_text(" ", strip=True)
    m = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", text)
    return temizle(m.group(0)) if m else ""


def telefon_bul(el):
    if el is None:
        return ""

    for a in el.find_all("a", href=True):
        href = a.get("href", "")
        if "tel:" in href:
            return telefon_formatla(href.split("tel:", 1)[1])

    text = el.get_text(" ", strip=True)
    # +90 (532) 486-9697, 0532 486 96 97, +null (535) 737-3531 vb.
    m = re.search(r"(?:\+?\s*(?:90|null)|0)?\s*\(?5\d{2}\)?[\s.-]*\d{3}[\s.-]*\d{2}[\s.-]*\d{2}", text)
    if not m:
        m = re.search(r"(?:\+?\s*(?:90|null)|0)?\s*\(?2\d{2}\)?[\s.-]*\d{3}[\s.-]*\d{2}[\s.-]*\d{2}", text)
    return telefon_formatla(m.group(0)) if m else ""


# ═══════════════════════════════════════════════════════════════════════════════
# OFİS LİSTESİ VE DETAYLARI
# ═══════════════════════════════════════════════════════════════════════════════

def ofis_listesini_cek():
    """
    /tr/ofisler sayfalarından ofis adı + link + logo_url döndürür.
    Döndürür:
        [{ofis_adi, ofis_link, logo_url}]
    """
    ofisler = []
    gorulen_linkler = set()

    for sayfa in range(1, 16):
        url = f"{BASE_URL}/tr/ofisler" if sayfa == 1 else f"{BASE_URL}/tr/ofisler?pageIndex={sayfa}"
        soup = get(url)
        if soup is None:
            break

        sayfa_logo_haritasi = {}

        for a in soup.find_all("a", href=True):
            img = a.find("img")
            if img is None:
                continue

            src = img.get("src", "") or img.get("data-src", "")
            if "officelogo" not in src.lower() and "office" not in src.lower():
                continue

            href = urljoin(BASE_URL, a["href"])
            sayfa_logo_haritasi[href] = urljoin(BASE_URL, src)

        eslesen = 0

        # Ana yöntem: logo linkleri üzerinden ofis kartlarını yakala
        for href, logo_url in sayfa_logo_haritasi.items():
            if href in gorulen_linkler:
                continue

            a = soup.find("a", href=lambda h: h and urljoin(BASE_URL, h) == href)
            ad = ""

            if a:
                # Aynı karta yakın başlıkları dene
                parent = a
                for _ in range(6):
                    parent = parent.parent if parent else None
                    if parent is None:
                        break
                    baslik = parent.find(["h2", "h3", "h4"])
                    if baslik:
                        ad = temizle(baslik.get_text(" ", strip=True))
                        if ad:
                            break

            # Fallback: href son slug
            if not ad:
                slug = href.rstrip("/").split("/")[-1]
                ad = slug.replace("-", " ").title()

            # Çok genel / yanlış metinleri ele
            if not ad or normalize_key(ad) in ("anasayfa", "ofislerimiz", "detay"):
                continue

            ofisler.append({
                "ofis_adi": ad,
                "ofis_link": href,
                "logo_url": logo_url,
            })
            gorulen_linkler.add(href)
            eslesen += 1

        # Fallback: başlık linklerinden ofis linki yakala
        if eslesen == 0:
            for h in soup.find_all(["h2", "h3", "h4"]):
                a = h.find("a", href=True)
                if not a:
                    continue
                href = urljoin(BASE_URL, a["href"])
                ad = temizle(a.get_text(" ", strip=True))
                if not ad or href in gorulen_linkler:
                    continue
                if "/ofisler/" not in href and not re.search(r"/[a-z0-9-]+$", href):
                    continue

                ofisler.append({
                    "ofis_adi": ad,
                    "ofis_link": href,
                    "logo_url": sayfa_logo_haritasi.get(href, ""),
                })
                gorulen_linkler.add(href)
                eslesen += 1

        print(f"  Sayfa {sayfa}: {eslesen} ofis")

        # İlk sayfadan sonra hiç eşleşme yoksa sayfalama bitmiş kabul edilir.
        if sayfa > 1 and eslesen == 0:
            break

        time.sleep(SLEEP_PAGE)

    return ofisler


def ofis_detay_cek(ofis_link):
    """Ofis sayfasından telefon, mail, adres, il, ilce, mahalle bilgisi çeker."""
    soup = get(ofis_link)
    if soup is None:
        return {}

    bilgi = {"telefon": "", "mail": "", "adres": "", "il": "", "ilce": "", "mahalle": ""}

    # Sayfanın üst ofis bilgi bloğundaki ilk tel/mail genellikle ofise aittir.
    bilgi["telefon"] = telefon_bul(soup)
    bilgi["mail"] = mail_bul(soup)

    # Adres satırı genellikle "İzmir / Bornova / Kazımdirik / ..." formatındadır.
    tum_satirlar = text_lines(soup)
    adres_adayi = ""
    for line in tum_satirlar:
        if "/" in line and any(ilce in line.lower() for ilce in AKS_HARITASI.keys()):
            adres_adayi = line
            break

    if not adres_adayi:
        for el in soup.find_all(["address", "p", "li", "div"]):
            text = temizle(el.get_text(" ", strip=True))
            if len(text) > 20 and any(c.isdigit() for c in text) and any(ilce in text.lower() for ilce in AKS_HARITASI.keys()):
                adres_adayi = text
                break

    bilgi["adres"] = adres_adayi[:300] if adres_adayi else ""

    # İl / ilçe / mahalle ayrıştırma
    parcalar = [temizle(p) for p in adres_adayi.split("/") if temizle(p)] if adres_adayi else []
    if len(parcalar) >= 2:
        bilgi["il"] = parcalar[0]
        bilgi["ilce"] = parcalar[1]
        if len(parcalar) >= 3:
            bilgi["mahalle"] = parcalar[2]

    if not bilgi["ilce"]:
        arama_metni = (bilgi["adres"] + " " + soup.get_text(" ", strip=True)[:3000]).lower()
        for ilce_anahtar in AKS_HARITASI.keys():
            if re.search(rf"\b{re.escape(ilce_anahtar)}\b", arama_metni):
                bilgi["il"] = "İzmir"
                bilgi["ilce"] = ilce_anahtar.capitalize()
                break

    return bilgi


# ═══════════════════════════════════════════════════════════════════════════════
# DANIŞMAN ÇEKME
# ═══════════════════════════════════════════════════════════════════════════════

def profil_link_mi(href):
    if not href:
        return False
    h = href.lower()
    return "/danismanlar/" in h or "/consultants/" in h or "/agents/" in h


def en_yakin_kisi_karti(anchor):
    """
    Profil linkinin bulunduğu en küçük danışman kartını bulur.

    Eski kod tüm div class'larında "agent" aradığı için bazı sayfalarda
    tüm ekip container'ını tek kart sanıyordu. Bu fonksiyon, aynı parent içinde
    yalnızca 1 benzersiz profil linki kalana kadar yukarı çıkar.
    """
    node = anchor

    for _ in range(10):
        if node is None:
            break

        parent = node.parent
        if parent is None or parent.name in ("body", "html"):
            break

        profil_linkleri = []
        for a in parent.find_all("a", href=True):
            if profil_link_mi(a.get("href", "")):
                profil_linkleri.append(urljoin(BASE_URL, a["href"]))

        benzersiz = set(profil_linkleri)
        metin = temizle(parent.get_text(" ", strip=True))

        # Parent tek kişiye aitse ve makul boyuttaysa bu karttır.
        if len(benzersiz) == 1 and len(metin) < 900:
            return parent

        node = parent

    return anchor.parent


def unvan_bul(kart, isim):
    if kart is None:
        return "Gayrimenkul Danışmanı"

    isim_key = normalize_key(isim)

    # Önce isim başlığının kardeş span/p/div alanını dene.
    for tag in kart.find_all(["h1", "h2", "h3", "h4", "strong", "a"]):
        if normalize_key(tag.get_text(" ", strip=True)) == isim_key:
            for sib in tag.find_all_next(["span", "p", "div"], limit=4):
                t = temizle(sib.get_text(" ", strip=True))
                if not t:
                    continue
                low = t.lower()
                if "@" in t or "tel:" in low or re.search(r"\d{3}", t):
                    continue
                if any(ipucu in low for ipucu in UNVAN_IPUCLARI):
                    return unvan_temizle(t)

    # Sonra satır satır tara.
    for line in text_lines(kart):
        low = line.lower()
        if normalize_key(line) == isim_key:
            continue
        if "@" in line or re.search(r"\d{3}", line):
            continue
        if low in ("broker/owner", "yönetim", "profesyoneller", "koordinasyon"):
            continue
        if any(ipucu in low for ipucu in UNVAN_IPUCLARI):
            return unvan_temizle(line)

    return "Gayrimenkul Danışmanı"


def foto_bul(kart):
    if kart is None:
        return ""

    img = kart.find("img")
    if not img:
        return ""

    src = img.get("src", "") or img.get("data-src", "")
    if not src:
        return ""

    return urljoin(BASE_URL, src)


def danisman_detay_cek(profil_link):
    """
    Kişi kartında telefon/mail eksik kaldığında profil sayfasından tamamlar.
    Ana akışta sadece eksik kayıtlar için kullanılır.
    """
    soup = get(profil_link, retries=2)
    if soup is None:
        return {}

    bilgi = {
        "telefon": telefon_bul(soup),
        "mail": mail_bul(soup),
        "foto_url": foto_bul(soup),
        "unvan": "",
    }

    # Profil sayfasında isimden sonraki ilk unvan satırı genelde yeterli.
    for line in text_lines(soup):
        low = line.lower()
        if any(ipucu in low for ipucu in UNVAN_IPUCLARI):
            bilgi["unvan"] = line
            break

    return bilgi


def danisman_listesi_cek(ofis_adi, ofis_link):
    """
    Ofis sayfasındaki danışman listesini döndürür.

    Temel strateji:
    1) Class adına güvenmek yerine /danismanlar/ profil linklerini yakala.
    2) Her profil linkinin en yakın tekil kişi kartını bul.
    3) İsim, unvan, telefon, mail, foto alanlarını karttan çıkar.
    4) Eksik telefon/mail varsa kişinin profil sayfasından tamamla.
    """
    soup = get(ofis_link)
    if soup is None:
        return []

    danismanlar = []
    gorulen_profiller = set()
    gorulen_isimler = set()

    profil_ankorlari = []
    for a in soup.find_all("a", href=True):
        href = a.get("href", "")
        if not profil_link_mi(href):
            continue

        isim = temizle(a.get_text(" ", strip=True))
        if not isim:
            # Fotoğraf linkleri boş gelir; aynı karttaki isim linki ayrıca yakalanır.
            continue

        # Menü/link kirliliği ele
        if normalize_key(isim) in ("detay", "profili ac", "tum portfoyleri"):
            continue

        profil_ankorlari.append(a)

    for a in profil_ankorlari:
        isim = temizle(a.get_text(" ", strip=True))
        profil_link = urljoin(BASE_URL, a["href"])

        isim_key = normalize_key(isim)
        if not isim_key or len(isim_key) < 3:
            continue

        # Aynı kişi aynı sayfada görsel link + isim link olarak tekrarlanabilir.
        if profil_link in gorulen_profiller or isim_key in gorulen_isimler:
            continue

        kart = en_yakin_kisi_karti(a)

        unvan = unvan_bul(kart, isim)
        telefon = telefon_bul(kart)
        mail = mail_bul(kart)
        foto_url = foto_bul(kart)

        # Kart küçük kaldıysa profil sayfasından tamamla.
        if (not telefon or not mail) and profil_link:
            detay = danisman_detay_cek(profil_link)
            telefon = telefon or detay.get("telefon", "")
            mail = mail or detay.get("mail", "")
            foto_url = foto_url or detay.get("foto_url", "")
            if unvan == "Gayrimenkul Danışmanı" and detay.get("unvan"):
                unvan = detay["unvan"]

        unvan = unvan_temizle(unvan)

        danismanlar.append({
            "ofis_adi": ofis_adi,
            "isim": isim,
            "unvan": unvan,
            "telefon": telefon,
            "mail": mail,
            "foto_url": foto_url,
            "profil_link": profil_link,
            "aktif": True,
            "guncelleme_tar": now_iso(),
        })

        gorulen_profiller.add(profil_link)
        gorulen_isimler.add(isim_key)

    # Ek fallback: Çok eski HTML yapısında sadece div.agent kartları varsa.
    if not danismanlar:
        for kart in soup.find_all("div", class_=lambda c: c and "agent" in str(c).lower()):
            isim = ""
            isim_tag = None

            for tag in kart.find_all(["h2", "h3", "h4", "strong"]):
                t = temizle(tag.get_text(" ", strip=True))
                if len(t) > 2:
                    isim_tag = tag
                    isim = t
                    break

            if not isim:
                continue

            isim_key = normalize_key(isim)
            if isim_key in gorulen_isimler:
                continue

            a = kart.find("a", href=lambda h: h and profil_link_mi(h))
            profil_link = urljoin(BASE_URL, a["href"]) if a else ""

            danismanlar.append({
                "ofis_adi": ofis_adi,
                "isim": isim,
                "unvan": unvan_temizle(unvan_bul(kart, isim)),
                "telefon": telefon_bul(kart),
                "mail": mail_bul(kart),
                "foto_url": foto_bul(kart),
                "profil_link": profil_link,
                "aktif": True,
                "guncelleme_tar": now_iso(),
            })

            gorulen_isimler.add(isim_key)

    return danismanlar


# ═══════════════════════════════════════════════════════════════════════════════
# BÖLGE VE SUPABASE
# ═══════════════════════════════════════════════════════════════════════════════

def bolge_tahmin(il, ilce):
    il_temiz = temizle(il)
    ilce_lower = temizle(ilce).lower()

    for anahtar, (_bolge_il, bolge_aksi) in AKS_HARITASI.items():
        if anahtar in ilce_lower:
            return "İzmir", bolge_aksi

    if il_temiz.lower() == "izmir":
        return "İzmir", "İzmir Merkez"

    return "İzmir Dışı", "İzmir Dışı"


def mevcut_ofis_adlari(supa):
    res = supa.table("rehber_ofisler").select("ofis_adi").eq("aktif", True).execute()
    return {r["ofis_adi"] for r in (res.data or [])}


def ofisleri_guncelle(supa, ofisler, dry_run=False):
    now = now_iso()
    kayitlar = []
    gorulen = set()

    for o in ofisler:
        ofis_adi = temizle(o.get("ofis_adi", ""))
        if not ofis_adi or normalize_key(ofis_adi) in gorulen:
            continue

        gorulen.add(normalize_key(ofis_adi))
        bolge_tipi, bolge_aksi = bolge_tahmin(o.get("il", ""), o.get("ilce", ""))

        kayitlar.append({
            "ofis_adi": ofis_adi,
            "ofis_link": o.get("ofis_link", ""),
            "logo_url": o.get("logo_url", ""),
            "telefon": o.get("telefon", ""),
            "mail": o.get("mail", ""),
            "adres": o.get("adres", ""),
            "il": o.get("il", ""),
            "ilce": o.get("ilce", ""),
            "mahalle": o.get("mahalle", ""),
            "bolge_tipi": bolge_tipi,
            "bolge_aksi": bolge_aksi,
            "aktif": True,
            "guncelleme_tar": now,
        })

    if dry_run:
        print(f"  DRY-RUN: {len(kayitlar)} ofis yazılacaktı.")
        return

    if kayitlar:
        supa.table("rehber_ofisler").upsert(kayitlar, on_conflict="ofis_adi").execute()

    print(f"  ✓ {len(kayitlar)} ofis güncellendi.")


def kapanan_ofisleri_pasifle(supa, eski_adlar, yeni_adlar, dry_run=False):
    kapananlar = eski_adlar - yeni_adlar
    if not kapananlar:
        return

    if dry_run:
        print(f"  DRY-RUN: {len(kapananlar)} ofis pasife alınacaktı: {sorted(kapananlar)}")
        return

    for ofis_adi in kapananlar:
        supa.table("rehber_ofisler").update({
            "aktif": False,
            "guncelleme_tar": now_iso(),
        }).eq("ofis_adi", ofis_adi).execute()

    print(f"  ⚠ {len(kapananlar)} ofis pasife alındı: {sorted(kapananlar)}")


def mevcut_aktif_danisman_isimleri(supa, ofis_adi):
    res = (
        supa.table("rehber_danismanlar")
        .select("isim")
        .eq("ofis_adi", ofis_adi)
        .eq("aktif", True)
        .execute()
    )
    return {r["isim"] for r in (res.data or [])}


def danismanlari_guncelle(supa, danismanlar, ofis_adi, dry_run=False, force_pasif=False):
    """
    Danışmanları upsert eder. Eksik çekim ihtimalinde mevcut kişileri pasife almaz.

    Eski sorun:
    - Scraper Zeta'da 1 kişi çekince, eski aktif 17 kişinin 16'sını pasife alıyordu.
    Yeni davranış:
    - Yeni çekim mevcut sayıya göre şüpheli düşükse sadece bulunanları günceller,
      ayrılanları pasife almaz.
    """
    if not danismanlar:
        print("    ⚠ Danışman bulunamadı; mevcut aktif kayıtlar korunuyor.")
        return 0

    # Tekilleştir
    tekil = {}
    for d in danismanlar:
        isim = temizle(d.get("isim", ""))
        if not isim:
            continue
        anahtar = (temizle(d.get("ofis_adi", ofis_adi)), normalize_key(isim))
        d["isim"] = isim
        d["ofis_adi"] = temizle(d.get("ofis_adi", ofis_adi)) or ofis_adi
        d["telefon"] = telefon_formatla(d.get("telefon", ""))
        d["mail"] = temizle(d.get("mail", ""))
        d["unvan"] = unvan_temizle(d.get("unvan", ""))
        d["aktif"] = True
        d["guncelleme_tar"] = now_iso()
        tekil[anahtar] = d

    danismanlar = list(tekil.values())

    eski_isimler = mevcut_aktif_danisman_isimleri(supa, ofis_adi) if not dry_run else set()
    yeni_isimler = {d["isim"] for d in danismanlar}

    if dry_run:
        print(f"    DRY-RUN: {len(danismanlar)} danışman yazılacaktı.")
        for d in danismanlar[:30]:
            print(f"      - {d['isim']} | {d['unvan']} | {d['telefon']} | {d['mail']}")
        if len(danismanlar) > 30:
            print(f"      ... +{len(danismanlar)-30} kişi")
        return len(danismanlar)

    supa.table("rehber_danismanlar").upsert(
        danismanlar,
        on_conflict="ofis_adi,isim",
    ).execute()

    ayrilanlar = eski_isimler - yeni_isimler

    if ayrilanlar:
        safe_to_deactivate = True

        if eski_isimler and not force_pasif:
            ratio = len(yeni_isimler) / max(len(eski_isimler), 1)
            if ratio < SAFE_DEACTIVATE_MIN_RATIO:
                safe_to_deactivate = False

        if safe_to_deactivate:
            for isim in ayrilanlar:
                supa.table("rehber_danismanlar").update({
                    "aktif": False,
                    "guncelleme_tar": now_iso(),
                }).eq("ofis_adi", ofis_adi).eq("isim", isim).execute()
            print(f"    ↳ {len(ayrilanlar)} danışman pasife alındı")
        else:
            print(
                f"    ⚠ Pasife alma atlandı: eski aktif={len(eski_isimler)}, "
                f"yeni çekilen={len(yeni_isimler)}. Parsiyel çekim olabilir."
            )

    return len(danismanlar)


# ═══════════════════════════════════════════════════════════════════════════════
# ANA AKIŞ
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Startkey Rehber → Supabase sync")
    parser.add_argument("--dry-run", action="store_true", help="Supabase'e yazmadan test eder.")
    parser.add_argument("--ofis", default="", help="Sadece adı bu ifadeyi içeren ofisleri işler. Örn: --ofis Zeta")
    parser.add_argument("--force-pasif", action="store_true", help="Güvenlik oranına bakmadan ayrılanları pasife alır.")
    args = parser.parse_args()

    print(f"Startkey Rehber Sync — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)

    supa = None
    eski_adlar = set()

    if not args.dry_run:
        supa = supabase_client()
        eski_adlar = mevcut_ofis_adlari(supa)
        print(f"Mevcut Supabase'de {len(eski_adlar)} aktif ofis var.")
    else:
        print("DRY-RUN modu: Supabase'e yazılmayacak.")

    print("\n── Ofis listesi çekiliyor...")
    ofisler = ofis_listesini_cek()

    if args.ofis:
        q = normalize_key(args.ofis)
        ofisler = [o for o in ofisler if q in normalize_key(o.get("ofis_adi", ""))]
        print(f"  Filtre: {args.ofis!r} → {len(ofisler)} ofis")

    print(f"  {len(ofisler)} ofis bulundu.")

    if not ofisler:
        print("HATA: Ofis listesi boş geldi. İşlem durduruldu.")
        return

    print("\n── Ofis detayları çekiliyor...")
    for i, ofis in enumerate(ofisler, 1):
        detay = ofis_detay_cek(ofis["ofis_link"])
        ofis.update(detay)
        print(
            f"  [{i}/{len(ofisler)}] {ofis['ofis_adi']} "
            f"→ {ofis.get('ilce','') or '-'} / {ofis.get('telefon','') or '-'}"
        )
        time.sleep(SLEEP_PAGE)

    print("\n── Ofisler Supabase'e yazılıyor...")
    if supa is not None:
        ofisleri_guncelle(supa, ofisler, dry_run=args.dry_run)
    else:
        print(f"  DRY-RUN: {len(ofisler)} ofis yazılacaktı.")

    if supa is not None and not args.ofis:
        yeni_adlar = {o["ofis_adi"] for o in ofisler}
        kapanan_ofisleri_pasifle(supa, eski_adlar, yeni_adlar, dry_run=args.dry_run)
    elif args.ofis:
        print("  Not: --ofis filtresi kullanıldığı için kapanan ofis pasifleştirme atlandı.")

    print("\n── Danışmanlar güncelleniyor...")
    toplam_dan = 0

    for i, ofis in enumerate(ofisler, 1):
        ofis_adi = ofis["ofis_adi"]
        print(f"  [{i}/{len(ofisler)}] {ofis_adi}...")
        danismanlar = danisman_listesi_cek(ofis_adi, ofis["ofis_link"])

        if supa is not None:
            yazilan = danismanlari_guncelle(
                supa,
                danismanlar,
                ofis_adi,
                dry_run=args.dry_run,
                force_pasif=args.force_pasif,
            )
        else:
            yazilan = len(danismanlar)
            print(f"    DRY-RUN: {len(danismanlar)} danışman bulundu.")
            for d in danismanlar[:30]:
                print(f"      - {d['isim']} | {d['unvan']} | {d['telefon']} | {d['mail']}")

        toplam_dan += yazilan
        time.sleep(SLEEP_OFFICE)

    print(f"\n✅ Sync tamamlandı. {len(ofisler)} ofis, {toplam_dan} danışman işlendi.")
    print(f"   Tarih: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    if args.dry_run:
        print("\nKontrol iyi görünüyorsa gerçek yazım için:")
        if args.ofis:
            print(f"  python rehber_sync.py --ofis \"{args.ofis}\"")
            print("Sonra tüm ofisler için:")
        print("  python rehber_sync.py")


if __name__ == "__main__":
    main()
