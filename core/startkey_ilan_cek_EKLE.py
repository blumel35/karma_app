# ─────────────────────────────────────────────────────────────────────────────
# STARTKEY İLAN ÇEKİCİ
# Bu bloğu mevcut revy_pazar_cek.py dosyasının en SONUNA ekle.
# Bağımlılıklar (requests, openpyxl, pandas, Path, datetime, session_olustur)
# zaten dosyanın üst bölümünde mevcut.
# ─────────────────────────────────────────────────────────────────────────────

STARTKEY_BAZA_URL = "https://revy.com.tr/app/portfoy/ilanlar"


def startkey_ilan_cek(cookie_dict, filtre=None, cikti_klasor=None, progress_cb=None):
    """
    Revy'den tüm Startkey ilanlarını keyword aramasıyla çeker.

    Endpoint:
        GET https://revy.com.tr/app/portfoy/ilanlar
        Params: export=1, area=all, keyword=startkey,
                advertisement_status=active | suspended

    filtre = {
        "durum": ["aktif"]                           # varsayılan
                 | ["yayindan_kalkan"]
                 | ["aktif", "yayindan_kalkan"]
    }

    Döndürür: pd.DataFrame
        Sütunlar: Revy'nin doğal çıktısı + "_durum" + "Ofis_normalize"
    """
    if filtre is None:
        filtre = {}
    if cikti_klasor is None:
        cikti_klasor = Path(__file__).parent.parent / "revy_startkey_cikti"
    klasor = Path(cikti_klasor)
    klasor.mkdir(exist_ok=True)

    session, headers = session_olustur(cookie_dict)

    durum_map    = {"aktif": "active", "yayindan_kalkan": "suspended"}
    secilen      = filtre.get("durum", ["aktif"])

    parcalar = []

    for durum_ad in secilen:
        durum_val = durum_map.get(durum_ad, "active")
        if progress_cb:
            progress_cb(f"📡 Startkey {durum_ad} ilanları çekiliyor...")

        params = {
            "export":               "1",
            "area":                 "all",
            "keyword":              "startkey",
            "advertisement_status": durum_val,
        }
        if durum_val == "suspended":
            params["tab"] = "archive"

        zaman = datetime.now().strftime("%Y%m%d_%H%M%S")
        dosya = klasor / f"startkey_{durum_ad}_{zaman}.xlsx"

        try:
            r = session.get(
                STARTKEY_BAZA_URL,
                params=params,
                headers=headers,
                timeout=90,
                stream=True,
            )
            ct = r.headers.get("Content-Type", "")
            is_xlsx = (
                "spreadsheet" in ct
                or "excel"       in ct
                or r.content[:4] == b"PK\x03\x04"
            )

            if r.status_code == 200 and is_xlsx:
                dosya.write_bytes(r.content)
                df_parca = pd.read_excel(dosya)
                df_parca["_durum"] = durum_ad
                parcalar.append(df_parca)
                if progress_cb:
                    progress_cb(f"✅ {durum_ad}: {len(df_parca):,} ilan")
            else:
                if progress_cb:
                    progress_cb(
                        f"⚠️ {durum_ad}: Beklenmeyen yanıt "
                        f"(HTTP {r.status_code}, Content-Type: {ct[:60]})"
                    )

        except Exception as e:
            if progress_cb:
                progress_cb(f"❌ {durum_ad} çekim hatası: {e}")

        finally:
            try:
                dosya.unlink(missing_ok=True)
            except Exception:
                pass

    if not parcalar:
        return pd.DataFrame()

    birlesik = pd.concat(parcalar, ignore_index=True)

    # URL bazlı duplicate temizle
    url_col = next((c for c in birlesik.columns if "url" in c.lower()), None)
    if url_col:
        birlesik = birlesik.drop_duplicates(subset=[url_col], keep="first")

    # Ofis adını normalize et (büyük/küçük harf + çoklu boşluk tutarsızlığı)
    if "Ofis" in birlesik.columns:
        birlesik["Ofis_normalize"] = (
            birlesik["Ofis"]
            .fillna("")
            .str.strip()
            .str.upper()
            .str.replace(r"\s+", " ", regex=True)
        )

    if progress_cb:
        progress_cb(f"🔗 Toplam: {len(birlesik):,} Startkey ilanı hazır")

    return birlesik
