import streamlit as st
import sys, os, re, html
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.ui_helpers import render_navbar, render_page_header
from core.supabase_client import get_client
from core.mail_paylas import render_mail_paylas_widget
from core.auth import oturum_kontrol

if not oturum_kontrol():
    st.switch_page("pages/giris.py")


# ─────────────────────────────────────────────────────────────────────────────
# NAVBAR
# ─────────────────────────────────────────────────────────────────────────────
render_navbar(
    user_role=st.session_state.get("user_role", "danisan"),
    user_name=st.session_state.get("user_name", ""),
    user_initials=st.session_state.get("user_initials", ""),
)

if st.button("← Çalışma Alanına Dön", key="pm_geri_kokpit"):
    st.switch_page("pages/gd_calisma_alani.py")


# ─────────────────────────────────────────────────────────────────────────────
# SABİTLER
# ─────────────────────────────────────────────────────────────────────────────
ILLER = ["İzmir", "Aydın", "Manisa", "Balıkesir", "Muğla", "İstanbul", "Ankara", "Diğer"]
BUCKET = "portfoy-fotograflari"

REVVY_AKTIF_KAYNAKLAR = ["zeta1", "zeta2"]

KAPALI_KAYNAKLAR = {
    "ofis_gizli",
    "kapali",
    "manuel_kapali",
    "kapali_portfoy",
    "gizli",
}

MANUEL_KOPRU_KAYNAKLAR = {
    "manuel_kopru",
    "kopru",
    "kopru_portfoy",
}


# ─────────────────────────────────────────────────────────────────────────────
# GENEL HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def h(s):
    return html.escape(str(s or ""))


def isim_ayikla(g):
    if not g:
        return ""
    g = str(g)
    if "<" in g:
        g = g[:g.index("<")].strip()
    return re.sub(r"[\"']", "", g).strip()


def normalize_text(s):
    s = isim_ayikla(s).lower().strip()
    tr_map = str.maketrans({
        "ı": "i",
        "İ": "i",
        "ğ": "g",
        "ü": "u",
        "ş": "s",
        "ö": "o",
        "ç": "c",
    })
    s = s.translate(tr_map)
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def isim_eslesir(a, b):
    a = normalize_text(a)
    b = normalize_text(b)

    if not a or not b:
        return False

    if a == b:
        return True

    if a in b or b in a:
        return True

    return False


def bool_deger(v):
    if isinstance(v, bool):
        return v
    if v is None:
        return False
    if isinstance(v, (int, float)):
        return bool(v)

    s = str(v).strip().lower()
    return s in {"true", "1", "evet", "yes", "x"}


def tarih_parse(s):
    if not s:
        return None

    s = str(s)

    for fmt in (
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
        "%d.%m.%Y",
        "%d/%m/%Y",
    ):
        try:
            return datetime.strptime(s[:26], fmt)
        except:
            pass

    return None


def en_iyi_tarih(v):
    for k in [
        "ilan_tarihi",
        "mail_tarihi",
        "paylasim_tarihi",
        "gonderim_tarihi",
        "tarih",
        "kayit_tarihi",
        "olusturma_tarihi",
        "created_at",
        "guncelleme_tarihi",
    ]:
        val = v.get(k)
        if val:
            return str(val)
    return ""


def tarih_str(v):
    d = tarih_parse(en_iyi_tarih(v))
    if not d:
        return "—"
    return d.strftime("%d.%m.%Y")


def tarih_saat_str(v):
    d = tarih_parse(en_iyi_tarih(v))
    if not d:
        return "—"
    return d.strftime("%d.%m.%Y\n%H:%M")


def ilce_grubu(v):
    ilceler = v.get("ilceler") or []
    ilce = v.get("ilce", "") or ""

    tum = ([ilce] if ilce else []) + [i for i in ilceler if i != ilce]
    tum = [i for i in tum if i and i != "Diğer Bölge"]

    return " · ".join(tum[:2]) if tum else (v.get("mahalle", "") or "—")


def lokasyon_text(v):
    il = v.get("il", "") or "İzmir"
    ilce = v.get("ilce", "") or ""
    mahalle = v.get("mahalle", "") or v.get("bolge_mahalle", "") or ""

    parcalar = [x for x in [il, ilce, mahalle] if x and x != "—"]
    if parcalar:
        return " / ".join(parcalar)

    return ilce_grubu(v)


def tip_badge(islem):
    islem_low = (islem or "").lower()

    if "kiralık" in islem_low or "kiralik" in islem_low:
        return "#EAF2FF", "#2F6FED", "Kiralık"

    if "satılık" in islem_low or "satilik" in islem_low:
        return "#FFF1F2", "#E15263", "Satılık"

    return "#F8FAFC", "#64748B", islem or "—"


def kaynak_etiketi(v):
    kaynak = (v.get("kaynak", "") or "").lower()

    if kaynak == "zeta1":
        return "Startkey Zeta 1"

    if kaynak == "zeta2":
        return "Startkey Zeta 2"

    if kaynak == "ofis":
        return "Startkey Zeta"

    if kaynak == "startkey_mail":
        return "Startkey"

    if kaynak in KAPALI_KAYNAKLAR:
        return "Kapalı Portföy"

    return ""


def portfoy_sahibi_adi(v):
    raw = (
        isim_ayikla(v.get("talep_eden_danisan", ""))
        or isim_ayikla(v.get("portfoy_sahibi", ""))
        or isim_ayikla(v.get("danisman", ""))
        or isim_ayikla(v.get("giren_gd", ""))
        or ""
    )

    if not raw:
        return "—"

    kaynak_lbl = kaynak_etiketi(v)
    if kaynak_lbl and kaynak_lbl.lower() not in raw.lower():
        return f"{raw} · {kaynak_lbl}"

    return raw


def foto_url_listesi(v):
    urls = []

    raw = v.get("foto_url", "") or ""
    if raw:
        urls.extend([
            u.strip()
            for u in str(raw).split(",")
            if u.strip().startswith("http")
        ])

    for key in [
        "ilk_foto_url",
        "startkey_foto_url",
        "vitrin_foto",
        "ana_foto",
        "image_url",
        "resim_url",
        "foto",
    ]:
        val = v.get(key, "")
        if val and str(val).strip().startswith("http"):
            urls.append(str(val).strip())

    for key in ["foto_url_listesi", "gorsel_urls", "foto_urls", "images"]:
        val = v.get(key)

        if isinstance(val, list):
            urls.extend([
                str(u).strip()
                for u in val
                if str(u).strip().startswith("http")
            ])

        elif val:
            try:
                import ast
                parsed = ast.literal_eval(str(val))
                if isinstance(parsed, list):
                    urls.extend([
                        str(u).strip()
                        for u in parsed
                        if str(u).strip().startswith("http")
                    ])
            except:
                urls.extend([
                    u.strip()
                    for u in str(val).split(",")
                    if u.strip().startswith("http")
                ])

    temiz = []
    seen = set()

    for u in urls:
        if u not in seen:
            temiz.append(u)
            seen.add(u)

    return temiz


def kayit_kapali_mi(v):
    kaynak = (v.get("kaynak", "") or "").lower().strip()

    if bool_deger(v.get("kapali_portfoy", False)):
        return True

    if bool_deger(v.get("gizli", False)):
        return True

    if kaynak in KAPALI_KAYNAKLAR:
        return True

    return False


def kayit_manuel_kopru_mu(v):
    kaynak = (v.get("kaynak", "") or "").lower().strip()

    if kaynak in MANUEL_KOPRU_KAYNAKLAR:
        return True

    if bool_deger(v.get("kopru_portfoy", False)):
        return True

    return False


def kayit_revy_aktif_mi(v):
    kaynak = (v.get("kaynak", "") or "").lower().strip()
    aktif = bool_deger(v.get("aktif", False))
    return kaynak in REVVY_AKTIF_KAYNAKLAR and aktif


def kayit_kullaniciya_ait_mi(v, user_id, user_name, user_email=""):
    if user_id and str(v.get("user_id", "") or "") == str(user_id):
        return True

    aday_isimler = [
        user_name,
        st.session_state.get("user_name", ""),
        st.session_state.get("user_full_name", ""),
    ]

    kayit_isimleri = [
        v.get("giren_gd", ""),
        v.get("talep_eden_danisan", ""),
        v.get("danisman", ""),
        v.get("portfoy_sahibi", ""),
        v.get("ekleyen", ""),
    ]

    for a in aday_isimler:
        for b in kayit_isimleri:
            if isim_eslesir(a, b):
                return True

    if user_email:
        user_email = str(user_email).lower().strip()
        kayit_email = str(v.get("email", "") or v.get("danisman_email", "") or "").lower().strip()
        if user_email and kayit_email and user_email == kayit_email:
            return True

    return False


def kayit_kullanici_tarafindan_girilmis_mi(v, user_id, user_name, user_email=""):
    if user_id and str(v.get("user_id", "") or "") == str(user_id):
        return True

    if isim_eslesir(user_name, v.get("giren_gd", "")):
        return True

    if isim_eslesir(user_name, v.get("ekleyen", "")):
        return True

    if user_email:
        user_email = str(user_email).lower().strip()
        kayit_email = str(v.get("email", "") or v.get("danisman_email", "") or "").lower().strip()
        if user_email and kayit_email and user_email == kayit_email:
            return True

    return False


def mulk_sahibi_adi(musteri_map, kid):
    return musteri_map.get(str(kid), "")


# ─────────────────────────────────────────────────────────────────────────────
# VERİ FONKSİYONLARI
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=60)
def ilce_listesi_cek():
    try:
        r = get_client().table("ilceler").select("ilce").execute()
        return sorted([x["ilce"] for x in r.data if x.get("ilce")])
    except:
        return []


@st.cache_data(ttl=60)
def mahalle_lookup_cek():
    try:
        r = get_client().table("mahalleler").select("il,ilce,mahalle").execute()
        return {
            row["mahalle"].strip().lower(): (row["il"], row["ilce"])
            for row in r.data
            if row.get("mahalle")
        }
    except:
        return {}


def mahalle_ile_ilce_bul(metin):
    if not metin:
        return {}

    lookup = mahalle_lookup_cek()
    metin_lower = metin.lower()
    eslesme = {}

    for mh_lower, (il, ilce) in lookup.items():
        if mh_lower in metin_lower:
            if not eslesme or len(mh_lower) > len(list(eslesme.keys())[0]):
                eslesme = {mh_lower: (il, ilce, mh_lower)}

    if eslesme:
        _, (il, ilce, mh) = list(eslesme.items())[0]
        return {"il": il, "ilce": ilce, "mahalle": mh}

    return {}


def foto_yukle(portfoy_id, dosyalar):
    import uuid, mimetypes

    client = get_client()
    urls = []
    hatalar = []

    for dosya in dosyalar:
        try:
            ext = dosya.name.split(".")[-1].lower()
            dosya_adi = f"{portfoy_id}/{uuid.uuid4()}.{ext}"
            mime = mimetypes.guess_type(dosya.name)[0] or "image/jpeg"

            client.storage.from_(BUCKET).upload(
                path=dosya_adi,
                file=dosya.getvalue(),
                file_options={"content-type": mime, "upsert": "true"},
            )

            url = client.storage.from_(BUCKET).get_public_url(dosya_adi)
            if url:
                urls.append(url)

        except Exception as e:
            hatalar.append(f"{dosya.name}: {e}")

    return urls, hatalar


def favori_guncelle(kid, mevcut):
    try:
        get_client().table("portfoyler").update({"favori": not mevcut}).eq("id", kid).execute()
        st.cache_data.clear()
        st.rerun(scope="app")
    except Exception as e:
        st.error(f"Hata: {e}")


def kayit_guncelle(kid, data):
    try:
        get_client().table("portfoyler").update(data).eq("id", kid).execute()
        st.cache_data.clear()
        st.success("Kayıt güncellendi.")
        # NOT: Bu işlem satırın kendisinde görünen başlık/bilgileri de değiştirir
        # (render_portfoy_detay_panel bir fragment, ama üstteki satır başlığı
        # fragment DIŞINDA) — o yüzden burada istisnai olarak tüm sayfa
        # yenileniyor, diğer işlemler (not/foto/mail) fragment içinde kalıp
        # sayfa kaymasını önlüyor.
        st.rerun(scope="app")
    except Exception as e:
        st.error(f"Güncelleme hatası: {e}")


def portfoy_kaydet(veri):
    try:
        r = get_client().table("portfoyler").insert(veri).execute()
        st.cache_data.clear()
        if r.data:
            return r.data[0]
        return {}
    except Exception as e:
        st.error(f"Kayıt hatası: {e}")
        return None


def ai_parse_portfoy(metin):
    import requests, json

    prompt = f"""Aşağıdaki gayrimenkul portföy açıklamasını analiz et ve JSON olarak döndür.
Sadece JSON döndür, başka hiçbir şey yazma.

Portföy:
{metin}

JSON:
{{
  "il": "İzmir",
  "ilce": "",
  "ilceler": [],
  "mulk_tipi": "Konut/İşyeri/Arsa/Belirsiz",
  "islem_tipi": "Satılık/Kiralık/Belirsiz",
  "oda_sayisi_m2": "",
  "fiyat": "",
  "mahalle": "",
  "ozel_kriterler": "",
  "ozet": "",
  "ilan_linki": ""
}}"""

    try:
        api_key = st.secrets["anthropic"]["api_key"].strip()

        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "Content-Type": "application/json",
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
            },
            json={
                "model": "claude-sonnet-4-6",
                "max_tokens": 600,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=30,
        )

        data = resp.json()

        if "error" in data:
            return {"_hata": str(data["error"])}

        text = data["content"][0]["text"].strip()
        text = text.replace("```json", "").replace("```", "").strip()

        return json.loads(text)

    except Exception as e:
        return {"_hata": str(e)}


@st.cache_data(ttl=60)
def revy_aktif_portfoyleri_cek():
    """
    Zeta Ofis Paneli ile aynı mantık:
    kaynak zeta1/zeta2 + aktif True + ilan_tarihi desc + sayfalama.
    """
    try:
        tum_veri = []
        sayfa_boyu = 1000
        bas = 0

        while True:
            r = (
                get_client()
                .table("portfoyler")
                .select("*")
                .in_("kaynak", REVVY_AKTIF_KAYNAKLAR)
                .eq("aktif", True)
                .order("ilan_tarihi", desc=True)
                .range(bas, bas + sayfa_boyu - 1)
                .execute()
            )

            parca = r.data or []
            tum_veri.extend(parca)

            if len(parca) < sayfa_boyu:
                break

            bas += sayfa_boyu

        return tum_veri

    except Exception as e:
        st.error(f"Revy aktif portföyleri yüklenemedi: {e}")
        return []


@st.cache_data(ttl=60)
def manuel_kayitlari_cek():
    """
    Revy aktif ilan verisi dışında kalan manuel kayıtları çeker.
    Kapalı portföy ve manuel köprü portföyler buradan ayrıştırılır.
    """
    try:
        tum_veri = []
        sayfa_boyu = 1000
        bas = 0

        while True:
            r = (
                get_client()
                .table("portfoyler")
                .select("*")
                .order("olusturma_tarihi", desc=True)
                .range(bas, bas + sayfa_boyu - 1)
                .execute()
            )

            parca = r.data or []
            tum_veri.extend(parca)

            if len(parca) < sayfa_boyu:
                break

            bas += sayfa_boyu

        return tum_veri

    except Exception as e:
        st.error(f"Manuel portföyler yüklenemedi: {e}")
        return []


@st.cache_data(ttl=60)
def portfoyleri_kullaniciya_gore_sinifla(user_id, user_name, user_email=""):
    """
    4'lü sınıflandırma:

    1. İlandaki Portföylerim
       Revy aktif veri + kullanıcıya ait kayıtlar

    2. Kapalı Portföylerim
       Manuel/gizli/kapalı veri + kullanıcıya ait kayıtlar

    3. Zeta Portföyleri
       Revy aktif veri + kullanıcıya ait olmayan Zeta portföyleri

    4. Köprü Portföylerim
       Sadece manuel girilen köprü portföyler
    """
    revy_aktifler = revy_aktif_portfoyleri_cek()
    manuel_kayitlar = manuel_kayitlari_cek()

    gruplar = {
        "ilandaki": [],
        "kapali": [],
        "zeta": [],
        "kopru": [],
    }

    goruldu = set()

    # 1. Revy aktif ilanları
    for v in revy_aktifler:
        kid = str(v.get("id", "") or "")

        if kid and kid in goruldu:
            continue

        bana_ait = kayit_kullaniciya_ait_mi(v, user_id, user_name, user_email)

        if bana_ait:
            gruplar["ilandaki"].append(v)
        else:
            gruplar["zeta"].append(v)

        if kid:
            goruldu.add(kid)

    # 2. Manuel kayıtlar
    for v in manuel_kayitlar:
        kid = str(v.get("id", "") or "")

        if kid and kid in goruldu:
            continue

        kaynak = (v.get("kaynak", "") or "").lower().strip()

        # Revy aktif kayıtları yukarıda işlendi
        if kaynak in REVVY_AKTIF_KAYNAKLAR and bool_deger(v.get("aktif", False)):
            continue

        bana_ait = kayit_kullaniciya_ait_mi(v, user_id, user_name, user_email)
        benim_girdigim = kayit_kullanici_tarafindan_girilmis_mi(v, user_id, user_name, user_email)

        if kayit_kapali_mi(v) and bana_ait:
            gruplar["kapali"].append(v)
            if kid:
                goruldu.add(kid)
            continue

        if kayit_manuel_kopru_mu(v) and benim_girdigim:
            gruplar["kopru"].append(v)
            if kid:
                goruldu.add(kid)
            continue

        # Eski veri uyumluluğu:
        # dis_kaynak + kullanıcı girmiş + portföy sahibi kullanıcı değilse köprü
        if kaynak == "dis_kaynak" and benim_girdigim and not bana_ait:
            gruplar["kopru"].append(v)
            if kid:
                goruldu.add(kid)
            continue

    return gruplar


@st.cache_data(ttl=60)
def favori_portfoyler():
    try:
        r = (
            get_client()
            .table("portfoyler")
            .select("*")
            .eq("favori", True)
            .order("olusturma_tarihi", desc=True)
            .limit(200)
            .execute()
        )
        return r.data or []
    except:
        return []


@st.cache_data(ttl=60)
def gd_listesi_zeta():
    try:
        z1 = sorted(set(
            v.get("talep_eden_danisan", "")
            for v in (
                get_client()
                .table("portfoyler")
                .select("talep_eden_danisan")
                .in_("kaynak", ["zeta1"])
                .execute()
                .data or []
            )
            if v.get("talep_eden_danisan", "")
        ))

        z2 = sorted(set(
            v.get("talep_eden_danisan", "")
            for v in (
                get_client()
                .table("portfoyler")
                .select("talep_eden_danisan")
                .in_("kaynak", ["zeta2"])
                .execute()
                .data or []
            )
            if v.get("talep_eden_danisan", "")
        ))

        return z1, z2, sorted(set(z1 + z2))

    except:
        return [], [], []


@st.cache_data(ttl=60)
def tum_musteri_map():
    """
    Teknik tablo adı 'musteriler'.
    Bu sayfada UI anlamı: Mülk Sahibi.
    """
    try:
        r = get_client().table("musteriler").select(
            "portfoy_id,musteri_adi,musteri_soyadi"
        ).execute()

        result = {}

        for row in (r.data or []):
            pid = str(row.get("portfoy_id", "") or "")
            ad = " ".join(filter(None, [
                row.get("musteri_adi", ""),
                row.get("musteri_soyadi", ""),
            ])).strip()

            if pid and ad:
                result[pid] = ad

        return result

    except:
        return {}


@st.cache_data(ttl=60)
def musteri_listesi_cek(portfoy_id_str):
    try:
        r = (
            get_client()
            .table("musteriler")
            .select("*")
            .eq("portfoy_id", portfoy_id_str)
            .execute()
        )
        return r.data or []
    except:
        return []


# ─────────────────────────────────────────────────────────────────────────────
# SESSION
# ─────────────────────────────────────────────────────────────────────────────
_k = st.session_state.get("kullanici", {}) or {}

user_id = _k.get("id", "")
user_name = (
    _k.get("ad_soyad")
    or _k.get("ad")
    or st.session_state.get("user_name", "")
    or ""
)
user_email = _k.get("email", "")

ilce_sec = ilce_listesi_cek()
gd_list_z1, gd_list_z2, gd_list_tum = gd_listesi_zeta()

# Oturumdaki kullanıcının adı listede HER ZAMAN bulunsun — eskiden liste sadece
# "kaynak=zeta1/zeta2" etiketli VAR OLAN portföy kayıtlarından türetiliyordu,
# yani daha önce hiç bu etiketle kayıt girmemiş bir GD listede hiç görünmüyordu.
if user_name:
    gd_list_z1 = sorted(set(gd_list_z1) | {user_name})
    gd_list_z2 = sorted(set(gd_list_z2) | {user_name})
    gd_list_tum = sorted(set(gd_list_tum) | {user_name})

musteri_map = tum_musteri_map()


# ─────────────────────────────────────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────────────────────────────────────
st.markdown(
    """
<style>
.pm-sec{
    font-size:10px;
    font-weight:800;
    color:#64748b;
    text-transform:uppercase;
    letter-spacing:.09em;
    margin:18px 0 6px;
    border-bottom:0.5px solid #e2e8f0;
    padding-bottom:6px;
}

.pm-sec-caption{
    font-size:11px;
    color:#94a3b8;
    margin:0 0 10px 0;
}

.pm-lbl{
    font-size:9px;
    font-weight:700;
    color:#94a3b8;
    text-transform:uppercase;
    letter-spacing:.07em;
    margin:14px 0 3px;
}

.pm-val{
    font-size:13px;
    color:#1e293b;
    font-weight:500;
    margin-bottom:6px;
}

.portfoy-row{
    background:#fff;
    border:1px solid #edf2f7;
    border-radius:16px;
    padding:12px 14px;
    box-shadow:0 2px 10px rgba(15,23,42,.035);
    margin-bottom:10px;
}

.pm-detail-box{
    background:#fbfdff;
    border:1px solid #dbe3ef;
    border-radius:14px;
    padding:14px 16px;
    margin:6px 0 16px 44px;
    box-shadow:0 4px 14px rgba(15,23,42,.04);
}

.pm-meta{
    font-size:12px;
    color:#64748b;
    line-height:1.5;
}

.pm-owner{
    font-size:12px;
    color:#475569;
    line-height:1.55;
}

.pm-badge{
    display:inline-block;
    padding:3px 8px;
    border-radius:999px;
    font-size:11px;
    font-weight:700;
}

.pm-chip{
    display:inline-flex;
    align-items:center;
    gap:4px;
    padding:3px 8px;
    border-radius:999px;
    font-size:10.5px;
    font-weight:700;
    background:#f8fafc;
    color:#64748b;
    border:1px solid #e2e8f0;
}

.pm-thumb-box{
    position:relative;
    width:132px;
    height:88px;
    overflow:hidden;
    border-radius:12px;
    border:1px solid #e2e8f0;
    background:#f8fafc;
}

.pm-thumb-img{
    width:100%;
    height:100%;
    object-fit:cover;
    display:block;
}

.pm-thumb-more{
    position:absolute;
    right:8px;
    bottom:8px;
    background:rgba(15,23,42,.72);
    color:#fff;
    padding:4px 8px;
    border-radius:999px;
    font-size:11px;
    font-weight:800;
}

.pm-placeholder{
    width:132px;
    height:88px;
    border-radius:12px;
    border:1px dashed #dbe3ef;
    background:#f8fafc;
    display:flex;
    align-items:center;
    justify-content:center;
    font-size:11px;
    color:#94a3b8;
}

.pm-small-note{
    background:#f8fafc;
    border:1px solid #e8eef6;
    border-radius:12px;
    padding:10px 12px;
    font-size:12px;
    color:#64748b;
    margin-top:8px;
}

.pm-circle{
    width:34px;
    height:34px;
    border-radius:50%;
    background:#e9f0fb;
    color:#355C7D;
    display:flex;
    align-items:center;
    justify-content:center;
    font-size:14px;
    font-weight:800;
    margin-top:6px;
}

.pm-empty{
    background:#fbfdff;
    border:1px dashed #dbe3ef;
    border-radius:12px;
    padding:14px;
    font-size:12px;
    color:#94a3b8;
    margin-bottom:10px;
}
</style>
""",
    unsafe_allow_html=True,
)


# ─────────────────────────────────────────────────────────────────────────────
# UI HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def render_thumb_html(urls):
    if not urls:
        st.markdown('<div class="pm-placeholder">Fotoğraf yok</div>', unsafe_allow_html=True)
        return

    url = urls[0]
    extra = len(urls) - 1
    extra_html = f'<div class="pm-thumb-more">+{extra}</div>' if extra > 0 else ""

    st.markdown(
        f"""
        <a href="{h(url)}" target="_blank" style="text-decoration:none;">
            <div class="pm-thumb-box">
                <img src="{h(url)}" class="pm-thumb-img"/>
                {extra_html}
            </div>
        </a>
        """,
        unsafe_allow_html=True,
    )


def render_badge(index_no):
    st.markdown(
        f'<div class="pm-circle">{index_no}</div>',
        unsafe_allow_html=True,
    )


def render_kayit_tipi_chip(grup):
    if grup == "kapali":
        return '<span class="pm-chip">🔒 Kapalı</span>'

    if grup == "kopru":
        return '<span class="pm-chip">🌉 Köprü</span>'

    if grup == "ilandaki":
        return '<span class="pm-chip">🏠 İlanda</span>'

    if grup == "zeta":
        return '<span class="pm-chip">🏛 Zeta</span>'

    if grup == "takip":
        return '<span class="pm-chip">⭐ Takip</span>'

    return ""


def sinif_label_bul(sel):
    if kayit_kapali_mi(sel):
        return "🔒 Kapalı Portföy"

    if kayit_manuel_kopru_mu(sel):
        return "🌉 Köprü Portföy"

    if kayit_kullaniciya_ait_mi(sel, user_id, user_name, user_email):
        return "🏠 İlandaki Portföy"

    return "🏛 Zeta Portföyü"


@st.fragment
def render_portfoy_detay_panel(sel):
    kid = sel.get("id")

    ozet = sel.get("ozet") or sel.get("mail_konusu") or "—"
    islem = sel.get("islem_tipi", "") or "—"
    mulk = sel.get("mulk_tipi", "") or sel.get("mulk_turu", "") or "—"
    il = sel.get("il", "") or "—"
    ilce = ilce_grubu(sel)
    bolge = sel.get("bolge_mahalle", "") or sel.get("mahalle", "") or "—"
    oda = sel.get("oda_sayisi_m2", "") or "—"
    fiyat = sel.get("fiyat", "") or "—"
    ozellik = sel.get("ozellikler", "") or sel.get("ozel_kriterler", "") or "—"
    link = sel.get("ilan_linki", "") or ""
    not_a = sel.get("not_alani", "") or ""
    gd_isim = portfoy_sahibi_adi(sel)
    favori = bool_deger(sel.get("favori", False))
    foto_urls = foto_url_listesi(sel)
    sinif_label = sinif_label_bul(sel)

    tip_bg, tip_fg, tip_lbl = tip_badge(islem)

    st.markdown('<div class="pm-detail-box">', unsafe_allow_html=True)

    st.markdown(
        f"""
        <div style="font-size:16px;font-weight:800;color:#172B4D;line-height:1.4;margin-bottom:8px;">
            {h(ozet)}
            <span style="background:{tip_bg};color:{tip_fg};padding:3px 9px;border-radius:999px;font-size:11px;font-weight:700;">
                {h(tip_lbl)}
            </span>
            <span style="background:#f8fafc;color:#64748b;border:1px solid #e2e8f0;padding:3px 9px;border-radius:999px;font-size:11px;font-weight:700;">
                {h(sinif_label)}
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # MÜLK SAHİBİ
    st.markdown('<p class="pm-lbl">👤 Mülk Sahibi</p>', unsafe_allow_html=True)

    musteriler = musteri_listesi_cek(str(kid))

    if musteriler:
        for m in musteriler:
            ad = " ".join(filter(None, [
                m.get("musteri_adi", ""),
                m.get("musteri_soyadi", ""),
            ])).strip() or "—"

            tel = m.get("telefon", "") or "—"
            initials = "".join(w[0].upper() for w in ad.split()[:2]) if ad != "—" else "?"

            st.markdown(
                f"""
                <div style="display:inline-flex;align-items:center;gap:10px;padding:7px 12px;
                background:#EEF4FA;border-radius:8px;border:0.5px solid #c7d9ed;margin-bottom:5px;">
                    <div style="width:30px;height:30px;border-radius:50%;background:#355C7D;
                    display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:700;color:#fff;">
                        {h(initials)}
                    </div>
                    <div>
                        <div style="font-size:13px;font-weight:700;color:#172B4D;">{h(ad)}</div>
                        <div style="font-size:11px;color:#64748b;">{h(tel)}</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    else:
        st.caption("Mülk sahibi bilgisi eklenmemiş.")

    musteri_form_key = f"pm_mf_{kid}"

    if st.session_state.get(musteri_form_key, False):
        mc1, mc2, mc3, mc4 = st.columns([2, 2, 2, 1])

        with mc1:
            y_ad = st.text_input("Adı", placeholder="Ad", key=f"pm_mad_{kid}")

        with mc2:
            y_soyad = st.text_input("Soyadı", placeholder="Soyad", key=f"pm_msoyad_{kid}")

        with mc3:
            y_tel = st.text_input("Telefon", placeholder="05xx", key=f"pm_mtel_{kid}")

        with mc4:
            st.markdown("<div style='height:27px'></div>", unsafe_allow_html=True)

            if st.button("💾", key=f"pm_mkyd_{kid}", use_container_width=True):
                if y_ad.strip():
                    try:
                        get_client().table("musteriler").insert({
                            "portfoy_id": str(kid),
                            "musteri_adi": y_ad.strip(),
                            "musteri_soyadi": y_soyad.strip(),
                            "telefon": y_tel.strip(),
                            "ekleyen": user_name,
                            "danisan_id": user_name,
                        }).execute()

                        st.cache_data.clear()
                        st.session_state[musteri_form_key] = False
                        st.success("Mülk sahibi eklendi.")
                        st.rerun(scope="app")

                    except Exception as e:
                        st.error(f"Hata: {e}")

                else:
                    st.warning("Ad girin.")

        if st.button("İptal", key=f"pm_miptl_{kid}"):
            st.session_state[musteri_form_key] = False
            st.rerun(scope="app")

    else:
        if st.button("+ Mülk Sahibi Ekle", key=f"pm_mekle_{kid}"):
            st.session_state[musteri_form_key] = True
            st.rerun(scope="app")

    # FOTOĞRAFLAR
    st.markdown('<hr style="border:none;border-top:0.5px solid #e2e8f0;margin:10px 0;">', unsafe_allow_html=True)
    st.markdown('<p class="pm-lbl">📷 Fotoğraflar</p>', unsafe_allow_html=True)

    if foto_urls:
        foto_cols = st.columns(min(len(foto_urls), 4))

        for i, url in enumerate(foto_urls[:4]):
            with foto_cols[i]:
                st.markdown(
                    f"""
                    <a href="{h(url)}" target="_blank" style="text-decoration:none;">
                        <img src="{h(url)}" style="
                            width:100%;
                            height:120px;
                            object-fit:cover;
                            border-radius:10px;
                            border:1px solid #dbe3ef;
                            display:block;
                        ">
                    </a>
                    """,
                    unsafe_allow_html=True,
                )

                if st.button("🗑 Kaldır", key=f"pm_foto_sil_{kid}_{i}", use_container_width=True):
                    yeni_liste = [u for j, u in enumerate(foto_urls) if j != i]

                    try:
                        get_client().table("portfoyler").update({
                            "foto_url": ",".join(yeni_liste)
                        }).eq("id", kid).execute()

                        st.cache_data.clear()
                        st.success("Fotoğraf kaldırıldı.")
                        st.rerun(scope="app")

                    except Exception as e:
                        st.error(f"Hata: {e}")

        st.caption("Fotoğraflar tıklanabilir yapıdadır.")
    else:
        st.caption("Henüz fotoğraf yok.")

    _foto_ac_key = f"pm_foto_ekle_acik_{kid}"
    if st.button("＋ Fotoğraf Ekle", key=f"pm_foto_ekle_btn_{kid}", use_container_width=True):
        st.session_state[_foto_ac_key] = not st.session_state.get(_foto_ac_key, False)

    if st.session_state.get(_foto_ac_key, False):
        yeni_fotolar = st.file_uploader(
            "Fotoğraf yükle",
            type=["jpg", "jpeg", "png", "webp"],
            accept_multiple_files=True,
            key=f"pm_foto_ekle_{kid}",
        )

        if yeni_fotolar and st.button("💾 Fotoğrafları Kaydet", key=f"pm_foto_kyd_{kid}", type="primary"):
            with st.spinner("Yükleniyor..."):
                yeni_urls, foto_hatalar = foto_yukle(kid, yeni_fotolar)

            if foto_hatalar:
                for _h in foto_hatalar:
                    st.error(f"Yükleme hatası — {_h}")

            if yeni_urls:
                tum_urls = foto_urls + yeni_urls

                try:
                    get_client().table("portfoyler").update({
                        "foto_url": ",".join(tum_urls)
                    }).eq("id", kid).execute()

                    st.cache_data.clear()
                    st.success(f"{len(yeni_urls)} fotoğraf eklendi.")
                    st.rerun(scope="app")

                except Exception as e:
                    st.error(f"Kayıt hatası: {e}")
            elif not foto_hatalar:
                st.warning("Fotoğraf yüklenemedi.")

    # BİLGİ GRID
    st.markdown('<hr style="border:none;border-top:0.5px solid #e2e8f0;margin:10px 0;">', unsafe_allow_html=True)

    d1, d2, d3 = st.columns(3)

    with d1:
        st.markdown(f'<p class="pm-lbl">Mülk Tipi</p><p class="pm-val">{h(mulk)}</p>', unsafe_allow_html=True)
        st.markdown(f'<p class="pm-lbl">İl / İlçe</p><p class="pm-val">{h(il)} / {h(ilce)}</p>', unsafe_allow_html=True)
        st.markdown(f'<p class="pm-lbl">Bölge / Mahalle</p><p class="pm-val">{h(bolge)}</p>', unsafe_allow_html=True)

    with d2:
        st.markdown(f'<p class="pm-lbl">Oda / m²</p><p class="pm-val">{h(oda)}</p>', unsafe_allow_html=True)
        st.markdown(
            f'<p class="pm-lbl">Fiyat</p><p class="pm-val" style="font-size:15px;font-weight:800;color:#172B4D;">{h(fiyat)}</p>',
            unsafe_allow_html=True,
        )
        st.markdown(f'<p class="pm-lbl">Portföy Sahibi</p><p class="pm-val">{h(gd_isim)}</p>', unsafe_allow_html=True)

    with d3:
        st.markdown(f'<p class="pm-lbl">Portföy Sınıfı</p><p class="pm-val">{h(sinif_label)}</p>', unsafe_allow_html=True)
        st.markdown(f'<p class="pm-lbl">Tarih</p><p class="pm-val">{h(tarih_str(sel))}</p>', unsafe_allow_html=True)

        if link and link != "—":
            st.markdown(
                f'<p class="pm-lbl">İlan</p><a href="{h(link)}" target="_blank" style="font-size:12px;color:#355C7D;">🔗 İlan Linki</a>',
                unsafe_allow_html=True,
            )

    if ozellik and ozellik != "—":
        st.markdown(f'<p class="pm-lbl">Özellikler</p><p class="pm-val">{h(ozellik)}</p>', unsafe_allow_html=True)

    # DÜZENLE
    _duzenle_ac_key = f"pm_duzenle_acik_{kid}"
    if st.button("✏️ Portföy Bilgilerini Düzenle", key=f"pm_duzenle_btn_{kid}", use_container_width=True):
        st.session_state[_duzenle_ac_key] = not st.session_state.get(_duzenle_ac_key, False)

    if st.session_state.get(_duzenle_ac_key, False):
        e1, e2, e3 = st.columns(3)

        with e1:
            yeni_ozet = st.text_input("Başlık", value=str(ozet if ozet != "—" else ""), key=f"edit_ozet_{kid}")
            yeni_il = st.text_input("İl", value=str(il if il != "—" else ""), key=f"edit_il_{kid}")
            yeni_ilce = st.text_input("İlçe", value=str(ilce if ilce != "—" else ""), key=f"edit_ilce_{kid}")

        with e2:
            yeni_mahalle = st.text_input("Mahalle / Bölge", value=str(bolge if bolge != "—" else ""), key=f"edit_mahalle_{kid}")
            yeni_mulk = st.selectbox(
                "Mülk Tipi",
                ["Konut", "İşyeri", "Arsa", "Belirsiz"],
                index=["Konut", "İşyeri", "Arsa", "Belirsiz"].index(mulk) if mulk in ["Konut", "İşyeri", "Arsa", "Belirsiz"] else 3,
                key=f"edit_mulk_{kid}",
            )
            yeni_islem = st.selectbox(
                "İşlem Tipi",
                ["Satılık", "Kiralık", "Belirsiz"],
                index=["Satılık", "Kiralık", "Belirsiz"].index(islem) if islem in ["Satılık", "Kiralık", "Belirsiz"] else 2,
                key=f"edit_islem_{kid}",
            )

        with e3:
            yeni_oda = st.text_input("Oda / M²", value=str(oda if oda != "—" else ""), key=f"edit_oda_{kid}")
            yeni_fiyat = st.text_input("Fiyat", value=str(fiyat if fiyat != "—" else ""), key=f"edit_fiyat_{kid}")
            yeni_link = st.text_input("İlan Linki", value=str(link or ""), key=f"edit_link_{kid}")

        yeni_ozel = st.text_area(
            "Özellikler / Notlar",
            value=str(ozellik if ozellik != "—" else ""),
            height=70,
            key=f"edit_ozel_{kid}",
        )

        if st.button("💾 Bilgileri Güncelle", key=f"edit_save_{kid}", type="primary"):
            data = {
                "ozet": yeni_ozet,
                "il": yeni_il,
                "ilce": yeni_ilce,
                "mahalle": yeni_mahalle,
                "mulk_tipi": yeni_mulk,
                "islem_tipi": yeni_islem,
                "oda_sayisi_m2": yeni_oda,
                "fiyat": yeni_fiyat,
                "ilan_linki": yeni_link,
                "ozel_kriterler": yeni_ozel,
            }
            kayit_guncelle(kid, data)

    # NOT
    st.markdown('<hr style="border:none;border-top:0.5px solid #e2e8f0;margin:10px 0;">', unsafe_allow_html=True)

    yeni_not = st.text_area(
        "📝 Notum",
        value=not_a,
        key=f"pnot_{kid}",
        height=80,
        placeholder="Bu portföy hakkında notlarınız...",
    )

    if st.button("💾 Notu Kaydet", key=f"pnot_kyd_{kid}"):
        try:
            get_client().table("portfoyler").update({
                "not_alani": yeni_not
            }).eq("id", kid).execute()

            st.cache_data.clear()
            st.success("Not kaydedildi.")

        except Exception as e:
            st.error(f"Hata: {e}")

    # PAYLAŞ
    st.markdown('<hr style="border:none;border-top:0.5px solid #e2e8f0;margin:10px 0;">', unsafe_allow_html=True)
    st.markdown('<p class="pm-lbl">Paylaş</p>', unsafe_allow_html=True)

    _fiyat_etiket = (
        "Kira Bedeli" if "kira" in islem.lower()
        else "Satış Fiyatı" if "sat" in islem.lower()
        else "Fiyat"
    )
    _ara_metin = (
        f"{ilce}'da yer alan bu {islem.lower()} {mulk.lower()} ile ilgili "
        f"temel bilgiler aşağıdadır."
    )
    render_mail_paylas_widget(
        key_prefix=f"pm_paylas_{kid}",
        gd_isim=gd_isim.split(" · ")[0].strip() if gd_isim and gd_isim != "—" else gd_isim,
        konu_ozet=ozet[:60],
        buton_etiketi="📧 Startkey'e Paylaş",
        baslik=ozet,
        ara_metin=_ara_metin,
        rozetler=[ilce, mulk, islem],
        bilgi_satirlari=[
            ("Lokasyon", f"{il} / {ilce}" + (f" / {bolge}" if bolge and bolge != "—" else "")),
            ("Kategori", mulk),
            ("İşlem Tipi", islem),
            ("Oda / M²", oda),
            (_fiyat_etiket, fiyat),
            ("Özellikler", ozellik),
        ],
        ilan_linki=link if link and link != "—" else None,
        gorsel_urls=foto_urls if foto_urls else None,
    )

    ab1, ab2 = st.columns(2)

    with ab1:
        if st.button("★ Favori" if favori else "☆ Favoriye Al", key=f"dp_fav_inline_{kid}", use_container_width=True):
            favori_guncelle(kid, favori)

    with ab2:
        if st.button("✖ Detayı Kapat", key=f"dp_kapat_inline_{kid}", use_container_width=True):
            st.session_state.pop("pm_selected_id", None)
            st.session_state["pm_aktif_sekme"] = "bos"
            st.rerun(scope="app")

    st.markdown("</div>", unsafe_allow_html=True)


def render_portfoy_row(v, row_no, prefix, musteri_map_ref, grup):
    kid = str(v.get("id", "") or "")
    secili = str(st.session_state.get("pm_selected_id") or "") == kid

    ozet = v.get("ozet") or v.get("mail_konusu") or "Portföy"
    lokasyon = lokasyon_text(v)

    islem = v.get("islem_tipi", "") or "—"
    mulk = v.get("mulk_tipi", "") or v.get("mulk_turu", "") or "—"
    oda = v.get("oda_sayisi_m2", "") or "—"
    fiyat = v.get("fiyat", "") or "—"

    favori = bool_deger(v.get("favori", False))

    tip_bg, tip_fg, tip_lbl = tip_badge(islem)

    mulk_sahibi = mulk_sahibi_adi(musteri_map_ref, kid) or "—"
    portfoy_sahibi = portfoy_sahibi_adi(v)
    foto_urls = foto_url_listesi(v)
    chip_html = render_kayit_tipi_chip(grup)

    with st.container():
        st.markdown('<div class="portfoy-row">', unsafe_allow_html=True)

        c1, c2, c3, c4, c5 = st.columns([0.55, 5.8, 1.6, 0.7, 1.0])

        with c1:
            render_badge(row_no)

        with c2:
            if st.button(
                str(ozet),
                key=f"{prefix}_sel_{kid}",
                use_container_width=True,
                type="primary" if secili else "secondary",
            ):
                st.session_state["pm_selected_id"] = int(kid) if kid.isdigit() else kid
                st.session_state["pm_aktif_sekme"] = "detay"
                st.rerun()

            st.markdown(
                f"""
                <div class="pm-meta" style="margin-top:4px;">
                    📍 {h(lokasyon or '—')}
                    &nbsp;&nbsp;·&nbsp;&nbsp;
                    <span class="pm-badge" style="background:{tip_bg};color:{tip_fg};">{h(tip_lbl)}</span>
                    &nbsp;&nbsp;·&nbsp;&nbsp;
                    {h(mulk)}
                    &nbsp;&nbsp;·&nbsp;&nbsp;
                    {h(oda)}
                    &nbsp;&nbsp;·&nbsp;&nbsp;
                    <span style="font-weight:800;color:#2F6FED;">{h(fiyat)}</span>
                    &nbsp;&nbsp;
                    {chip_html}
                </div>

                <div class="pm-owner" style="margin-top:6px;">
                    👤 <strong>Mülk Sahibi:</strong> {h(mulk_sahibi)}
                </div>

                <div class="pm-owner">
                    🏠 <strong>Portföy Sahibi:</strong> {h(portfoy_sahibi)}
                </div>
                """,
                unsafe_allow_html=True,
            )

        with c3:
            render_thumb_html(foto_urls)

        with c4:
            if st.button("★" if favori else "☆", key=f"{prefix}_fav_{kid}", use_container_width=True):
                favori_guncelle(int(kid) if kid.isdigit() else kid, favori)

        with c5:
            st.caption(tarih_saat_str(v))

        st.markdown("</div>", unsafe_allow_html=True)

        if secili and st.session_state.get("pm_aktif_sekme") == "detay":
            render_portfoy_detay_panel(v)


def render_portfoy_section(title, caption, liste, prefix, grup):
    st.markdown(f'<div class="pm-sec">{title}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="pm-sec-caption">{caption}</div>', unsafe_allow_html=True)

    if not liste:
        st.markdown(
            '<div class="pm-empty">Bu bölümde görüntülenecek portföy bulunmuyor.</div>',
            unsafe_allow_html=True,
        )
        return

    for i, v in enumerate(liste, start=1):
        render_portfoy_row(v, i, prefix, musteri_map, grup)


# ─────────────────────────────────────────────────────────────────────────────
# BAŞLIK
# ─────────────────────────────────────────────────────────────────────────────
hc1, hc2 = st.columns([1, 0.1])

with hc1:
    render_page_header(
        "🏠 Portföylerim",
        f"Kullanıcı bazlı portföy çalışma paneli · {user_name}",
    )

with hc2:
    if st.button("↺", key="pm_yenile", help="Yenile"):
        st.cache_data.clear()
        st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# VERİ
# ─────────────────────────────────────────────────────────────────────────────
gruplar = portfoyleri_kullaniciya_gore_sinifla(user_id, user_name, user_email)

ilandaki_portfoyler = gruplar["ilandaki"]
kapali_portfoyler = gruplar["kapali"]
zeta_portfoyleri = gruplar["zeta"]
kopru_portfoyler = gruplar["kopru"]

fav_portfoyler = favori_portfoyler()
takip_sess = st.session_state.get("takip_listesi", {})
fav_idler = {str(v.get("id", "")) for v in fav_portfoyler}

takip_kayitlar = list(fav_portfoyler)

for k, v in takip_sess.items():
    if str(k) not in fav_idler and "portfoy" in v.get("_takip_kaynak", ""):
        takip_kayitlar.append(v)

aktif_sekme = st.session_state.get("pm_aktif_sekme", "bos")
selected_id = st.session_state.get("pm_selected_id")


# ─────────────────────────────────────────────────────────────────────────────
# ÜST ÖZET
# ─────────────────────────────────────────────────────────────────────────────
m1, m2, m3, m4, m5 = st.columns(5)

with m1:
    st.metric("İlandaki", len(ilandaki_portfoyler))

with m2:
    st.metric("Kapalı", len(kapali_portfoyler))

with m3:
    st.metric("Zeta", len(zeta_portfoyleri))

with m4:
    st.metric("Köprü", len(kopru_portfoyler))

with m5:
    st.metric("Takip", len(takip_kayitlar))


# ─────────────────────────────────────────────────────────────────────────────
# LİSTE BÖLÜMLERİ
# ─────────────────────────────────────────────────────────────────────────────
if takip_kayitlar:
    render_portfoy_section(
        "⭐ Takip Listem",
        "Favoriye aldığınız veya çalışma listenize eklediğiniz portföyler.",
        takip_kayitlar,
        "ptk",
        "takip",
    )

render_portfoy_section(
    "🏠 İlandaki Portföylerim",
    "Revy aktif ilan verisinden gelen, Startkey / Zeta sisteminde halen yayında olan size ait portföyler.",
    ilandaki_portfoyler,
    "ilan",
    "ilandaki",
)

render_portfoy_section(
    "🔒 Kapalı Portföylerim",
    "İlanda olmayan, size ait özel veya kapalı portföyler. Bu bölüm manuel / gizli kayıtlardan gelir.",
    kapali_portfoyler,
    "kapali",
    "kapali",
)

_zeta_ac_key = "pm_zeta_portfoyleri_acik"
if st.button(
    f"🏛 Zeta Portföyleri ({len(zeta_portfoyleri)})",
    key="pm_zeta_toggle_btn", use_container_width=True,
):
    st.session_state[_zeta_ac_key] = not st.session_state.get(_zeta_ac_key, False)

if st.session_state.get(_zeta_ac_key, False):
    st.caption("Revy aktif ilan verisinden gelen diğer Zeta danışman portföyleri. İhtiyaç halinde açıp inceleyebilirsiniz.")

    if not zeta_portfoyleri:
        st.markdown(
            '<div class="pm-empty">Zeta portföyü bulunmuyor.</div>',
            unsafe_allow_html=True,
        )
    else:
        for i, v in enumerate(zeta_portfoyleri, start=1):
            render_portfoy_row(v, i, "zeta", musteri_map, "zeta")

render_portfoy_section(
    "🌉 Köprü Portföylerim",
    "Sizin manuel girdiğiniz köprü portföyleri.",
    kopru_portfoyler,
    "kopru",
    "kopru",
)

st.markdown('<div style="height:8px;"></div>', unsafe_allow_html=True)

btn1, btn2 = st.columns([0.25, 0.75])

with btn1:
    if st.button("＋ Yeni Portföy Ekle", key="btn_yeni_portfoy", type="primary", use_container_width=True):
        st.session_state["pm_aktif_sekme"] = "yeni_portfoy"
        st.session_state.pop("pm_selected_id", None)
        st.rerun()

st.markdown(
    '<div class="pm-small-note">ℹ️ Fotoğraflar tıklanabilir yapıdadır. Büyük görüntü için fotoğrafa tıklayın.</div>',
    unsafe_allow_html=True,
)

st.markdown("---")


# ─────────────────────────────────────────────────────────────────────────────
# ALT: YENİ PORTFÖY FORMU
# ─────────────────────────────────────────────────────────────────────────────
if aktif_sekme == "yeni_portfoy":
    parse_sonuc = st.session_state.get("pm_parse_sonuc", {})

    st.markdown("### ＋ Yeni Portföy Ekle")

    gc1, gc2, gc3, gc4 = st.columns(4)

    with gc1:
        st.caption("Portföy Tipi")
        yeni_portfoy_tipi = st.selectbox(
            "Portföy tipi",
            ["Kapalı Portföy", "Köprü Portföy"],
            key="pm_yeni_portfoy_tipi",
            help="İlandaki portföyler Revy aktif verisinden gelir. Manuel girişte kapalı veya köprü portföy eklenir.",
        )

    with gc2:
        st.caption("Ofis")
        zeta_ofis = st.selectbox(
            "Ofis",
            ["Seç...", "ZETA 1", "ZETA 2", "Diğer Ofis"],
            key="pm_ofis",
        )

    with gc3:
        if zeta_ofis in ("ZETA 1", "ZETA 2", "Seç..."):
            st.caption("Portföyü Paylaşan GD")
            gd_kaynak = (
                gd_list_z1 if zeta_ofis == "ZETA 1"
                else gd_list_z2 if zeta_ofis == "ZETA 2"
                else gd_list_tum
            )

            gd_sec_secenekleri = ["Seç..."] + gd_kaynak + ["Diğer (manuel gir)"]
            # Varsayılan seçim: oturumdaki kullanıcı (listede her zaman var artık) —
            # böylece kendi sayfandayken adın otomatik gelir, istersen değiştirirsin.
            _varsayilan_idx = (
                gd_sec_secenekleri.index(user_name) if user_name in gd_sec_secenekleri else 0
            )
            gd_sec = st.selectbox(
                "Danışman seçin",
                gd_sec_secenekleri,
                index=_varsayilan_idx,
                key="pm_gd_sec",
            )

            gd_sec_val = gd_sec

            if yeni_portfoy_tipi == "Kapalı Portföy":
                if gd_sec_val in ("Seç...", "Diğer (manuel gir)"):
                    gd_ad = user_name
                else:
                    gd_ad = gd_sec_val
            else:
                if gd_sec_val == "Seç...":
                    gd_ad = ""
                elif gd_sec_val == "Diğer (manuel gir)":
                    gd_ad = ""
                else:
                    gd_ad = gd_sec_val

            ofis_adi = ""

        else:
            st.caption("Ofis Adı")
            ofis_adi = st.text_input(
                "Ofis adı",
                placeholder="Örn: RE/MAX Bornova",
                key="pm_ofis_adi",
            )
            gd_sec_val = "Seç..."
            gd_ad = ""

    with gc4:
        if zeta_ofis == "Diğer Ofis":
            st.caption("Danışman Adı")
            gd_dis = st.text_input(
                "Danışman adı",
                placeholder="Ad Soyad",
                key="pm_gd_dis",
            )
            gd_ad = f"{gd_dis} - {ofis_adi}".strip(" -") if (gd_dis or ofis_adi) else ""

        elif gd_sec_val == "Diğer (manuel gir)":
            varsayilan = user_name if yeni_portfoy_tipi == "Kapalı Portföy" else ""
            gd_ad = st.text_input(
                "Danışman adı",
                value=varsayilan,
                placeholder="Portföy sahibi danışman",
                key="pm_gd_manuel",
            )
        else:
            st.empty()

    if yeni_portfoy_tipi == "Kapalı Portföy" and not gd_ad:
        gd_ad = user_name

    if yeni_portfoy_tipi == "Köprü Portföy":
        kaynak = "manuel_kopru"
        kapali_flag = False
    else:
        kaynak = "ofis_gizli"
        kapali_flag = True

    st.markdown("---")
    st.markdown(
        '<p style="font-size:12px;font-weight:600;color:#355C7D;">👤 Mülk Sahibi Bilgisi <span style="font-weight:400;color:#94a3b8;">(isteğe bağlı)</span></p>',
        unsafe_allow_html=True,
    )

    mk1, mk2, mk3 = st.columns(3)

    with mk1:
        pm_musteri_adi = st.text_input("Adı", placeholder="Ad", key="pm_musteri_adi")

    with mk2:
        pm_musteri_soyadi = st.text_input("Soyadı", placeholder="Soyad", key="pm_musteri_soyadi")

    with mk3:
        pm_musteri_tel = st.text_input("Telefon", placeholder="05xx xxx xx xx", key="pm_musteri_tel")

    st.markdown("---")

    yontem = st.radio(
        "Portföy bilgileri",
        ["Metin Yaz → Sistem Doldursun", "Formu Kendim Doldurayım"],
        horizontal=True,
        key="pm_yontem",
    )

    if yontem == "Metin Yaz → Sistem Doldursun":
        metin = st.text_area(
            "Portföy açıklaması",
            placeholder="Örn: Bornova Erzene'de 3+1 satılık daire, 120 m², 4.5 milyon TL...",
            height=80,
            key="pm_metin",
        )

        if st.button("Metni Yorumla", key="pm_parse_btn", type="primary"):
            if metin.strip():
                with st.spinner("Analiz ediliyor..."):
                    sonuc = ai_parse_portfoy(metin)

                    if "_hata" not in sonuc:
                        lookup = mahalle_ile_ilce_bul(sonuc.get("mahalle", "") or metin)

                        if lookup:
                            sonuc["il"] = lookup.get("il", "")
                            sonuc["ilce"] = lookup.get("ilce", "")

                            if not sonuc.get("mahalle"):
                                sonuc["mahalle"] = lookup.get("mahalle", "")

                        st.session_state["pm_parse_sonuc"] = sonuc
                        parse_sonuc = sonuc
                        st.success("Dolduruldu — kontrol edin.")
                        st.rerun()

                    else:
                        st.error(f"Hata: {sonuc['_hata']}")

            else:
                st.warning("Açıklama yazın.")

        if parse_sonuc:
            st.caption("✅ Aşağıdaki alanları kontrol edip düzenleyebilirsiniz.")

    if yontem == "Formu Kendim Doldurayım" or parse_sonuc:
        f1, f2, f3 = st.columns(3)

        with f1:
            ozet = st.text_input(
                "Özet / Başlık",
                value=parse_sonuc.get("ozet", ""),
                key="pm_ozet",
            )

            il = st.selectbox(
                "İl",
                ILLER,
                index=ILLER.index(parse_sonuc.get("il", "İzmir"))
                if parse_sonuc.get("il", "") in ILLER else 0,
                key="pm_il",
            )

            ilce_opts = ["İzmir Genel"] + ilce_sec
            ilce_raw = parse_sonuc.get("ilce", "")

            ilce_sec2 = st.selectbox(
                "Birincil İlçe",
                ilce_opts,
                index=ilce_opts.index(ilce_raw) if ilce_raw in ilce_opts else 0,
                key="pm_ilce",
            )

            ilce_val = "" if ilce_sec2 == "İzmir Genel" else ilce_sec2

        with f2:
            mulk = st.selectbox(
                "Mülk Tipi",
                ["Konut", "İşyeri", "Arsa", "Belirsiz"],
                index=["Konut", "İşyeri", "Arsa", "Belirsiz"].index(parse_sonuc.get("mulk_tipi", "Belirsiz"))
                if parse_sonuc.get("mulk_tipi", "") in ["Konut", "İşyeri", "Arsa", "Belirsiz"] else 3,
                key="pm_mulk",
            )

            islem = st.selectbox(
                "İşlem Tipi",
                ["Satılık", "Kiralık", "Belirsiz"],
                index=["Satılık", "Kiralık", "Belirsiz"].index(parse_sonuc.get("islem_tipi", "Belirsiz"))
                if parse_sonuc.get("islem_tipi", "") in ["Satılık", "Kiralık", "Belirsiz"] else 2,
                key="pm_islem",
            )

            fiyat = st.text_input(
                "Fiyat",
                value=parse_sonuc.get("fiyat", ""),
                placeholder="Örn: 4.500.000 TL",
                key="pm_fiyat",
            )

        with f3:
            oda = st.text_input(
                "Oda / M²",
                value=parse_sonuc.get("oda_sayisi_m2", ""),
                placeholder="Örn: 3+1 / 120 m²",
                key="pm_oda",
            )

            mahalle = st.text_input(
                "Mahalle / Semt",
                value=parse_sonuc.get("mahalle", ""),
                key="pm_mahalle",
            )

            link = st.text_input(
                "İlan Linki",
                value=parse_sonuc.get("ilan_linki", ""),
                key="pm_link",
            )

        ilceler_default = [
            i for i in (parse_sonuc.get("ilceler") or [])
            if i in ilce_sec
        ]

        ilceler = st.multiselect(
            "Tüm İlçeler",
            ilce_sec,
            default=ilceler_default,
            key="pm_ilceler",
        )

        ozel = st.text_area(
            "Özellikler / Notlar",
            value=parse_sonuc.get("ozel_kriterler", ""),
            height=70,
            key="pm_ozel",
        )

        st.markdown("**Fotoğraflar** *(isteğe bağlı)*")

        yuklenen = st.file_uploader(
            "Fotoğraf yükle",
            type=["jpg", "jpeg", "png", "webp"],
            accept_multiple_files=True,
            key="pm_foto",
        )

        if yuklenen:
            import base64

            imgs_html = ""

            for dosya in yuklenen:
                b64 = base64.b64encode(dosya.read()).decode()
                dosya.seek(0)

                mime = "image/jpeg" if dosya.name.lower().endswith(("jpg", "jpeg")) else "image/png"

                imgs_html += (
                    f'<img src="data:{mime};base64,{b64}" '
                    f'style="width:110px;height:85px;object-fit:cover;'
                    f'border-radius:8px;margin:3px;border:1px solid #e5e7eb;" />'
                )

            st.markdown(
                f'<div style="display:flex;flex-wrap:wrap;gap:4px;">{imgs_html}</div>',
                unsafe_allow_html=True,
            )

        st.markdown("---")

        ka, kb = st.columns([1, 5])

        with ka:
            if st.button("💾 Kaydet", key="pm_kaydet", type="primary"):
                if yeni_portfoy_tipi == "Köprü Portföy" and not gd_ad:
                    st.warning("Köprü portföy için portföy sahibi danışman / ofis bilgisini girin.")
                else:
                    with st.spinner("Kaydediliyor..."):
                        import uuid as _uuid

                        storage_key = str(_uuid.uuid4())
                        foto_urls_list, foto_hatalar_yeni = foto_yukle(storage_key, yuklenen) if yuklenen else ([], [])
                        for _h in foto_hatalar_yeni:
                            st.error(f"Fotoğraf yükleme hatası — {_h}")

                        veri = {
                            "talep_eden_danisan": gd_ad,
                            "kaynak": kaynak,
                            "giren_gd": user_name,
                            "il": il,
                            "ilce": ilce_val,
                            "ilceler": ilceler if ilceler else ([ilce_val] if ilce_val else []),
                            "mulk_tipi": mulk,
                            "islem_tipi": islem,
                            "fiyat": fiyat,
                            "oda_sayisi_m2": oda,
                            "mahalle": mahalle,
                            "ilan_linki": link,
                            "ozet": ozet,
                            "ozel_kriterler": ozel,
                            "foto_url": ",".join(foto_urls_list) if foto_urls_list else "",
                            "kapali_portfoy": kapali_flag,
                            "aktif": False if yeni_portfoy_tipi == "Kapalı Portföy" else True,
                            "olusturma_tarihi": datetime.now().isoformat(),
                        }

                        kayit = portfoy_kaydet(veri)

                        if kayit is not None:
                            kayit_id = str(kayit.get("id") or storage_key)

                            if pm_musteri_adi.strip():
                                try:
                                    get_client().table("musteriler").insert({
                                        "portfoy_id": kayit_id,
                                        "musteri_adi": pm_musteri_adi.strip(),
                                        "musteri_soyadi": pm_musteri_soyadi.strip(),
                                        "telefon": pm_musteri_tel.strip(),
                                        "ekleyen": user_name,
                                        "danisan_id": user_name,
                                    }).execute()
                                except Exception:
                                    pass

                            st.session_state.pop("pm_parse_sonuc", None)
                            st.session_state["pm_aktif_sekme"] = "bos"
                            st.success("✅ Portföy kaydedildi.")
                            st.rerun()

        with kb:
            if st.button("İptal", key="pm_iptal"):
                st.session_state.pop("pm_parse_sonuc", None)
                st.session_state["pm_aktif_sekme"] = "bos"
                st.rerun()
