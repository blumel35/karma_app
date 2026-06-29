import re
import json
import time
import pandas as pd
import requests

from pathlib import Path
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options


BASE_URL = "https://www.startkey.com.tr"

STARTKEY_OFFICES = {
    "zeta1": {
        "label": "ZETA 1",
        "office_id": "18830",
        "url": "https://www.startkey.com.tr/tr/portfoy?FilterDTO.OfficeId=18830",
    },
    
    "zeta2": {
    "label": "ZETA 2",
    "office_id": "18824",
    "url": "https://www.startkey.com.tr/tr/portfoy?FilterDTO.OfficeId=18824",
}
}

OUTPUT_DIR = Path("debug_startkey")
OUTPUT_DIR.mkdir(exist_ok=True)


def clean_text(text):
    if not text:
        return ""
    text = str(text).replace("\n", " ").replace("\r", " ").replace("\t", " ")
    return re.sub(r"\s+", " ", text).strip()


def setup_driver():
    options = Options()
    options.add_argument("--start-maximized")
    return webdriver.Chrome(options=options)


def title_from_slug(url):
    slug = urlparse(url).path.strip("/").split("/")[-1]
    return slug.replace("-", " ").title()


def get_html(url):
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8",
    }
    r = requests.get(url, headers=headers, timeout=30)
    r.raise_for_status()
    return r.text


def scroll_to_bottom(driver):
    last_height = 0
    for _ in range(5):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1.2)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height


def parse_listing_page(driver, page_no, office_key):
    soup = BeautifulSoup(driver.page_source, "html.parser")
    rows = []
    seen = set()

    for a in soup.find_all("a", href=True):
        href = a.get("href", "")
        if "/tr/portfoy/" not in href:
            continue

        full_url = urljoin(BASE_URL, href)

        if full_url in seen:
            continue

        seen.add(full_url)

        card = a
        for _ in range(6):
            if card.parent:
                card = card.parent

        text = clean_text(card.get_text(" "))

        rows.append({
            "kaynak": office_key,
            "sayfa": page_no,
            "portfoy_link": full_url,
            "kart_metin": text,
        })

    return rows


def click_next_page(driver, current_page):
    next_page = current_page + 1

    candidates = [
        f"//a[normalize-space()='{next_page}']",
        f"//button[normalize-space()='{next_page}']",
        "//a[contains(., 'Sonraki')]",
        "//button[contains(., 'Sonraki')]",
        "//a[contains(., 'Next')]",
        "//button[contains(., 'Next')]",
        "//a[contains(., '›')]",
        "//button[contains(., '›')]",
    ]

    for xp in candidates:
        try:
            elements = driver.find_elements(By.XPATH, xp)
            for el in elements:
                if el.is_displayed() and el.is_enabled():
                    driver.execute_script(
                        "arguments[0].scrollIntoView({block:'center'});",
                        el
                    )
                    time.sleep(0.5)
                    driver.execute_script("arguments[0].click();", el)
                    time.sleep(2.5)
                    return True
        except Exception:
            pass

    return False


def fetch_listing_links_for_office(office_key, max_pages=20, log_fn=None):
    office = STARTKEY_OFFICES.get(office_key)

    if not office:
        raise ValueError(f"Bilinmeyen ofis: {office_key}")

    if not office.get("url"):
        raise ValueError(f"{office_key} için Startkey URL tanımlı değil.")

    def log(msg):
        print(msg)
        if log_fn:
            log_fn(msg)

    driver = setup_driver()
    all_rows = []
    all_links = set()

    try:
        log(f"🌐 {office['label']} Startkey sayfası açılıyor...")
        driver.get(office["url"])
        time.sleep(5)

        for page_no in range(1, max_pages + 1):
            log(f"📄 {office['label']} sayfa {page_no} okunuyor...")

            scroll_to_bottom(driver)
            rows = parse_listing_page(driver, page_no, office_key)

            new_rows = []
            for row in rows:
                link = row["portfoy_link"]
                if link not in all_links:
                    all_links.add(link)
                    new_rows.append(row)

            all_rows.extend(new_rows)

            log(f"Bu sayfa: {len(rows)} | Yeni: {len(new_rows)} | Toplam: {len(all_rows)}")

            if len(new_rows) == 0:
                break

            if not click_next_page(driver, page_no):
                break

    finally:
        driver.quit()

    df = pd.DataFrame(all_rows)

    output_file = OUTPUT_DIR / f"startkey_{office_key}_links.xlsx"
    df.to_excel(output_file, index=False)

    log(f"✅ {office['label']} link çıktısı: {output_file}")

    return df


def extract_images(soup, url):
    images = []

    for img in soup.find_all("img"):
        src = (
            img.get("src")
            or img.get("data-src")
            or img.get("data-original")
            or img.get("data-lazy")
        )

        if not src:
            continue

        full = urljoin(url, src)
        low = full.lower()

        parent_text = ""
        parent = img.parent
        for _ in range(4):
            if parent:
                parent_text += " " + clean_text(parent.get_text(" "))
                parent = parent.parent

        parent_low = parent_text.lower()

        blacklist = [
            "logo", "icon", "avatar", "flag", "flags", "svg",
            "banner", "favicon", "user", "dogrulama", "doğrulama",
            "elektronik", "eids", "qr", "sertifika", "certificate",
            "startkey-turkiye", "default", "placeholder"
        ]

        if any(x in low for x in blacklist):
            continue

        if any(x in parent_low for x in blacklist):
            continue

        if not any(x in low for x in [".jpg", ".jpeg", ".png", ".webp"]):
            continue

        images.append(full)

    return list(dict.fromkeys(images))


def extract_price(text):
    m = re.search(r"₺\s*[\d\.\,]+|[\d\.\,]+\s*TL", text)
    return clean_text(m.group(0)) if m else ""


def extract_m2(text, label):
    patterns = [
        rf"{label}\s*Alan\s*([\d\.\,]+)",
        rf"{label}\s*([\d\.\,]+)\s*(?:m2|m²)?",
    ]

    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            return clean_text(m.group(1))

    return ""


def extract_room(text):
    m = re.search(r"\b(\d+\+\d+)\b", text)
    return m.group(1) if m else ""


def extract_portfoy_id(url, text=""):
    m = re.search(r"/portfoy/(\d+)", url)
    if m:
        return m.group(1)

    m = re.search(r"Portföy\s*Id\s*:?\s*(\d+)", text, re.IGNORECASE)
    if m:
        return m.group(1)

    return ""


def extract_operation_type(text):
    t = text.lower()
    if "kiralık" in t:
        return "Kiralık"
    if "satılık" in t:
        return "Satılık"
    return ""


def extract_property_type(text):
    types = ["Daire", "Villa", "Arsa", "Tarla", "İş Yeri", "Dükkan", "Bina", "Residence"]
    for x in types:
        if x.lower() in text.lower():
            return x
    return ""


def parse_detail(url, office_key):
    html = get_html(url)
    soup = BeautifulSoup(html, "html.parser")
    text = clean_text(soup.get_text(" "))

    images = extract_images(soup, url)

    # İlk görsel bazen doğrulama/yardımcı görsel olabildiği için 2. görsel güvenli fallback.
    first_photo = ""
    if len(images) > 1:
        first_photo = images[1]
    elif len(images) == 1:
        first_photo = images[0]

    return {
        "kaynak": office_key,
        "startkey_portfoy_id": extract_portfoy_id(url, text),
        "baslik": title_from_slug(url),
        "fiyat": extract_price(text),
        "brut_m2": extract_m2(text, "Brüt"),
        "net_m2": extract_m2(text, "Net"),
        "oda_sayisi": extract_room(text),
        "islem_tipi": extract_operation_type(text),
        "mulk_tipi": extract_property_type(text),
        "foto_sayisi": len(images),
        "ilk_foto_url": first_photo,
        "foto_url_listesi": json.dumps(images, ensure_ascii=False),
        "startkey_detay_link": url,
        "ham_metin_ilk_1500": text[:1500],
    }


def fetch_details_for_office(office_key, links_df=None, limit=None, log_fn=None):
    office = STARTKEY_OFFICES.get(office_key)

    if not office:
        raise ValueError(f"Bilinmeyen ofis: {office_key}")

    def log(msg):
        print(msg)
        if log_fn:
            log_fn(msg)

    if links_df is None:
        links_file = OUTPUT_DIR / f"startkey_{office_key}_links.xlsx"
        if not links_file.exists():
            links_df = fetch_listing_links_for_office(office_key, log_fn=log_fn)
        else:
            links_df = pd.read_excel(links_file)

    links = (
        links_df["portfoy_link"]
        .dropna()
        .astype(str)
        .drop_duplicates()
        .tolist()
    )

    if limit:
        links = links[:limit]

    rows = []

    for i, link in enumerate(links, start=1):
        log(f"🏠 {office['label']} detay {i}/{len(links)} çekiliyor...")
        try:
            rows.append(parse_detail(link, office_key))
        except Exception as e:
            rows.append({
                "kaynak": office_key,
                "startkey_detay_link": link,
                "hata": str(e),
            })
        time.sleep(0.4)

    df = pd.DataFrame(rows)

    output_excel = OUTPUT_DIR / f"startkey_{office_key}_details.xlsx"
    output_json = OUTPUT_DIR / f"startkey_{office_key}_details.json"

    df.to_excel(output_excel, index=False)
    output_json.write_text(
        json.dumps(rows, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    log(f"✅ {office['label']} detay çıktısı: {output_excel}")

    return df


def sync_startkey_office(office_key, limit=None, log_fn=None):
    links_df = fetch_listing_links_for_office(office_key, log_fn=log_fn)
    detail_df = fetch_details_for_office(
        office_key=office_key,
        links_df=links_df,
        limit=limit,
        log_fn=log_fn
    )
    return detail_df


def sync_startkey_all(limit=None, log_fn=None):
    results = {}

    for office_key in ["zeta1", "zeta2"]:
        office = STARTKEY_OFFICES.get(office_key, {})
        if not office.get("url"):
            results[office_key] = {"hata": "Startkey URL tanımlı değil."}
            continue

        try:
            df = sync_startkey_office(office_key, limit=limit, log_fn=log_fn)
            results[office_key] = {
                "kayit": len(df),
                "excel": str(OUTPUT_DIR / f"startkey_{office_key}_details.xlsx")
            }
        except Exception as e:
            results[office_key] = {"hata": str(e)}

    return results


if __name__ == "__main__":
    print("Startkey Sync başlıyor...")
    sonuc = sync_startkey_all(limit=None)
    print(sonuc)