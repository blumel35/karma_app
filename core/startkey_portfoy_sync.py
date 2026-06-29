"""
core/startkey_portfoy_sync.py
──────────────────────────────
startkey.com.tr → Supabase sync motoru.
Zeta 1 ve Zeta 2 ilanlarını çeker, parse eder, Supabase'e yazar.

- Liste sayfaları: requests (JS gerektirmiyor)
- Detay sayfaları: Selenium headless (JS ile render edilen içerik)
  → Tek driver tüm ilanlar boyunca paylaşılır (hız optimizasyonu)

Kullanım (terminalden):
    python core/startkey_portfoy_sync.py

Supabase tablosu: startkey_portfoyler
"""

import re
import time
import json
import sys
import os
from datetime import datetime, timezone
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.startkey.com.tr"
HEADERS  = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "tr-TR,tr;q=0.9",
}

OFISLER = {
    "zeta1": {
        "label":     "ZETA 1",
        "office_id": "18830",
        "url":       f"{BASE_URL}/tr/portfoy?FilterDTO.OfficeId=18830",
    },
    "zeta2": {
        "label":     "ZETA 2",
        "office_id": "18824",
        "url":       f"{BASE_URL}/tr/portfoy?FilterDTO.OfficeId=18824",
    },
}

# ── Yardımcılar ───────────────────────────────────────────────────────────────

def _temizle(s):
    if not s:
        return ""
    return re.sub(r"\s+", " ", str(s)).strip()

def _get_requests(url, retries=3):
    """requests ile HTML çek — JS gerektirmeyen sayfalar için."""
    for attempt in range(retries):
        try:
            r = requests.get(url, headers=HEADERS, timeout=30)
            r.raise_for_status()
            return BeautifulSoup(r.text, "html.parser")
        except Exception as e:
            if attempt == retries - 1:
                print(f"  ✗ HATA: {url} → {e}")
                return None
            time.sleep(2 ** attempt)


# ── Selenium driver ───────────────────────────────────────────────────────────

def _driver_olustur(headless=True):
    """Headless Chrome driver oluştur."""
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    options = Options()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1280,900")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    return webdriver.Chrome(options=options)


def _selenium_soup(driver, url, bekleme=2.5):
    """Driver ile sayfayı aç, render bekle, BeautifulSoup döndür."""
    driver.get(url)
    time.sleep(bekleme)
    return BeautifulSoup(driver.page_source, "html.parser")


# ── URL parse — il/ilçe/mahalle/işlem/mülk ───────────────────────────────────

# Slug → Türkçe kelime haritası
_TR_KELIME = {
    "kiralik":"Kiralık","satilik":"Satılık","daire":"Daire","villa":"Villa",
    "arsa":"Arsa","tarla":"Tarla","isyeri":"İşyeri","dukkan":"Dükkan",
    "ofis":"Ofis","bina":"Bina","konut":"Konut","residence":"Residence",
    "mahallesinde":"Mahallesi'nde","mahallesindeki":"Mahallesi'ndeki",
    "mahallesi":"Mahallesi","izmir":"İzmir","karsiyaka":"Karşıyaka",
    "bornova":"Bornova","buca":"Buca","konak":"Konak","bayrakli":"Bayraklı",
    "cigli":"Çiğli","gaziemir":"Gaziemir","karabaglar":"Karabağlar",
    "narlidere":"Narlıdere","balcova":"Balçova","guzelbahce":"Güzelbahçe",
    "cesme":"Çeşme","urla":"Urla","seferihisar":"Seferihisar",
    "menderes":"Menderes","torbali":"Torbalı","dirmil":"Dirmil","mustafa":"Mustafa","kemal":"Kemal","kemalapasa":"Kemalpaşa",
    "menemen":"Menemen","aliaga":"Aliağa","bergama":"Bergama",
    "foca":"Foça","pinarbasi":"Pınarbaşı","umit":"Ümit","ataturk":"Atatürk",
    "gultepe":"Gültepe","yesilova":"Yeşilova","yesilkoy":"Yeşilköy",
    "istiklal":"İstiklal","cumhuriyet":"Cumhuriyet","kazimdirik":"Kazımdirik",
    "alsancak":"Alsancak","hatay":"Hatay","yeni":"Yeni","eski":"Eski",
    "merkez":"Merkez","deniz":"Deniz","bahce":"Bahçe","park":"Park",
    "sitesinde":"Sitesi'nde","konforlu":"Konforlu","modern":"Modern",
    "luks":"Lüks","komple":"Komple","duplex":"Dubleks","dubleks":"Dubleks",
    "zeytinlik":"Zeytinlik","sogukpinar":"Soğukpınar","kavaklidere":"Kavaklıdere",
    "ayranci":"Ayrancı","sirinyer":"Şirinyer","bostanli":"Bostanlı",
    "mavişehir":"Mavişehir","mavisehir":"Mavişehir","üçyol":"Üçyol",
    "ucyol":"Üçyol","kizilkanat":"Kızılkanat","firat":"Fırat",
    "ic":"İç","ust":"Üst","yuksek":"Yüksek","genis":"Geniş",
}

def _slug_to_baslik(slug):
    """URL slug'ından okunabilir Türkçe başlık üret."""
    kelimeler = slug.split("-")
    parcalar = []
    for k in kelimeler:
        if not k:
            continue
        parcalar.append(_TR_KELIME.get(k.lower(), k.title()))
    return " ".join(parcalar)


# Slug → Türkçe kelime haritası
_TR_KELIME = {
    "kiralik":"Kiralık","satilik":"Satılık","daire":"Daire","villa":"Villa",
    "arsa":"Arsa","tarla":"Tarla","isyeri":"İşyeri","dukkan":"Dükkan",
    "ofis":"Ofis","bina":"Bina","konut":"Konut","residence":"Residence",
    "mahallesinde":"Mahallesi'nde","mahallesindeki":"Mahallesi'ndeki",
    "mahallesi":"Mahallesi","izmir":"İzmir","karsiyaka":"Karşıyaka",
    "bornova":"Bornova","buca":"Buca","konak":"Konak","bayrakli":"Bayraklı",
    "cigli":"Çiğli","gaziemir":"Gaziemir","karabaglar":"Karabağlar",
    "narlidere":"Narlıdere","balcova":"Balçova","guzelbahce":"Güzelbahçe",
    "cesme":"Çeşme","urla":"Urla","menderes":"Menderes","torbali":"Torbalı","dirmil":"Dirmil","mustafa":"Mustafa","kemal":"Kemal",
    "kemalapasa":"Kemalpaşa","menemen":"Menemen","aliaga":"Aliağa",
    "foca":"Foça","pinarbasi":"Pınarbaşı","umit":"Ümit","ataturk":"Atatürk",
    "gultepe":"Gültepe","yesilova":"Yeşilova","yesilkoy":"Yeşilköy",
    "istiklal":"İstiklal","cumhuriyet":"Cumhuriyet","kazimdirik":"Kazımdirik",
    "alsancak":"Alsancak","yeni":"Yeni","eski":"Eski","merkez":"Merkez",
    "deniz":"Deniz","bahce":"Bahçe","sitesinde":"Sitesi'nde",
    "konforlu":"Konforlu","modern":"Modern","luks":"Lüks","komple":"Komple",
    "duplex":"Dubleks","dubleks":"Dubleks","zeytinlik":"Zeytinlik",
    "sogukpinar":"Soğukpınar","kavaklidere":"Kavaklıdere","ayranci":"Ayrancı",
    "sirinyer":"Şirinyer","bostanli":"Bostanlı","mavisehir":"Mavişehir",
    "ucyol":"Üçyol","kizilkanat":"Kızılkanat","firat":"Fırat",
    "ic":"İç","ust":"Üst","yuksek":"Yüksek","genis":"Geniş","bahceli":"Bahçeli",
}

def _slug_to_baslik(slug):
    """URL slug'ından okunabilir Türkçe başlık üret."""
    parcalar = []
    for k in slug.split("-"):
        if not k:
            continue
        parcalar.append(_TR_KELIME.get(k.lower(), k.title()))
    return " ".join(parcalar)


def _url_parse(url):
    """
    URL pattern: /tr/portfoy/{id}/{islem}/{mulk}/{il}/{ilce}/{slug}
    Örnek: /tr/portfoy/472932/kiralik/daire/izmir/karsiyaka/karsiyaka-mustafa-kemal-...
    """
    sonuc = {
        "portfoy_id": "",
        "islem_tipi": "",
        "mulk_tipi":  "",
        "il":         "",
        "ilce":       "",
        "mahalle":    "",
        "baslik_slug": "",
    }
    # Türkçe karakter haritası — slug latinize → Türkçe
    TR_MAP = str.maketrans({
        "a":"a","e":"e","i":"i","o":"o","u":"u","c":"c","g":"g","s":"s",
        # slug zaten ASCII, başlık için slug kelimelerini title-case yaparız
        # Türkçe kelime düzeltmeleri sonraki adımda
    })
    TR_KELIME = {
        "kiralik":"Kiralık","satilik":"Satılık","daire":"Daire","villa":"Villa",
        "arsa":"Arsa","tarla":"Tarla","isyeri":"İşyeri","dukkan":"Dükkan",
        "ofis":"Ofis","bina":"Bina","konut":"Konut","residence":"Residence",
        "mahallesinde":"Mahallesi'nde","mahallesindeki":"Mahallesi'ndeki",
        "mahallesi":"Mahallesi","izmir":"İzmir","karsiyaka":"Karşıyaka",
        "bornova":"Bornova","buca":"Buca","konak":"Konak","bayrakli":"Bayraklı",
        "cigli":"Çiğli","gaziemir":"Gaziemir","karabaglar":"Karabağlar",
        "narlidere":"Narlıdere","balcova":"Balçova","guzelbahce":"Güzelbahçe",
        "cesme":"Çeşme","urla":"Urla","seferihisar":"Seferihisar",
        "menderes":"Menderes","torbali":"Torbalı","dirmil":"Dirmil","mustafa":"Mustafa","kemal":"Kemal","kemalapasa":"Kemalpaşa",
        "menemen":"Menemen","aliaga":"Aliağa","bergama":"Bergama","dikili":"Dikili",
        "foca":"Foça","pinarbasi":"Pınarbaşı","umit":"Ümit","ataturk":"Atatürk",
        "gultepe":"Gültepe","yesilova":"Yeşilova","yesilkoy":"Yeşilköy",
        "istiklal":"İstiklal","cumhuriyet":"Cumhuriyet","kazimdirik":"Kazımdirik",
        "alsancak":"Alsancak","hatay":"Hatay","mavi":"Mavi","yesil":"Yeşil",
        "ic":"İç","dis":"Dış","ust":"Üst","alt":"Alt","yeni":"Yeni","eski":"Eski",
        "merkez":"Merkez","sehir":"Şehir","deniz":"Deniz","bahce":"Bahçe",
        "park":"Park","site":"Site","sitesinde":"Sitesi'nde","konforlu":"Konforlu",
        "modern":"Modern","luks":"Lüks","satilik":"Satılık","kiralik":"Kiralık",
        "komple":"Komple","duplex":"Dubleks","dubleks":"Dubleks",
        "zeytinlik":"Zeytinlik","gazi":"Gazi","sogukpinar":"Soğukpınar",
        "ayrancılar":"Ayrancılar","ayranci":"Ayrancı","kavaklidere":"Kavaklıdere",
    }

    def _slug_to_baslik(slug, islem="", mulk=""):
        """Slug'dan okunabilir Türkçe başlık üret."""
        kelimeler = slug.split("-")
        cevrilmis = []
        for k in kelimeler:
            if k.isdigit():
                # Sayı — oda sayısı gibi (+1 ekle)
                cevrilmis.append(k)
            else:
                cevrilmis.append(TR_KELIME.get(k.lower(), k.title()))
        return " ".join(cevrilmis)

    try:
        path     = url.replace(BASE_URL, "").strip("/")
        parcalar = path.split("/")
        # [0]='tr', [1]='portfoy', [2]=id, [3]=islem, [4]=mulk, [5]=il, [6]=ilce, [7]=slug

        if len(parcalar) >= 3 and parcalar[2].isdigit():
            sonuc["portfoy_id"] = parcalar[2]

        if len(parcalar) >= 4:
            i = parcalar[3].lower()
            if "kiralik" in i or "kiralık" in i:
                sonuc["islem_tipi"] = "Kiralık"
            elif "satilik" in i or "satılık" in i:
                sonuc["islem_tipi"] = "Satılık"

        if len(parcalar) >= 5:
            MULK_MAP = {
                "daire": "Daire", "villa": "Villa", "arsa": "Arsa",
                "tarla": "Tarla", "isyeri": "İşyeri", "dukkan": "Dükkan",
                "bina": "Bina", "residence": "Residence", "konut": "Konut",
            }
            m_raw = parcalar[4].lower()
            sonuc["mulk_tipi"] = next(
                (v for k, v in MULK_MAP.items() if k in m_raw),
                parcalar[4].title()
            )

        if len(parcalar) >= 6:
            sonuc["il"] = parcalar[5].replace("-", " ").title()
        if len(parcalar) >= 7:
            sonuc["ilce"] = parcalar[6].replace("-", " ").title()

        if len(parcalar) >= 8:
            slug = parcalar[7]
            m = re.search(r"^(.+?)(?:-mahallesinde|-mahallesi|-mah-|-mah\.)", slug)
            if m:
                mah = m.group(1).replace("-", " ").title()
                ilce_lower = sonuc["ilce"].lower()
                if mah.lower().startswith(ilce_lower):
                    mah = mah[len(sonuc["ilce"]):].strip()
                sonuc["mahalle"] = mah
        # Slug'dan başlık üret (her zaman)
        sonuc["baslik_slug"] = _slug_to_baslik(slug)

    except Exception:
        pass
    return sonuc


# ── Liste sayfası — requests yeterli ─────────────────────────────────────────

def _ilan_linkleri_cek(ofis_url, max_sayfa=30, log_fn=None):
    """Ofis portföy listesinden tüm ilan linklerini çek (requests)."""
    linkler = set()

    def log(msg):
        print(msg)
        if log_fn: log_fn(msg)

    for sayfa in range(1, max_sayfa + 1):
        url  = ofis_url if sayfa == 1 else f"{ofis_url}&pageIndex={sayfa}"
        soup = _get_requests(url)
        if soup is None:
            break

        yeni = set()
        for a in soup.find_all("a", href=True):
            if re.search(r"/tr/portfoy/\d+/", a["href"]):
                tam = urljoin(BASE_URL, a["href"]).split("?")[0]
                if tam not in linkler:
                    yeni.add(tam)

        if not yeni:
            log(f"  Sayfa {sayfa}: yeni ilan yok, durduruluyor.")
            break

        linkler |= yeni
        log(f"  Sayfa {sayfa}: {len(yeni)} yeni — toplam {len(linkler)}")
        time.sleep(0.6)

    return list(linkler)


# ── Detay parse — Selenium ────────────────────────────────────────────────────

# Sayfadaki özellik satırı → kolon eşlemesi
_ALAN_MAP = {
    "portföy id":        "portfoy_id",
    "fiyat":             "_skip",
    "portföy tipi":      "_islem",
    "depozito":          "depozito",
    "kat sayısı":        "kat_sayisi",
    "bulunduğu kat":     "bulundugu_kat",
    "balkon sayısı":     "balkon_sayisi",
    "ısıtma tipi":       "isitma_tipi",
    "otopark":           "otopark",
    "asansör":           "asansor",
    "brüt m²":           "brut_m2",
    "net m²":            "net_m2",
    "oda sayısı":        "oda_sayisi",
    "banyo sayısı":      "banyo_sayisi",
    "tuvalet sayısı":    "tuvalet_sayisi",
    "bina yaşı":         "bina_yasi",
    "yapım yılı":        "yapim_yili",
    "tapu durumu":       "tapu_durumu",
    "güncelleme tarihi": "guncelleme_tarihi",
}

_GORSEL_KARA = ["logo", "icon", "flag", "startkey-turkiye", "default",
                "dogrulama", "doğrulama", "sertifika", "qr", "footer-map",
                "footer", "/themes/"]


def _detay_parse_selenium(driver, url, kaynak):
    """
    Selenium driver ile detay sayfasını parse et.
    Driver dışarıdan verilir — tüm ilanlar için paylaşılır.
    """
    url_bilgi = _url_parse(url)

    sonuc = {
        "portfoy_id":        url_bilgi["portfoy_id"],
        "kaynak":            kaynak,
        "startkey_url":      url,
        "islem_tipi":        url_bilgi["islem_tipi"],
        "mulk_tipi":         url_bilgi["mulk_tipi"],
        "il":                url_bilgi["il"],
        "ilce":              url_bilgi["ilce"],
        "mahalle":           url_bilgi["mahalle"],
        "baslik":            "",
        "fiyat":             "",
        "fiyat_num":         None,
        "brut_m2":           "",
        "net_m2":            "",
        "oda_sayisi":        "",
        "kat_sayisi":        "",
        "bulundugu_kat":     "",
        "bina_yasi":         "",
        "yapim_yili":        "",
        "tapu_durumu":       "",
        "isitma_tipi":       "",
        "otopark":           "",
        "asansor":           "",
        "balkon_sayisi":     "",
        "banyo_sayisi":      "",
        "tuvalet_sayisi":    "",
        "depozito":          "",
        "guncelleme_tarihi": "",
        "aciklama":          "",
        "gd_adi":            "",
        "gd_foto_url":       "",
        "gd_telefon":        "",
        "gd_mail":           "",
        "foto_urls":         [],
        "ilk_foto_url":      "",
        "sync_tarihi":       datetime.now(tz=timezone.utc).isoformat(),
    }

    try:
        soup = _selenium_soup(driver, url, bekleme=2.5)
    except Exception as e:
        print(f"  ✗ Selenium hata: {e}")
        return sonuc

    tam_metin = soup.get_text(" ")

    # ── Başlık ────────────────────────────────────────────────────────────────
    h1 = soup.find("h1")
    if h1:
        for el in h1.find_all(["img", "svg", "span"]):
            el.decompose()
        baslik_h1 = _temizle(h1.get_text())
        # h1 anlamlı geldi mi? (en az 5 karakter, sadece sembol değil)
        if len(baslik_h1) >= 5 and any(c.isalpha() for c in baslik_h1):
            sonuc["baslik"] = baslik_h1
    # h1 boş veya anlamsızsa slug'dan üret
    if not sonuc["baslik"]:
        sonuc["baslik"] = url_bilgi.get("baslik_slug", "")

    # ── Fiyat ─────────────────────────────────────────────────────────────────
    # "₺ 26.000" veya "26.000" renk vurgulu element
    for el in soup.find_all(["span", "div", "p", "strong", "b", "h2", "h3"]):
        t = _temizle(el.get_text())
        m = re.match(r"^[₺\s]*([\d\.]+)\s*$", t)
        if m and len(m.group(1).replace(".", "")) >= 4:
            # Rakam string → fiyat
            try:
                num = float(m.group(1).replace(".", ""))
                sonuc["fiyat"]     = f"₺ {m.group(1)}"
                sonuc["fiyat_num"] = num
                break
            except Exception:
                pass

    # ── Konum satırı: "İzmir / Bornova / Ümit" ───────────────────────────────
    for el in soup.find_all(["span", "div", "p", "a"]):
        t = _temizle(el.get_text())
        m = re.match(
            r"^([\w\sÇĞİÖŞÜçğışöü]+?)\s*/\s*([\w\sÇĞİÖŞÜçğışöü]+?)\s*/\s*([\w\sÇĞİÖŞÜçğışöü]+)$",
            t
        )
        if m and len(t) < 80:
            if not sonuc["il"]:
                sonuc["il"] = m.group(1).strip()
            if not sonuc["ilce"]:
                sonuc["ilce"] = m.group(2).strip()
            if not sonuc["mahalle"]:
                sonuc["mahalle"] = m.group(3).strip()
            break

    # ── Özellikler listesi ────────────────────────────────────────────────────
    # Startkey: <li> içinde "Brüt m² 130" veya "Oda Sayısı: 3+1" formatı
    for li in soup.find_all("li"):
        metin = _temizle(li.get_text())
        metin_l = metin.lower()
        for anahtar, kolon in _ALAN_MAP.items():
            if metin_l.startswith(anahtar):
                deger = metin[len(anahtar):].strip(" :").strip()
                if not deger:
                    break
                if kolon == "_skip":
                    break
                if kolon == "_islem":
                    d_l = deger.lower()
                    if not sonuc["islem_tipi"]:
                        sonuc["islem_tipi"] = "Kiralık" if "kira" in d_l else "Satılık"
                    break
                if kolon in sonuc:
                    sonuc[kolon] = deger
                break

    # Portföy ID yoksa metinden al
    if not sonuc["portfoy_id"]:
        m = re.search(r"Portföy\s*(?:Id|ID)\s*:?\s*(\d+)", tam_metin, re.IGNORECASE)
        if m:
            sonuc["portfoy_id"] = m.group(1)

    # ── Açıklama ──────────────────────────────────────────────────────────────
    for h_el in soup.find_all(["h2", "h3"]):
        if "açıklama" in h_el.get_text().lower():
            container = h_el.find_parent(["div", "section"])
            if container:
                metin_blok = _temizle(container.get_text())
                # Başlığı çıkar
                sonuc["aciklama"] = metin_blok.replace(
                    _temizle(h_el.get_text()), ""
                ).strip()[:2000]
            break

    # ── GD bilgileri — sağ panel ──────────────────────────────────────────────
    # Pattern: ad + foto + ofis adı + telefon + mail
    tel_pattern  = re.compile(r"\+90[\s\-\(\)0-9]{10,18}")
    mail_pattern = re.compile(r"[\w\.\-]+@[\w\.\-]+\.com\.tr")

    for el in soup.find_all(["div", "aside", "section"]):
        ic_metin = el.get_text(" ")
        tel_m    = tel_pattern.search(ic_metin)
        mail_m   = mail_pattern.search(ic_metin)

        if not (tel_m or mail_m):
            continue

        # İsim — h2/h3/h4/strong içinde
        _GD_KARA_KELIME = [
            "portföy", "id:", "fiyat", "ilan", "tarih", "tarihi",
            "startkey", "zeta", "gayrimenkul", "ofis",
            "kat sayısı", "oda sayısı", "brüt", "net m", "asansör",
            "tapu", "depozito", "bina", "yapım", "isıtma", "balkon",
            "banyo", "tuvalet", "güncelleme", "açıklama", "konum",
            "satılık", "kiralık", "daire", "villa", "arsa",
        ]
        for isim_el in el.find_all(["h2", "h3", "h4", "strong"]):
            isim_t = _temizle(isim_el.get_text(separator=" ", strip=True))
            # HTML artığı, noktalı virgül, iki nokta üst üste → özellik satırı
            if "<" in isim_t or ">" in isim_t or "style=" in isim_t:
                continue
            if ":" in isim_t:  # "Kat Sayısı:", "Portföy Id:" gibi özellik satırları
                continue
            kelimeler = [k for k in isim_t.split() if k]
            # İsim: 2-4 kelime, baş harf büyük, sayı yok, ≤40 karakter, kara listede değil
            if (2 <= len(kelimeler) <= 4
                    and len(isim_t) <= 40
                    and all(k[0].isupper() for k in kelimeler)
                    and not any(c.isdigit() for c in isim_t)
                    and not any(k in isim_t.lower() for k in _GD_KARA_KELIME)):
                if not sonuc["gd_adi"]:
                    sonuc["gd_adi"] = isim_t
                break

        if tel_m and not sonuc["gd_telefon"]:
            sonuc["gd_telefon"] = _temizle(tel_m.group(0))
        if mail_m and not sonuc["gd_mail"]:
            sonuc["gd_mail"] = mail_m.group(0)

        # GD fotoğrafı — panel içindeki küçük kare/yuvarlak foto
        for img in el.find_all("img"):
            src = img.get("src") or img.get("data-src") or ""
            if not src:
                continue
            src_l = src.lower()
            if any(k in src_l for k in ["logo", "icon", "flag", "banner"]):
                continue
            if any(ext in src_l for ext in [".jpg", ".jpeg", ".png", ".webp"]):
                if not sonuc["gd_foto_url"]:
                    sonuc["gd_foto_url"] = urljoin(BASE_URL, src)
                break

        if sonuc["gd_adi"]:  # Panel bulundu, dur
            break

    # ── Fotoğraflar ───────────────────────────────────────────────────────────
    # Startkey CDN: cdnc.re-os.com/property/{uuid}.jpg?width=...
    # Aynı görsel iki boyutta geliyor:
    #   thumbnail → ?width=412&height=292&mode=Crop
    #   tam boyut → ?width=1920&height=1080&quality=100
    # Sadece tam boyutları al; UUID ile tekrar kontrolü yap.

    foto_urls = []
    goruldu   = set()   # tam URL tekrar engeli
    gorsel_id = set()   # UUID tekrar engeli

    def _foto_filtrele(src):
        low = src.lower()
        if any(k in low for k in _GORSEL_KARA):
            return False
        if not any(ext in low for ext in [".jpg", ".jpeg", ".png", ".webp"]):
            return False
        # Thumbnail parametrelerini at — bunlar küçük kırpılmış varyantlar
        if "mode=crop" in low:
            return False
        if "width=412" in low or "width=150" in low or "width=200" in low:
            return False
        if "height=292" in low or "height=150" in low:
            return False
        return True

    def _gorsel_uuid(src):
        m = re.search(r"/property/([a-f0-9\-]{30,})\.", src, re.IGNORECASE)
        return m.group(1) if m else None

    def _foto_ekle(src):
        if not src:
            return
        tam = urljoin(BASE_URL, src) if src.startswith("/") else src
        if tam in goruldu:
            return
        if tam == sonuc["gd_foto_url"]:
            return
        if not _foto_filtrele(tam):
            return
        uuid = _gorsel_uuid(tam)
        if uuid and uuid in gorsel_id:
            return
        goruldu.add(tam)
        if uuid:
            gorsel_id.add(uuid)
        foto_urls.append(tam)

    for img in soup.find_all("img"):
        for attr in ["src", "data-src", "data-original", "data-lazy"]:
            v = img.get(attr, "")
            if v:
                _foto_ekle(v)
                break

    for el in soup.find_all(attrs={"data-src": True}):
        if el.name != "img":
            _foto_ekle(el.get("data-src", ""))

    sonuc["foto_urls"] = foto_urls
    # ilk_foto_url: parametresiz (tam boyut) URL tercih et
    ilk_foto = ""
    for f in foto_urls:
        if "?" not in f:  # parametresiz = orijinal CDN URL
            ilk_foto = f
            break
    if not ilk_foto and foto_urls:
        ilk_foto = foto_urls[0]  # parametresiz yoksa ilkini al
    sonuc["ilk_foto_url"] = ilk_foto

    return sonuc


# ── Supabase client ───────────────────────────────────────────────────────────

def _supabase():
    """
    Supabase client — üç kaynaktan sırayla dener:
      1. core.supabase_client.get_client()  (Karma App içinden)
      2. st.secrets["supabase"]             (Streamlit / secrets.toml)
      3. SUPABASE_URL + SUPABASE_KEY env    (terminal CLI)
    """
    # 1. Karma App core client
    try:
        from core.supabase_client import get_client
        return get_client()
    except Exception:
        pass

    # 2. st.secrets
    try:
        import streamlit as st
        from supabase import create_client
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["secret_key"]
        return create_client(url, key)
    except Exception:
        pass

    # 3. Environment variables
    from supabase import create_client
    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_KEY", "")
    if not url or not key:
        print("HATA: Supabase bağlantısı kurulamadı.")
        print("  Çözüm A — Karma App sync butonunu kullan.")
        print("  Çözüm B — .streamlit/secrets.toml kontrol et.")
        print("  Çözüm C — SUPABASE_URL + SUPABASE_KEY env tanımla.")
        sys.exit(1)
    return create_client(url, key)


# ── Supabase yazma ────────────────────────────────────────────────────────────

def _supabase_yaz(supa, kayitlar, log_fn=None):
    def log(msg):
        print(msg)
        if log_fn: log_fn(msg)

    BATCH  = 50
    toplam = 0
    for i in range(0, len(kayitlar), BATCH):
        batch = []
        for k in kayitlar[i:i + BATCH]:
            kk = dict(k)
            kk["foto_urls"] = json.dumps(kk.get("foto_urls") or [], ensure_ascii=False)
            batch.append(kk)
        supa.table("startkey_portfoyler").upsert(
            batch, on_conflict="startkey_url"
        ).execute()
        toplam += len(batch)
        log(f"  {toplam}/{len(kayitlar)} kayıt yazıldı")
    return toplam


def _kapanan_pasifle(supa, kaynak, aktif_urller, log_fn=None):
    def log(msg):
        print(msg)
        if log_fn: log_fn(msg)
    try:
        res = (supa.table("startkey_portfoyler")
               .select("startkey_url")
               .eq("kaynak", kaynak)
               .eq("aktif", True)
               .execute())
        eski  = {r["startkey_url"] for r in (res.data or [])}
        kapan = eski - set(aktif_urller)
        if kapan:
            supa.table("startkey_portfoyler").update({
                "aktif":       False,
                "sync_tarihi": datetime.now(tz=timezone.utc).isoformat()
            }).in_("startkey_url", list(kapan)).execute()
            log(f"  ⚠ {len(kapan)} ilan pasife alındı")
    except Exception as e:
        log(f"  Pasife alma hatası: {e}")


# ── Ana sync fonksiyonları ────────────────────────────────────────────────────

def sync_ofis(kaynak, log_fn=None, limit=None):
    """
    Tek ofis sync eder.
    Karma App içinden veya terminalden çağrılabilir.
    limit: sadece ilk N ilanı işle (test için)
    """
    ofis = OFISLER.get(kaynak)
    if not ofis:
        raise ValueError(f"Bilinmeyen kaynak: {kaynak}")

    def log(msg):
        print(msg)
        if log_fn: log_fn(msg)

    supa = _supabase()

    # ── Adım 1: Liste sayfasından linkler (requests) ──────────────────────────
    log(f"\n── {ofis['label']} ilan linkleri çekiliyor (requests)...")
    linkler = _ilan_linkleri_cek(ofis["url"], log_fn=log_fn)
    log(f"  {len(linkler)} ilan bulundu")

    if not linkler:
        log(f"⚠ {ofis['label']}: Hiç ilan bulunamadı")
        return 0

    if limit:
        linkler = linkler[:limit]
        log(f"  ⚡ Test modu: ilk {limit} ilan işlenecek")

    # ── Adım 2: Detaylar — tek Selenium driver ───────────────────────────────
    log(f"\n── {ofis['label']} detayları çekiliyor (Selenium headless)...")
    driver   = None
    kayitlar = []
    try:
        driver = _driver_olustur(headless=True)
        for i, url in enumerate(linkler, 1):
            slug = url.split("/")[-1][:55]
            log(f"  [{i}/{len(linkler)}] {slug}...")
            try:
                detay = _detay_parse_selenium(driver, url, kaynak)
                if detay:
                    detay["aktif"] = True
                    kayitlar.append(detay)
                    # Kısa özet log
                    log(f"    → {detay.get('baslik','—')[:50]} | "
                        f"{detay.get('fiyat','—')} | "
                        f"{len(detay.get('foto_urls',[]))} foto")
            except Exception as e:
                log(f"    ✗ Hata: {e}")
            time.sleep(0.8)   # sunucuya nazik ol
    finally:
        if driver:
            try: driver.quit()
            except Exception: pass

    # ── Adım 3: Supabase ─────────────────────────────────────────────────────
    if kayitlar:
        log(f"\n── Supabase'e yazılıyor ({len(kayitlar)} kayıt)...")
        _supabase_yaz(supa, kayitlar, log_fn=log_fn)
        _kapanan_pasifle(supa, kaynak, linkler, log_fn=log_fn)
        log(f"✅ {ofis['label']}: {len(kayitlar)} ilan sync edildi")
    else:
        log(f"⚠ {ofis['label']}: Hiç kayıt çekilemedi")

    return len(kayitlar)


def sync_tum(log_fn=None, limit=None):
    """Zeta 1 + Zeta 2 birlikte sync et."""
    toplam = 0
    for kaynak in ["zeta1", "zeta2"]:
        try:
            toplam += sync_ofis(kaynak, log_fn=log_fn, limit=limit)
        except Exception as e:
            msg = f"HATA [{kaynak}]: {e}"
            print(msg)
            if log_fn: log_fn(msg)
    return toplam


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Startkey Portföy Sync")
    parser.add_argument("--ofis", choices=["zeta1", "zeta2", "tum"],
                        default="tum", help="Hangi ofis sync edilsin")
    args = parser.parse_args()

    print(f"Startkey Portföy Sync — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)

    if args.ofis == "tum":
        toplam = sync_tum()
    else:
        toplam = sync_ofis(args.ofis)

    print(f"\n✅ Tamamlandı — toplam {toplam} ilan işlendi.")
