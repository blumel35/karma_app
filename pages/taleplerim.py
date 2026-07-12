import streamlit as st
import sys, os, re, json, html, uuid
from pathlib import Path
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.ui_helpers import render_navbar, render_page_header
from core.supabase_client import get_client
from core.match_engine import eslesen_portfoyleri_bul

render_navbar(
    user_role=st.session_state.get("user_role", "danisan"),
    user_name=st.session_state.get("user_name", ""),
    user_initials=st.session_state.get("user_initials", ""),
)

if st.button("← Çalışma Alanına Dön", key="tm_geri_kokpit"):
    st.switch_page("pages/gd_calisma_alani.py")

# ── Helpers ───────────────────────────────────────────────────────────────────
def _mail_metni_temizle(ham_html):
    """Ham HTML mail gövdesini okunabilir düz metne çevirir. Mail istemcileri
    (Yandex, Outlook vb.) gövdeyi HTML olarak sakladığı için (<div>, <br />
    gibi etiketlerle) bu dönüşüm olmadan etiketler ekranda çıplak metin gibi
    görünüyordu. <br>/</div> gibi satır-sonu niteliğindeki etiketleri gerçek
    satır sonuna çevirir, kalan etiketleri siler, &nbsp; gibi HTML karakter
    kodlarını çözer."""
    if not ham_html:
        return ""
    metin = re.sub(r'(?i)<br\s*/?>', '\n', ham_html)
    metin = re.sub(r'(?i)</(div|p|li|tr)>', '\n', metin)
    metin = re.sub(r'(?i)<[^>]+>', '', metin)
    metin = html.unescape(metin)
    metin = re.sub(r'\n{3,}', '\n\n', metin)
    return metin.strip()


def _sayfali_cek(sorgu_fn, sayfa_boyutu=1000):
    """Supabase/PostgREST varsayılan olarak tek sorguda en fazla 1000 satır
    döndürür. .range() kullanmadan büyük bir tabloyu (örn. haftalık tüm İzmir
    taraması sonrası şişen izmir_pazar_ilanlar) okumaya çalışırsan, hata
    ALMADAN sessizce ilk 1000 kaydı döndürür — eşleşme motoru geri kalanını
    hiç görmez. Bu yardımcı fonksiyon, sorgu bitene kadar sayfa sayfa okur.

    sorgu_fn(baslangic, bitis) -> Supabase response nesnesi almalı
    (yani .range(baslangic, bitis).execute() çağrısını içeren bir lambda)."""
    tum_satirlar = []
    baslangic = 0
    while True:
        resp = sorgu_fn(baslangic, baslangic + sayfa_boyutu - 1)
        satirlar = resp.data or []
        tum_satirlar.extend(satirlar)
        if len(satirlar) < sayfa_boyutu:
            break
        baslangic += sayfa_boyutu
    return tum_satirlar


@st.cache_data(ttl=120)
def _tum_portfoyler_esleme_icin():
    """Eşleşme motoru için TÜM portföyleri çeker — aktif/pasif ayrımını
    match_engine kendi içinde yapıyor (coalesce(aktif,true) mantığı),
    burada filtre uygulamıyoruz. Sadece okuma, veritabanına yazmıyor.

    ÖNEMLİ DÜZELTME: Eskiden .range() olmadan select("*").execute()
    kullanılıyordu — portfoyler tablosu 1000 satırı geçtiğinde eşleşme
    motoru sessizce eksik veriyle çalışırdı. Artık sayfalanmış okunuyor."""
    try:
        return _sayfali_cek(
            lambda b, s: get_client().table("portfoyler").select("*").range(b, s).execute()
        )
    except Exception:
        return []


@st.cache_data(ttl=120)
def _startkey_agi_ilanlari_esleme_icin():
    """izmir_pazar_ilanlar'dan Startkey ağı ilanlarını çeker (marka filtresi
    match_engine içinde uygulanıyor, burada sadece aktif olanları çekip
    veri boyutunu makul tutuyoruz). Sadece okuma.

    ÖNEMLİ DÜZELTME: Haftalık tüm İzmir taraması gibi büyük hacimli
    çekimlerden sonra bu tablo kolayca 1000 satırı geçebilir. Eskiden
    .range() olmadan çekiliyordu, bu da sessiz veri kaybına yol açardı.
    Artık sayfalanmış okunuyor."""
    try:
        return _sayfali_cek(
            lambda b, s: (
                get_client().table("izmir_pazar_ilanlar")
                .select("*")
                .eq("marka", "startkey")
                .eq("aktif", True)
                .range(b, s)
                .execute()
            )
        )
    except Exception:
        return []


def htmlesc(v):
    return html.escape(str(v if v is not None else "—"))


def fiyat_formatla(v):
    """Talep/portföy fiyatlarını 3.500.000 TL formatına yaklaştırır.
    Mevcut veri kolonunu değiştirmez; sadece ekranda okunabilir gösterir."""
    if v is None:
        return "—"

    if isinstance(v, (int, float)):
        try:
            n = int(v)
            return f"{n:,}".replace(",", ".") + " TL" if n > 0 else "—"
        except Exception:
            return str(v)

    s = str(v).strip()
    if not s or s in ("—", "None", "nan"):
        return "—"

    lower = s.lower().replace("ı", "i")

    # 3.5 milyon / 3,5 mio / 5mio gibi kullanımlar
    m = re.search(r"(\d+(?:[\.,]\d+)?)\s*(milyon|mio|mn|m)\b", lower)
    if m:
        try:
            n = int(float(m.group(1).replace(",", ".")) * 1_000_000)
            return f"{n:,}".replace(",", ".") + " TL"
        except Exception:
            pass

    digits = re.sub(r"[^0-9]", "", s)
    if digits and len(digits) >= 4:
        try:
            n = int(digits)
            return f"{n:,}".replace(",", ".") + " TL"
        except Exception:
            pass

    return s if "tl" in lower else s


def isim_ayikla(g):
    if not g:
        return ""
    if "<" in g:
        g = g[:g.index("<")].strip()
    return re.sub(r"[\"']", "", g).strip()


def tarih_parse(s):
    """Tarih string'ini datetime olarak döndürür (saat dahil).
    2_Talep_Tablosu.py / 3_Portfoy_Tablosu.py ile aynı mantık — önce mail
    header formatını (RFC2822, örn. 'Mon, 06 Jul 2026 11:37:44 +0300')
    dener, olmazsa ISO/Türkçe formatlara düşer.

    ÖNEMLİ DÜZELTME: Eskiden bu fonksiyon parsedate_to_datetime hiç
    denenmiyordu, bu yüzden mail kaynaklı kayıtlardaki 'kayit_tarihi'
    (RFC2822 formatında) hiçbir zaman parse edilemiyor, tarih hep "—"
    görünüyordu.
    """
    if not s:
        return None
    try:
        return parsedate_to_datetime(str(s))
    except Exception:
        pass
    s = str(s)
    for fmt in (
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
        "%d.%m.%Y %H:%M",
        "%d.%m.%Y",
    ):
        try:
            return datetime.strptime(s[:len(datetime.now().strftime(fmt))], fmt)
        except Exception:
            try:
                return datetime.strptime(s[:25], fmt)
            except Exception:
                pass
    return None


def en_iyi_tarih(v):
    """2_Talep_Tablosu.py ile aynı öncelik sırası: mail tarihi varsa onu,
    yoksa kayıt/oluşturma tarihini döndürür."""
    return (
        v.get("mail_tarihi")
        or v.get("kayit_tarihi")
        or v.get("olusturma_tarihi")
        or v.get("created_at")
        or ""
    )


def tarih_str(v):
    d = tarih_parse(en_iyi_tarih(v))
    if not d:
        return "—"
    has_t = hasattr(d, "hour") and (d.hour != 0 or d.minute != 0)
    return d.strftime("%d.%m.%Y %H:%M") if has_t else d.strftime("%d.%m.%Y")


def tarih_sade(s):
    d = tarih_parse(s)
    if not d:
        return "—"
    return d.strftime("%d.%m.%Y %H:%M")


def ilce_grubu(v):
    ilceler = v.get("ilceler") or []
    ilce = v.get("ilce", "") or ""
    tum = ([ilce] if ilce else []) + [i for i in ilceler if i != ilce]
    tum = [i for i in tum if i and i != "Diğer Bölge"]
    return " · ".join(tum[:3]) if tum else (v.get("bolge_mahalle", "") or "—")


def tip_badge(islem):
    islem = (islem or "").lower()
    if "kiralık" in islem or "kiralik" in islem:
        return "#f0fdf4", "#166534", "Kiralık"
    if "satılık" in islem or "satilik" in islem:
        return "#fef2f2", "#991b1b", "Satılık"
    return "#f8fafc", "#64748b", islem.title() if islem else "—"


def kaynak_etiketi(portfoy):
    return {
        "kapali_portfoy": "Kapalı Portföy",
        "kapali_adayi": "Kapalı Aday",
        "ilandaki_portfoy": "Zeta Portföyü",
        "startkey_agi": "Startkey Ağı",
        "portfoy_havuzu": "Portföy Havuzu",
    }.get(portfoy.get("portfoy_gorunurluk", ""), portfoy.get("portfoy_gorunurluk") or "Portföy Havuzu")


def ofis_etiketi(portfoy):
    """Hangi ofisin portföyü olduğunu gösterir.
    - izmir_pazar_ilanlar (Startkey Ağı) kaynaklı kayıtlarda gerçek 'ofis'
      alanı var, doğrudan kullanılır.
    - portfoyler tablosunda ayrı bir 'ofis' kolonu yok; 'kaynak' alanından
      (zeta1/zeta2/dis_kaynak/startkey_mail) türetilir."""
    ofis = portfoy.get("ofis")
    if ofis:
        return ofis
    kaynak = (portfoy.get("kaynak") or "").lower().strip()
    return {
        "zeta1": "Zeta 1",
        "zeta2": "Zeta 2",
        "dis_kaynak": "Dış Kaynak (Köprü)",
        "startkey_mail": "Startkey Mail Ağı",
        "ofis": "Ofis (manuel)",
    }.get(kaynak, "—")


def skor_renkleri(skor, seviye):
    seviye_l = str(seviye or "").lower()
    try:
        skor_i = int(skor or 0)
    except Exception:
        skor_i = 0
    if "güç" in seviye_l or "guc" in seviye_l or skor_i >= 80:
        return "#dcfce7", "#166534", "#bbf7d0", "Güçlü"
    if skor_i >= 60:
        return "#fef3c7", "#92400e", "#fde68a", "Orta"
    return "#f1f5f9", "#475569", "#e2e8f0", (seviye or "Aday").title()


def gerekce_badgeleri(gerekce):
    metin = str(gerekce or "").strip()
    if not metin:
        return ["Uygun aday"]
    parcalar = re.split(r"[\n\|;,·]+", metin)
    temiz = []
    for p in parcalar:
        p = re.sub(r"^[\s\-•✅✓]+", "", p).strip()
        p = re.sub(r"\s+", " ", p)
        if p and len(p) <= 42 and p not in temiz:
            temiz.append(p)
    if not temiz:
        temiz = [metin[:42]]
    return temiz[:5]


def talep_ozeti_olustur(v, musteri_map=None):
    kid = str(v.get("id", ""))
    musteri = (musteri_map or {}).get(kid, "") or v.get("musteri_adi", "") or "—"
    ilce = ilce_grubu(v)
    islem = v.get("islem_tipi") or "—"
    butce = fiyat_formatla(v.get("max_butce"))
    oda = v.get("oda_sayisi_m2") or "—"
    mulk = v.get("mulk_tipi") or "—"
    son = tarih_sade(v.get("son_eslesme_tarihi")) if v.get("son_eslesme_tarihi") else "—"
    return {
        "kid": kid,
        "ilce": ilce,
        "islem": islem,
        "butce": butce,
        "oda": oda,
        "mulk": mulk,
        "musteri": musteri,
        "son_arama": son,
        "kisa": f"{ilce} · {islem} · {butce} · {oda}",
        "alt": f"{mulk} · {oda} · {musteri}",
    }


ILLER = ["İzmir", "Aydın", "Manisa", "Balıkesir", "Muğla", "İstanbul", "Ankara", "Diğer"]


# ── Gönderime Hazırla / Hazır Şablon Yardımcıları ─────────────────────────────
# Bu bölüm veritabanı şemasını değiştirmez. GD'nin Canva/PDF/görsel/HTML gibi
# hazır gönderim şablonlarını proje klasöründe saklar ve Gönderim Özeti panelinde
# seçilebilir hale getirir. Streamlit Cloud gibi geçici dosya sistemlerinde bu
# klasör kalıcı olmayabilir; lokal/kurumsal sunucuda kalıcıdır.
BASE_DIR = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TEMPLATE_DIR = BASE_DIR / "data" / "gonderim_sablonlari"
TEMPLATE_META_FILE = TEMPLATE_DIR / "templates.json"
ALLOWED_TEMPLATE_EXTS = {"pdf", "png", "jpg", "jpeg", "webp", "html", "htm"}


def _ensure_template_store():
    TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)
    if not TEMPLATE_META_FILE.exists():
        TEMPLATE_META_FILE.write_text("[]", encoding="utf-8")


def _safe_filename(name):
    name = re.sub(r"[^A-Za-z0-9_ğüşöçıİĞÜŞÖÇ\-. ]+", "_", str(name or "sablon")).strip()
    return name or "sablon"


def _load_templates():
    try:
        _ensure_template_store()
        data = json.loads(TEMPLATE_META_FILE.read_text(encoding="utf-8") or "[]")
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _save_templates(items):
    try:
        _ensure_template_store()
        TEMPLATE_META_FILE.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
        return True
    except Exception as e:
        st.warning(f"Şablon metadata kaydedilemedi: {e}")
        return False


def _template_label(t):
    kanal = t.get("kanal", "Genel")
    kaynak = "Canva link" if t.get("url") else "Dosya"
    return f'{t.get("baslik", "Şablon")} · {kanal} · {kaynak}'


def _save_uploaded_template(uploaded_file, baslik, kanal, owner_name, url=""):
    items = _load_templates()
    tid = str(uuid.uuid4())[:8]
    file_path = ""
    original_name = ""
    if uploaded_file is not None:
        original_name = _safe_filename(uploaded_file.name)
        ext = original_name.split(".")[-1].lower() if "." in original_name else ""
        if ext not in ALLOWED_TEMPLATE_EXTS:
            raise ValueError("Sadece PDF, görsel veya HTML şablon yüklenebilir.")
        stored_name = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{tid}_{original_name}"
        full_path = TEMPLATE_DIR / stored_name
        full_path.write_bytes(uploaded_file.getbuffer())
        file_path = str(full_path)

    if not file_path and not str(url or "").strip():
        raise ValueError("Şablon için dosya yükleyin veya Canva/link girin.")

    item = {
        "id": tid,
        "baslik": (baslik or original_name or "Hazır Şablon").strip(),
        "kanal": kanal or "Genel",
        "owner": owner_name or "—",
        "url": str(url or "").strip(),
        "file_path": file_path,
        "file_name": original_name,
        "created_at": datetime.now().isoformat(),
    }
    items.insert(0, item)
    _save_templates(items)
    return item


def _selected_templates_key(talep_id):
    return f"tm_selected_template_{talep_id}"


def _selected_portfolios_key(talep_id):
    return f"tm_secili_portfoyler_{talep_id}"


def _portfolio_identity(p, index=0):
    if p.get("id") is not None:
        return str(p.get("id"))
    raw = f'{p.get("baslik") or p.get("ozet") or ""}|{p.get("ilan_linki") or ""}|{index}'
    return str(abs(hash(raw)))


def _portfolio_compact(sonuc, index=0):
    p = sonuc.get("portfoy", {}) or {}
    return {
        "pid": _portfolio_identity(p, index),
        "id": p.get("id"),
        "baslik": p.get("baslik") or p.get("ozet") or "Portföy",
        "fiyat": fiyat_formatla(p.get("fiyat")),
        "ilce": p.get("ilce") or "—",
        "oda": p.get("oda_sayisi_m2") or "—",
        "skor": sonuc.get("skor", "—"),
        "seviye": sonuc.get("seviye", ""),
        "kaynak": kaynak_etiketi(p),
        "ilan_linki": p.get("ilan_linki") or "",
    }


def _get_selected_portfolios(talep_id):
    key = _selected_portfolios_key(talep_id)
    val = st.session_state.get(key, [])
    return val if isinstance(val, list) else []


def _toggle_selected_portfolio(talep_id, sonuc, index=0):
    key = _selected_portfolios_key(talep_id)
    mevcut = _get_selected_portfolios(talep_id)
    item = _portfolio_compact(sonuc, index)
    if any(str(x.get("pid")) == str(item["pid"]) for x in mevcut):
        mevcut = [x for x in mevcut if str(x.get("pid")) != str(item["pid"])]
    else:
        mevcut.append(item)
    st.session_state[key] = mevcut


def _is_portfolio_selected(talep_id, sonuc, index=0):
    item = _portfolio_compact(sonuc, index)
    return any(str(x.get("pid")) == str(item["pid"]) for x in _get_selected_portfolios(talep_id))


def _eslesme_kpi_hesapla(sel):
    sonuclar = st.session_state.get(f"tm_esleme_sonuc_{sel.get('id')}")
    if sonuclar is None:
        sonuclar = normalize_eslesme_sonuclari(sel.get("son_eslesme_json"))

    guclu = 0
    alternatif = 0
    butce_iyi = False
    ilce_iyi = False
    for s in sonuclar or []:
        try:
            skor = int(s.get("skor") or 0)
        except Exception:
            skor = 0
        if skor >= 80:
            guclu += 1
        elif skor >= 60:
            alternatif += 1
        gerekce = str(s.get("gerekce", "")).lower()
        if "bütçe içinde" in gerekce or "butce icinde" in gerekce or "bütçe uygun" in gerekce or "butce uygun" in gerekce:
            butce_iyi = True
        if "aynı ilçe" in gerekce or "ayni ilce" in gerekce or "ilçe uyumu" in gerekce or "ilce uyumu" in gerekce:
            ilce_iyi = True

    return {
        "guclu": guclu,
        "alternatif": alternatif,
        "butce": "yüksek" if butce_iyi or guclu else "kontrol",
        "ilce": "güçlü" if ilce_iyi or guclu else "kontrol",
        "son_arama": (
            st.session_state.get(f"tm_esleme_tarih_{sel.get('id')}")
            or (tarih_sade(sel.get("son_eslesme_tarihi")) if sel.get("son_eslesme_tarihi") else "—")
        ),
    }

# ── Veri fonksiyonları ────────────────────────────────────────────────────────
@st.cache_data(ttl=60)
def ilce_listesi_cek():
    try:
        r = get_client().table("ilceler").select("ilce").execute()
        return sorted([x["ilce"] for x in r.data if x.get("ilce")])
    except Exception:
        return []


@st.cache_data(ttl=60)
def zeta_gd_listesi():
    """Zeta 1 ve Zeta 2 portföylerindeki danışman isimlerini döndürür.

    ÖNEMLİ DÜZELTME: Bu liste eskiden sadece portföy PAYLAŞMIŞ danışmanları
    içeriyordu (portfoyler tablosundaki talep_eden_danisan'dan türetiliyor).
    Admin/broker gibi kendi adına portföy paylaşmayan ama talep girmesi
    gereken kullanıcılar (örn. Meltem Bulu) listede hiç görünmüyordu, tek
    seçenek "Diğer (manuel gir)" oluyordu. Artık oturumdaki kullanıcının
    adı, hangi ofis seçilirse seçilsin, listeye otomatik ekleniyor."""
    try:
        z1 = sorted(set(
            isim_ayikla(v.get("talep_eden_danisan", ""))
            for v in (get_client().table("portfoyler").select("talep_eden_danisan")
                      .in_("kaynak", ["zeta1"]).execute().data or [])
            if v.get("talep_eden_danisan", "")
        ))
        z2 = sorted(set(
            isim_ayikla(v.get("talep_eden_danisan", ""))
            for v in (get_client().table("portfoyler").select("talep_eden_danisan")
                      .in_("kaynak", ["zeta2"]).execute().data or [])
            if v.get("talep_eden_danisan", "")
        ))
        mevcut_kullanici = (user_name or "").strip()
        if mevcut_kullanici:
            z1 = sorted(set(z1 + [mevcut_kullanici]))
            z2 = sorted(set(z2 + [mevcut_kullanici]))
        return z1, z2, sorted(set(z1 + z2))
    except Exception:
        return [], [], []


@st.cache_data(ttl=60)
def mahalle_lookup_cek():
    try:
        r = get_client().table("mahalleler").select("il,ilce,mahalle").execute()
        return {row["mahalle"].strip().lower(): (row["il"], row["ilce"]) for row in r.data}
    except Exception:
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


def talep_kaydet(veri):
    try:
        get_client().table("alici_talepleri").insert(veri).execute()
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Kayıt hatası: {e}")
        return False


def favori_guncelle(kid, mevcut):
    try:
        get_client().table("alici_talepleri").update({"favori": not mevcut}).eq("id", kid).execute()
        st.cache_data.clear()
        st.rerun(scope="app")
    except Exception as e:
        st.error(f"Hata: {e}")


def ai_parse_talep(metin):
    import requests
    prompt = f"""Aşağıdaki gayrimenkul talep açıklamasını analiz et ve JSON olarak döndür.
Sadece JSON döndür, başka hiçbir şey yazma.

Talep:
{metin}

JSON formatı:
{{
  "il": "İzmir",
  "ilce": "birincil ilçe veya boş",
  "ilceler": ["ilçe1", "ilçe2"],
  "mulk_tipi": "Konut/İşyeri/Arsa/Belirsiz",
  "islem_tipi": "Satılık/Kiralık/Belirsiz",
  "oda_sayisi_m2": "3+1 veya 120 m² gibi",
  "max_butce": "rakam ve para birimi",
  "mahalle": "mahalle/semt bilgisi",
  "ozel_kriterler": "özel istekler, notlar",
  "ozet": "talebi özetleyen kısa cümle (şehir adı yazma, sadece talep özeti)"
}}"""
    try:
        api_key = st.secrets["anthropic"]["api_key"].strip()
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"Content-Type": "application/json", "x-api-key": api_key, "anthropic-version": "2023-06-01"},
            json={"model": "claude-sonnet-4-6", "max_tokens": 600, "messages": [{"role": "user", "content": prompt}]},
            timeout=30,
        )
        data = resp.json()
        if "error" in data:
            return {"_parse_hatasi": data["error"].get("message", str(data["error"]))}
        text = data["content"][0]["text"].strip().replace("```json", "").replace("```", "").strip()
        return json.loads(text)
    except Exception as e:
        return {"ozet": metin, "_parse_hatasi": str(e)}


@st.cache_data(ttl=60)
def benim_taleplerim(user_id, user_name):
    """
    ÖNEMLİ DÜZELTME: Eskiden burada `.limit(500)` vardı — sorgu önce tabloda
    en yeni 500 kaydı çekiyor, SONRA kullanıcıya göre filtreliyordu. Tablo
    500'den fazla satıra ulaştığında (örn. toplu mail çekimi sonrası), eski
    tarihli kendi taleplerin bu 500'lük pencerenin dışına düşüp hiç
    görünmüyordu — veri kaybı yoktu ama bu sayfadan erişilemiyordu.
    Artık `.range()` ile sayfa sayfa TÜM kayıtlar çekiliyor, hiçbir kayıt
    filtreye ulaşmadan elenmiyor.
    """
    try:
        tum = []
        sayfa_boyu = 1000
        bas = 0
        while True:
            r = (
                get_client()
                .table("alici_talepleri")
                .select("*")
                .eq("kategori", "alici_talebi")
                .order("olusturma_tarihi", desc=True)
                .range(bas, bas + sayfa_boyu - 1)
                .execute()
            )
            parca = r.data or []
            tum.extend(parca)
            if len(parca) < sayfa_boyu:
                break
            bas += sayfa_boyu

        sonuc = []
        goruldu = set()
        for v in tum:
            vid = v.get("id")
            if vid in goruldu:
                continue
            if user_id and v.get("user_id") == user_id:
                sonuc.append(v)
                goruldu.add(vid)
                continue
            if user_name and user_name.strip():
                un = user_name.lower().strip()
                gd = isim_ayikla(v.get("talep_eden_danisan", "")).lower()
                if un in gd or gd in un:
                    sonuc.append(v)
                    goruldu.add(vid)
                    continue
                gg = isim_ayikla(v.get("giren_gd", "")).lower()
                if gg and (un in gg or gg in un):
                    sonuc.append(v)
                    goruldu.add(vid)
                    continue
        return sonuc
    except Exception as e:
        st.error(f"Hata: {e}")
        return []


@st.cache_data(ttl=60)
def favori_talepler():
    """Aynı düzeltme: sabit .limit(200) yerine tam sayfalama."""
    try:
        tum = []
        sayfa_boyu = 1000
        bas = 0
        while True:
            r = (
                get_client()
                .table("alici_talepleri")
                .select("*")
                .eq("favori", True)
                .eq("kategori", "alici_talebi")
                .order("olusturma_tarihi", desc=True)
                .range(bas, bas + sayfa_boyu - 1)
                .execute()
            )
            parca = r.data or []
            tum.extend(parca)
            if len(parca) < sayfa_boyu:
                break
            bas += sayfa_boyu
        return tum
    except Exception:
        return []


@st.cache_data(ttl=60)
def talepleri_kullaniciya_gore_sinifla(user_id, user_name):
    """
    portfoylerím.py'deki 'İlandaki / Kapalı / Zeta / Köprü' modelinin talep
    tarafı karşılığı. 3'lü sınıflandırma:

    1. Benim Taleplerim
       user_id eşleşmesi VEYA talep_eden_danisan/giren_gd isim eşleşmesi —
       ama kaynak='dis_kaynak' (köprü) olan kayıtlar burada DEĞİL, 2. maddede.

    2. Zeta Talepleri
       talep_eden_danisan veya giren_gd, Zeta 1/Zeta 2 danışman rosterinde
       (zeta_gd_listesi() → portfoyler tablosundan türetilir) yer alan ama
       BANA AİT OLMAYAN kayıtlar. Kaynak fark etmez — hem ofis içi manuel
       girilenler hem Startkey mail sisteminden gelenler dahil, çünkü roster
       eşleşmesi zaten kişinin Zeta 1/Zeta 2 danışmanı olduğunu gösteriyor.
       Startkey'in geneli (diğer franchise ofisleri) dahil DEĞİL.

    3. Köprü Talepler
       kaynak == 'dis_kaynak' VE giren_gd bana ait — başka bir danışmandan/
       dış kaynaktan gelip benim sisteme manuel girdiğim talepler.
    """
    try:
        tum = []
        sayfa_boyu = 1000
        bas = 0
        while True:
            r = (
                get_client()
                .table("alici_talepleri")
                .select("*")
                .eq("kategori", "alici_talebi")
                .order("olusturma_tarihi", desc=True)
                .range(bas, bas + sayfa_boyu - 1)
                .execute()
            )
            parca = r.data or []
            tum.extend(parca)
            if len(parca) < sayfa_boyu:
                break
            bas += sayfa_boyu

        _, _, gd_list_tum = zeta_gd_listesi()
        zeta_roster = set(x.lower().strip() for x in gd_list_tum if x and len(x.strip()) > 1)

        def _zeta_roster_eslesme(v):
            for alan in ("talep_eden_danisan", "giren_gd"):
                isim = isim_ayikla(v.get(alan, "")).lower().strip()
                if not isim:
                    continue
                if isim in zeta_roster:
                    return True
                if any(isim in r or r in isim for r in zeta_roster):
                    return True
            return False

        un = (user_name or "").lower().strip()
        gruplar = {"benim": [], "zeta": [], "kopru": []}
        goruldu = set()

        for v in tum:
            vid = v.get("id")
            if vid in goruldu:
                continue

            kaynak = (v.get("kaynak", "") or "").lower().strip()
            giren_isim = isim_ayikla(v.get("giren_gd", "")).lower().strip()
            talep_isim = isim_ayikla(v.get("talep_eden_danisan", "")).lower().strip()

            giren_bana_ait = bool(un) and bool(giren_isim) and (un in giren_isim or giren_isim in un)
            talep_bana_ait = (user_id and v.get("user_id") == user_id) or (
                bool(un) and bool(talep_isim) and (un in talep_isim or talep_isim in un)
            )

            # 1) Köprü — önce bu kontrol ediliyor ki "benim girdiğim ama
            #    başkasına ait" kayıtlar yanlışlıkla "Benim Taleplerim"e düşmesin.
            if kaynak == "dis_kaynak" and giren_bana_ait:
                gruplar["kopru"].append(v)
                goruldu.add(vid)
                continue

            # 2) Benim Taleplerim
            if talep_bana_ait or giren_bana_ait:
                gruplar["benim"].append(v)
                goruldu.add(vid)
                continue

            # 3) Zeta Talepleri
            if _zeta_roster_eslesme(v):
                gruplar["zeta"].append(v)
                goruldu.add(vid)

        return gruplar
    except Exception as e:
        st.error(f"Hata: {e}")
        return {"benim": [], "zeta": [], "kopru": []}


@st.cache_data(ttl=60)
def talep_musteri_map():
    try:
        r = get_client().table("musteriler").select("talep_id,musteri_adi").execute()
        return {str(row["talep_id"]): row["musteri_adi"] for row in (r.data or []) if row.get("talep_id")}
    except Exception:
        return {}


@st.cache_data(ttl=60)
def musteri_cek_talep(talep_id):
    try:
        r = get_client().table("musteriler").select("*").eq("talep_id", str(talep_id)).execute()
        return r.data or []
    except Exception:
        return []


def _sonuc_serialize_listesi(sonuclar):
    """Motor sonucunu sadece ekranda kullanılan alanlarla hafifletir.
    Eşleşme algoritması ve skor mantığına dokunmaz.

    ÖNEMLİ DÜZELTME: talep_eden_danisan ve tarih alanları eskiden bu
    listede hiç yoktu — bu yüzden Eşleşen Portföyler kartlarında danışman
    ve tarih her zaman "—" görünüyordu, veri portfoyler tablosunda dolu
    olsa bile (JSON'a hiç yazılmıyordu). Artık dahil ediliyor.
    """
    cikti = []
    for s in sonuclar:
        p = s.get("portfoy", {}) or {}
        tarih_ham = (
            p.get("ilan_tarihi") or p.get("mail_tarihi") or p.get("paylasim_tarihi")
            or p.get("kayit_tarihi") or p.get("olusturma_tarihi") or ""
        )
        cikti.append({
            "skor": s.get("skor"),
            "seviye": s.get("seviye"),
            "gerekce": s.get("gerekce", ""),
            "grup": s.get("grup"),
            "portfoy": {
                "id": p.get("id"),
                "ozet": p.get("ozet"),
                "baslik": p.get("baslik"),
                "ilce": p.get("ilce"),
                "oda_sayisi_m2": p.get("oda_sayisi_m2") or p.get("oda") or p.get("oda_sayisi"),
                "fiyat": p.get("fiyat"),
                "portfoy_gorunurluk": p.get("portfoy_gorunurluk"),
                "ilan_linki": p.get("ilan_linki"),
                "talep_eden_danisan": p.get("talep_eden_danisan"),
                "tarih_ham": tarih_ham,
                "ofis": p.get("ofis"),
                "kaynak": p.get("kaynak"),
            },
        })
    return cikti


def _esleme_ara_ve_kaydet(talep_kaydi, talep_id):
    _portfoy_havuzu = _tum_portfoyler_esleme_icin()
    _pazar_havuzu = _startkey_agi_ilanlari_esleme_icin()
    _sonuclar = eslesen_portfoyleri_bul(
        talep_kaydi, _portfoy_havuzu, pazar_ilanlari=_pazar_havuzu, max_sonuc=10
    )
    _hafif = _sonuc_serialize_listesi(_sonuclar)
    try:
        get_client().table("alici_talepleri").update({
            "son_eslesme_json": _hafif,
            "son_eslesme_tarihi": datetime.now(timezone.utc).isoformat(),
        }).eq("id", talep_id).execute()
    except Exception as e:
        st.warning(f"Eşleşme sonucu kaydedilemedi (sonuçlar yine de gösteriliyor): {e}")
    return _hafif


def normalize_eslesme_sonuclari(v):
    if not v:
        return []
    if isinstance(v, list):
        return v
    if isinstance(v, str):
        try:
            parsed = json.loads(v)
            return parsed if isinstance(parsed, list) else []
        except Exception:
            return []
    return []

# ── Session ───────────────────────────────────────────────────────────────────
_k = st.session_state.get("kullanici", {})
user_id = _k.get("id", "")
user_name = _k.get("ad_soyad") or _k.get("ad", "")

ilce_sec = ilce_listesi_cek()
gd_list_z1, gd_list_z2, gd_list_tum = zeta_gd_listesi()

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
.tm-section-label {
    font-size:10px;font-weight:700;color:#94a3b8;text-transform:uppercase;
    letter-spacing:.08em;margin:16px 0 8px;border-bottom:1px solid #f1f5f9;padding-bottom:6px;
}
.demand-card {
    background:#ffffff;border:1px solid #e2e8f0;border-radius:14px;padding:10px 12px;
    margin:0 0 6px 0;box-shadow:0 1px 2px rgba(15,23,42,.03);
}
.demand-card-active {
    background:#fff1f2;border:1px solid #fecdd3;border-left:4px solid #dc2626;
    border-radius:14px;padding:10px 12px;margin:0 0 6px 0;
    box-shadow:0 6px 18px rgba(220,38,38,.07);
}
.demand-card-title {font-size:13px;font-weight:800;color:#172B4D;line-height:1.28;margin-bottom:4px;}
.demand-card-subtitle {font-size:12px;font-weight:600;color:#475569;line-height:1.3;}
.demand-card-meta {font-size:10.5px;color:#94a3b8;margin-top:4px;}
.selected-demand-summary {
    background:#ffffff;border:1px solid #e2e8f0;
    border-radius:16px;padding:13px 15px;margin-bottom:12px;box-shadow:0 8px 24px rgba(15,23,42,.06);
}
.summary-main {font-size:15px;font-weight:850;color:#172B4D;line-height:1.35;margin-bottom:6px;}
.summary-sub {font-size:12px;color:#64748b;line-height:1.45;}
.match-card {
    background:#ffffff;border:1px solid #e2e8f0;border-radius:16px;padding:14px 15px;
    margin-bottom:10px;box-shadow:0 3px 12px rgba(15,23,42,.04);
}
.match-card-head {display:flex;align-items:flex-start;justify-content:space-between;gap:10px;margin-bottom:8px;}
.match-score-badge {display:inline-flex;align-items:center;gap:4px;border-radius:999px;padding:4px 9px;font-size:11.5px;font-weight:850;border:1px solid transparent;white-space:nowrap;}
.match-source-badge {display:inline-flex;align-items:center;border-radius:999px;padding:3px 8px;font-size:10.5px;font-weight:700;color:#64748b;background:#f8fafc;border:1px solid #e2e8f0;white-space:nowrap;}
.match-title {font-size:14px;font-weight:850;color:#172B4D;line-height:1.35;margin-bottom:5px;}
.match-meta {font-size:12px;font-weight:600;color:#64748b;margin-bottom:8px;}
.match-reason-row {display:flex;flex-wrap:wrap;gap:5px;margin:7px 0 4px 0;}
.match-reason-badge {font-size:10.5px;font-weight:700;color:#355C7D;background:#EEF4FA;border:1px solid #dbeafe;border-radius:999px;padding:3px 8px;}
.empty-state {
    min-height:150px;display:flex;flex-direction:column;align-items:center;justify-content:center;
    text-align:center;color:#94a3b8;border:1px dashed #e2e8f0;border-radius:16px;background:#fbfdff;padding:22px;
}
.empty-state-icon {font-size:30px;line-height:1;margin-bottom:7px;color:#cbd5e1;}
.empty-state-title {font-size:13px;font-weight:800;color:#64748b;margin-bottom:3px;}
.empty-state-desc {font-size:11.5px;color:#94a3b8;max-width:320px;}
.dp-label{font-size:11px;font-weight:700;color:#64748b;text-transform:none;letter-spacing:0;margin-bottom:3px;}
.dp-value{font-size:13px;color:#1e293b;font-weight:600;margin-bottom:11px;line-height:1.45;}
.dp-divider{border:none;border-top:1px solid #f1f5f9;margin:12px 0;}
.soft-note {font-size:11.5px;color:#64748b;background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;padding:8px 10px;margin:6px 0 10px 0;}
.tm-mini-title {font-size:13px;font-weight:850;color:#172B4D;margin:4px 0 10px 0;}

/* Gönderime Hazırla revizyonu */
.kpi-row {display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:8px;margin-top:12px;}
.kpi-item {background:#F8FAFC;border:1px solid #e2e8f0;border-radius:12px;padding:9px 10px;min-height:58px;}
.kpi-value {font-size:15px;font-weight:900;color:#172B4D;line-height:1.15;}
.kpi-label {font-size:10.5px;font-weight:650;color:#64748b;margin-top:4px;line-height:1.25;}
.send-panel {background:#fff;border:1px solid #e2e8f0;border-radius:16px;padding:16px 18px;box-shadow:0 8px 24px rgba(15,23,42,.04);margin-top:8px;}
.send-title {font-size:14px;font-weight:900;color:#172B4D;margin-bottom:12px;display:flex;align-items:center;gap:7px;}
.send-label {font-size:10.5px;font-weight:800;color:#64748b;text-transform:uppercase;letter-spacing:.05em;margin-top:10px;margin-bottom:4px;}
.send-value {font-size:12.5px;font-weight:750;color:#172B4D;line-height:1.35;margin-bottom:6px;}
.send-soft-box {background:#f8fafc;border:1px solid #e2e8f0;border-radius:12px;padding:9px 10px;font-size:11.5px;color:#475569;line-height:1.45;}
.selected-mini {display:flex;align-items:flex-start;justify-content:space-between;gap:8px;background:#F8FAFC;border:1px solid #e2e8f0;border-radius:12px;padding:8px 9px;margin-bottom:6px;}
.selected-mini-title {font-size:11.5px;font-weight:850;color:#172B4D;line-height:1.25;}
.selected-mini-meta {font-size:10.5px;color:#64748b;margin-top:2px;}
.match-action-note {font-size:10.5px;color:#94a3b8;margin-top:-4px;margin-bottom:7px;}
.template-pill {display:inline-flex;align-items:center;border-radius:999px;padding:4px 8px;font-size:10.5px;font-weight:750;color:#355C7D;background:#EEF4FA;border:1px solid #dbeafe;margin:2px 4px 2px 0;}
.compact-empty {background:#fbfdff;border:1px dashed #e2e8f0;border-radius:12px;padding:10px 12px;color:#94a3b8;font-size:11.5px;line-height:1.4;}


/* Üst yatay talep paneli revizyonu */
.talep-board-shell {
    background:#ffffff;border:1px solid #e2e8f0;border-radius:18px;
    padding:14px 16px 12px 16px;margin:10px 0 18px 0;
    box-shadow:0 8px 24px rgba(15,23,42,.045);
}
.talep-board-head {display:flex;align-items:flex-start;justify-content:space-between;gap:14px;margin-bottom:10px;}
.talep-board-title {font-size:15px;font-weight:900;color:#172B4D;line-height:1.25;}
.talep-board-sub {font-size:11.5px;color:#64748b;margin-top:2px;line-height:1.35;}
.talep-grid-card {
    background:#ffffff;border:1px solid #e2e8f0;border-radius:14px;padding:11px 12px;
    min-height:100px;box-shadow:0 1px 2px rgba(15,23,42,.03);
}
.talep-grid-card-active {
    background:#fff1f2;border:1px solid #fecdd3;border-left:4px solid #dc2626;
    border-radius:14px;padding:11px 12px;min-height:100px;
    box-shadow:0 6px 18px rgba(220,38,38,.07);
}
.talep-grid-title {font-size:13px;font-weight:900;color:#172B4D;line-height:1.28;margin-bottom:6px;min-height:34px;}
.talep-grid-sub {font-size:11.5px;font-weight:650;color:#475569;line-height:1.3;margin-bottom:5px;}
.talep-grid-meta {font-size:10.5px;color:#94a3b8;line-height:1.25;}
.talep-grid-badge {display:inline-flex;border-radius:999px;background:#F8FAFC;border:1px solid #e2e8f0;color:#64748b;font-size:10px;font-weight:750;padding:2px 7px;margin-top:6px;}
.talep-detail-band {
    background:#ffffff;border:1px solid #e2e8f0;border-radius:16px;padding:14px 16px;
    margin:0 0 12px 0;box-shadow:0 3px 12px rgba(15,23,42,.035);
}
.talep-detail-band-title {font-size:13.5px;font-weight:900;color:#172B4D;margin-bottom:10px;}
.talep-detail-grid {display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:8px;}
.talep-detail-item {background:#F8FAFC;border:1px solid #e2e8f0;border-radius:12px;padding:8px 9px;}
.talep-detail-label {font-size:10px;font-weight:800;color:#94a3b8;text-transform:uppercase;letter-spacing:.045em;margin-bottom:3px;}
.talep-detail-value {font-size:11.5px;font-weight:800;color:#172B4D;line-height:1.28;overflow-wrap:anywhere;}
.talep-detail-note {background:#fff;border:1px dashed #e2e8f0;border-radius:12px;padding:9px 10px;margin-top:9px;font-size:11.5px;color:#475569;line-height:1.45;}
.pagination-note {font-size:10.5px;color:#94a3b8;margin-top:4px;}


/* Talep Tablosu hiyerarşisi: Liste / Kart paneli */
.talep-view-toolbar {
    display:flex;align-items:center;justify-content:space-between;gap:12px;
    background:#fff;border:1px solid #e2e8f0;border-radius:14px;padding:10px 12px;margin:8px 0 10px 0;
}
.talep-panel-table {
    background:#fff;border:1px solid #e2e8f0;border-radius:14px;overflow:hidden;margin-top:6px;
}
.talep-panel-head {
    display:grid;grid-template-columns:1.15fr .85fr 2.8fr 1.35fr 1.25fr 1.15fr .95fr .75fr .45fr;
    gap:10px;background:#f8fafc;border-bottom:1px solid #e2e8f0;padding:9px 12px;
    font-size:10px;font-weight:800;color:#94a3b8;text-transform:uppercase;letter-spacing:.06em;
}
.talep-panel-row {
    display:grid;grid-template-columns:1.15fr .85fr 2.8fr 1.35fr 1.25fr 1.15fr .95fr .75fr .45fr;
    gap:10px;align-items:center;padding:9px 12px;border-bottom:.5px solid #f1f5f9;background:#fff;
}
.talep-panel-row:hover {background:rgba(30,58,95,.025);}
.talep-panel-row-active {background:#fff1f2;border-left:4px solid #dc2626;padding-left:8px;}
.talep-row-title {font-size:12px;font-weight:800;color:#172B4D;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;display:block;}
.talep-row-desc {font-size:10.5px;color:#64748b;margin-top:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;display:block;}
.talep-row-tag {display:inline-block;padding:2px 7px;border-radius:5px;font-size:10px;font-weight:750;white-space:nowrap;}
.talep-row-date {font-size:10.5px;font-weight:700;padding:2px 6px;border-radius:5px;white-space:nowrap;display:inline-block;}
.talep-row-kpi {font-size:10.5px;font-weight:800;color:#355C7D;background:#EEF4FA;border:1px solid #dbeafe;border-radius:999px;padding:2px 7px;white-space:nowrap;display:inline-block;}
.talep-row-muted {font-size:11px;color:#64748b;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.talep-panel-card {
    background:#ffffff;border:1px solid #e2e8f0;border-radius:16px;padding:15px 17px 13px 17px;
    min-height:190px;box-shadow:0 2px 10px rgba(15,23,42,.055);transition:.14s ease;
}
.talep-panel-card:hover {border-color:#b8cadb;box-shadow:0 7px 20px rgba(15,23,42,.09);transform:translateY(-1px);}
.talep-panel-card-active {background:#fff1f2;border-color:#fecdd3;border-left:4px solid #dc2626;}
.talep-card-badges {display:flex;align-items:center;justify-content:space-between;gap:8px;margin-bottom:9px;}
.talep-card-title {font-size:15px;font-weight:900;color:#0F172A;line-height:1.32;margin-bottom:7px;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;}
.talep-card-desc {font-size:12px;color:#64748b;line-height:1.45;min-height:34px;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;margin-bottom:10px;}
.talep-card-price {font-size:16px;font-weight:900;color:#172B4D;margin-bottom:10px;}
.talep-card-foot {border-top:1px solid #f1f5f9;padding-top:9px;display:flex;align-items:center;justify-content:space-between;gap:8px;}
.talep-pagination {font-size:10.5px;color:#94a3b8;margin-top:8px;line-height:1.35;}
.talep-view-help {font-size:11px;color:#64748b;line-height:1.35;}


/* ── KOMPAKT ÜST TALEP PANELİ REVİZYONU ───────────────────── */
.compact-panel-title {
    display:flex;align-items:center;justify-content:space-between;gap:10px;
    margin:2px 0 4px 0;padding:5px 8px;border:1px solid #edf2f7;
    border-radius:10px;background:#ffffff;color:#172B4D;font-size:13px;font-weight:900;
}
.compact-panel-title span {font-size:10.5px;font-weight:600;color:#94a3b8;}
.compact-toolbar-note {font-size:10px;color:#94a3b8;margin:-2px 0 4px 1px;line-height:1.25;}
.talep-board-shell {padding:7px 10px 6px 10px !important;margin:4px 0 6px 0 !important;border-radius:12px !important;box-shadow:none !important;}
.talep-board-head {margin-bottom:0 !important;}
.talep-board-title {font-size:13px !important;}
.talep-board-sub {display:none !important;}
.talep-panel-compact-head {
    display:grid;grid-template-columns:1.0fr .7fr .65fr 2.15fr 1.1fr 1.0fr .9fr .75fr .5fr .38fr;
    gap:8px;background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px 10px 0 0;
    padding:5px 9px;font-size:9.3px;font-weight:850;color:#94a3b8;text-transform:uppercase;letter-spacing:.055em;
    margin-top:4px;
}
.talep-compact-row-sep {height:1px;background:#f1f5f9;margin:0;}
.talep-inline-panel-wrap {
    background:#f8fafc;border:1px solid #e2e8f0;border-left:3px solid #355C7D;
    border-radius:8px;padding:14px 16px 10px 16px;margin:6px 0 12px 0;
}
.talep-compact-cell {
    min-height:27px;display:flex;align-items:center;overflow:hidden;
    font-size:10.5px;color:#475569;line-height:1.1;
}
.talep-compact-title {font-size:11.2px;font-weight:850;color:#172B4D;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;display:block;line-height:1.15;}
.talep-compact-desc {font-size:9.6px;color:#94a3b8;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;display:block;line-height:1.1;margin-top:1px;}
.talep-compact-tag {display:inline-flex;align-items:center;padding:1px 5px;border-radius:5px;font-size:9.2px;font-weight:800;white-space:nowrap;line-height:1.45;}
.talep-compact-date {display:inline-flex;align-items:center;padding:1px 5px;border-radius:5px;font-size:9.4px;font-weight:800;white-space:nowrap;line-height:1.45;}
.talep-compact-kpi {display:inline-flex;align-items:center;padding:1px 6px;border-radius:999px;font-size:9.3px;font-weight:850;white-space:nowrap;line-height:1.45;}
.talep-compact-muted {font-size:10.2px;color:#64748b;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;line-height:1.1;}
.talep-compact-price {font-size:10.7px;font-weight:850;color:#172B4D;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;line-height:1.1;}
.talep-list-row-active-marker {border-left:3px solid #dc2626;padding-left:5px;background:#fff7f8;border-radius:6px;}
.talep-panel-table {margin-top:3px !important;border-radius:10px !important;}
.talep-panel-head {padding:5px 9px !important;font-size:9.3px !important;}
.talep-panel-row {padding:4px 9px !important;gap:8px !important;min-height:32px !important;}
.talep-row-title {font-size:11.1px !important;line-height:1.1 !important;}
.talep-row-desc {font-size:9.6px !important;margin-top:1px !important;line-height:1.05 !important;}
.talep-row-tag {padding:1px 5px !important;font-size:9.2px !important;line-height:1.35 !important;}
.talep-row-date {padding:1px 5px !important;font-size:9.3px !important;line-height:1.35 !important;}
.talep-row-kpi {padding:1px 6px !important;font-size:9.2px !important;line-height:1.35 !important;}
.talep-row-muted {font-size:10px !important;line-height:1.1 !important;}
.talep-view-help {font-size:10px !important;margin:0 0 3px 0 !important;}
.talep-pagination {font-size:10px !important;margin-top:4px !important;}
.talep-panel-card {padding:10px 12px 9px 12px !important;min-height:132px !important;border-radius:12px !important;box-shadow:0 1px 5px rgba(15,23,42,.04) !important;}
.talep-card-badges {margin-bottom:5px !important;}
.talep-card-title {font-size:12.6px !important;line-height:1.2 !important;margin-bottom:4px !important;-webkit-line-clamp:1 !important;}
.talep-card-desc {font-size:10.4px !important;line-height:1.25 !important;min-height:24px !important;margin-bottom:6px !important;}
.talep-card-price {font-size:13px !important;margin-bottom:6px !important;}
.talep-card-foot {padding-top:5px !important;}
.kpi-row {gap:6px !important;margin-top:8px !important;}
.kpi-item {padding:6px 8px !important;min-height:46px !important;border-radius:10px !important;}
.kpi-value {font-size:13px !important;}
.kpi-label {font-size:9.5px !important;margin-top:2px !important;}
.talep-detail-band {padding:10px 12px !important;margin-bottom:8px !important;border-radius:12px !important;}
.talep-detail-grid {gap:6px !important;}
.talep-detail-item {padding:6px 7px !important;border-radius:9px !important;}
.talep-detail-label {font-size:9px !important;margin-bottom:2px !important;}
.talep-detail-value {font-size:10.5px !important;}
.selected-demand-summary {padding:10px 12px !important;margin-bottom:8px !important;border-radius:12px !important;}
.summary-main {font-size:13.5px !important;margin-bottom:4px !important;}
.summary-sub {font-size:11px !important;}
/* Üst paneldeki butonları sıkılaştır */
div[data-testid="stButton"] > button {
    min-height:28px;
    padding:4px 9px;
    font-size:11px;
}

</style>
""", unsafe_allow_html=True)

# ── Başlık ────────────────────────────────────────────────────────────────────
render_page_header("👤 Taleplerim", f"Talep bazlı portföy karar ve aksiyon merkezi · {user_name}")

# ── Veri ─────────────────────────────────────────────────────────────────────
talep_gruplari = talepleri_kullaniciya_gore_sinifla(user_id, user_name)
talepler = talep_gruplari.get("benim", [])  # geriye dönük uyumluluk (yeni talep formu vb. yerlerde kullanılıyor)
fav_talepler = favori_talepler()
takip_sess = st.session_state.get("takip_listesi", {})
fav_idler = {str(v["id"]) for v in fav_talepler if v.get("id") is not None}
takip_kayitlar = list(fav_talepler)
for k, v in takip_sess.items():
    if str(k) not in fav_idler and "talep" in v.get("_takip_kaynak", ""):
        takip_kayitlar.append(v)

selected_id = st.session_state.get("tm_selected_id")
musteri_map_t = talep_musteri_map()

# ── Render yardımcıları ───────────────────────────────────────────────────────
def render_empty_state(icon, title, desc):
    st.markdown(
        f'''
        <div class="empty-state">
            <div class="empty-state-icon">{htmlesc(icon)}</div>
            <div class="empty-state-title">{htmlesc(title)}</div>
            <div class="empty-state-desc">{htmlesc(desc)}</div>
        </div>
        ''',
        unsafe_allow_html=True,
    )



def render_talep_karti(v, prefix, musteri_map=None):
    kid = str(v.get("id", ""))
    favori = v.get("favori", False)
    secili = str(selected_id or "") == kid
    o = talep_ozeti_olustur(v, musteri_map)
    kart_class = "demand-card-active" if secili else "demand-card"

    c_kart, c_btn, c_fav = st.columns([8.6, 1.05, .72], gap="small")
    with c_kart:
        st.markdown(
            f'''
            <div class="{kart_class}">
                <div class="demand-card-title">{htmlesc(o["ilce"])} · {htmlesc(o["islem"])} · {htmlesc(o["butce"])}</div>
                <div class="demand-card-subtitle">{htmlesc(o["mulk"])} · {htmlesc(o["oda"])} · {htmlesc(o["musteri"])}</div>
                <div class="demand-card-meta">{htmlesc(tarih_str(v))}</div>
            </div>
            ''',
            unsafe_allow_html=True,
        )
    with c_btn:
        st.markdown("<div style='height:7px'></div>", unsafe_allow_html=True)
        if st.button("✓" if secili else "Aç", key=f"{prefix}_sel_{kid}", use_container_width=True):
            st.session_state["tm_selected_id"] = int(kid) if kid.isdigit() else kid
            st.session_state["tm_aktif_sekme"] = "detay"
            st.rerun()
    with c_fav:
        st.markdown("<div style='height:7px'></div>", unsafe_allow_html=True)
        if st.button("★" if favori else "☆", key=f"{prefix}_fav_{kid}"):
            favori_guncelle(int(kid) if kid.isdigit() else kid, favori)


def render_compact_follow_empty():
    st.markdown(
        '<div class="compact-empty">Henüz takipte talep yok. Favoriye aldıkların burada kısa liste olarak görünür.</div>',
        unsafe_allow_html=True,
    )


def render_selected_summary(sel, musteri_map=None):
    o = talep_ozeti_olustur(sel, musteri_map)
    kpi = _eslesme_kpi_hesapla(sel)
    son = kpi["son_arama"] if kpi["son_arama"] != "—" else "Henüz tarama yok"
    st.markdown(
        f'''
        <div class="selected-demand-summary">
            <div class="summary-main">{htmlesc(o["kisa"])}</div>
            <div class="summary-sub">Müşteri: <b>{htmlesc(o["musteri"])}</b> &nbsp;·&nbsp; Son arama: {htmlesc(son)}</div>
            <div class="kpi-row">
                <div class="kpi-item"><div class="kpi-value">{htmlesc(kpi["guclu"])}</div><div class="kpi-label">güçlü eşleşme</div></div>
                <div class="kpi-item"><div class="kpi-value">{htmlesc(kpi["alternatif"])}</div><div class="kpi-label">alternatif portföy</div></div>
                <div class="kpi-item"><div class="kpi-value">{htmlesc(kpi["butce"])}</div><div class="kpi-label">bütçe uyumu</div></div>
                <div class="kpi-item"><div class="kpi-value">{htmlesc(kpi["ilce"])}</div><div class="kpi-label">ilçe uyumu</div></div>
                <div class="kpi-item"><div class="kpi-value">{htmlesc(kpi["son_arama"])}</div><div class="kpi-label">son tarama</div></div>
            </div>
        </div>
        ''',
        unsafe_allow_html=True,
    )


def render_kriter_editor(sel):
    kid = sel.get("id")
    st.markdown('<div class="tm-mini-title">⚙️ Kriterleri Düzenle</div>', unsafe_allow_html=True)
    with st.form(f"tm_kriter_form_{kid}"):
        f1, f2, f3 = st.columns(3)
        with f1:
            yeni_ozet = st.text_input("Özet", value=sel.get("ozet") or sel.get("mail_konusu") or "")
            il_opts = ILLER
            il_val = sel.get("il") if sel.get("il") in il_opts else "İzmir"
            yeni_il = st.selectbox("İl", il_opts, index=il_opts.index(il_val))
        with f2:
            mulk_opts = ["Konut", "İşyeri", "Arsa", "Belirsiz"]
            mulk_val = sel.get("mulk_tipi") if sel.get("mulk_tipi") in mulk_opts else "Belirsiz"
            yeni_mulk = st.selectbox("Mülk Tipi", mulk_opts, index=mulk_opts.index(mulk_val))
            islem_opts = ["Satılık", "Kiralık", "Belirsiz"]
            islem_val = sel.get("islem_tipi") if sel.get("islem_tipi") in islem_opts else "Belirsiz"
            yeni_islem = st.selectbox("İşlem Tipi", islem_opts, index=islem_opts.index(islem_val))
        with f3:
            yeni_butce = st.text_input("Maks. Bütçe", value=sel.get("max_butce") or "")
            yeni_oda = st.text_input("Oda / m²", value=sel.get("oda_sayisi_m2") or "")

        ilce_opts = ["İzmir Genel"] + ilce_sec
        ilce_raw = sel.get("ilce") or ""
        ilce_idx = ilce_opts.index(ilce_raw) if ilce_raw in ilce_opts else 0
        yeni_ilce_sec = st.selectbox("Birincil İlçe", ilce_opts, index=ilce_idx)
        yeni_ilce = "" if yeni_ilce_sec == "İzmir Genel" else yeni_ilce_sec

        mevcut_ilceler = [i for i in (sel.get("ilceler") or []) if i in ilce_sec]
        yeni_ilceler = st.multiselect("Tüm İlçeler", ilce_sec, default=mevcut_ilceler)
        yeni_kriter = st.text_area("Özel Kriterler", value=sel.get("ozel_kriterler") or "", height=80)

        kaydet = st.form_submit_button("💾 Kriterleri Kaydet")
        if kaydet:
            try:
                get_client().table("alici_talepleri").update({
                    "ozet": yeni_ozet,
                    "il": yeni_il,
                    "ilce": yeni_ilce,
                    "ilceler": yeni_ilceler if yeni_ilceler else ([yeni_ilce] if yeni_ilce else []),
                    "mulk_tipi": yeni_mulk,
                    "islem_tipi": yeni_islem,
                    "max_butce": yeni_butce,
                    "oda_sayisi_m2": yeni_oda,
                    "ozel_kriterler": yeni_kriter,
                }).eq("id", kid).execute()
                st.cache_data.clear()
                st.success("Kriterler güncellendi.")
                st.rerun(scope="app")
            except Exception as e:
                st.error(f"Kriterler kaydedilemedi: {e}")



def render_eslesme_karti(sonuc, index=0, talep_kaydi=None):
    p = sonuc.get("portfoy", {}) or {}
    talep_id = (talep_kaydi or {}).get("id", "")
    skor = sonuc.get("skor", "—")
    seviye = sonuc.get("seviye", "")
    bg, fg, brd, seviye_lbl = skor_renkleri(skor, seviye)
    baslik = p.get("baslik") or p.get("ozet") or "Portföy"
    fiyat = fiyat_formatla(p.get("fiyat"))
    ilce = p.get("ilce") or "—"
    oda = p.get("oda_sayisi_m2") or "—"
    kaynak = kaynak_etiketi(p)
    gerekceler = gerekce_badgeleri(sonuc.get("gerekce", ""))
    selected = _is_portfolio_selected(talep_id, sonuc, index)

    # Danışman + tarih — artık _sonuc_serialize_listesi() bu alanları JSON'a
    # dahil ediyor (eskiden hiç yoktu). "Yeniden Tara" yapılmamış, henüz
    # eski/budanmış JSON'a sahip kayıtlarda hâlâ "—" görünebilir.
    danisman_p = isim_ayikla(p.get("talep_eden_danisan", "")) or "—"
    tarih_p_raw = p.get("tarih_ham") or ""
    tarih_p = tarih_sade(tarih_p_raw) if tarih_p_raw else "—"
    ofis_p = ofis_etiketi(p)

    reason_html = "".join([f'<span class="match-reason-badge">{htmlesc(g)}</span>' for g in gerekceler])
    st.markdown(
        f'''
        <div class="match-card">
            <div style="display:grid;grid-template-columns:82px 1fr 132px;gap:14px;align-items:start;">
                <div style="background:{bg};color:{fg};border:1px solid {brd};border-radius:14px;padding:10px 8px;text-align:center;min-height:76px;">
                    <div style="font-size:24px;font-weight:950;line-height:1;">{htmlesc(skor)}</div>
                    <div style="font-size:11px;font-weight:850;margin-top:4px;line-height:1.2;">{htmlesc(seviye_lbl)}</div>
                </div>
                <div>
                    <div class="match-title">{htmlesc(baslik)}</div>
                    <div class="match-meta">{htmlesc(fiyat)} · {htmlesc(ilce)} · {htmlesc(oda)}</div>
                    <div class="match-meta" style="margin-top:2px;color:#94a3b8;">👤 {htmlesc(danisman_p)} · 🏢 {htmlesc(ofis_p)} · 🕐 {htmlesc(tarih_p)}</div>
                    <div style="margin-bottom:4px;margin-top:4px;"><span class="match-source-badge">{htmlesc(kaynak)}</span></div>
                    <div class="match-reason-row">{reason_html}</div>
                </div>
                <div></div>
            </div>
        </div>
        ''',
        unsafe_allow_html=True,
    )

    a1, a2, a3 = st.columns([1, 1, 1], gap="small")
    with a1:
        if p.get("ilan_linki"):
            st.link_button("İlan Aç", p["ilan_linki"], use_container_width=True)
        elif p.get("id"):
            # ÖNEMLİ DÜZELTME: Eskiden sadece portfoy_gorunurluk="kapali_portfoy"/
            # "kapali_adayi" olan kayıtlar satır içi "Detay" ile açılıyordu;
            # diğer tüm kayıtlar (örn. "teyit_gerekli" — Portföy Havuzu
            # taramasından gelenler) Portföylerim sayfasına YÖNLENDİRİYORDU.
            # Artık ilan_linki olmayan HER kayıt Taleplerim sayfasından
            # ayrılmadan, satır içi açılıyor.
            detay_key = f"tm_esleme_detay_acik_{index}_{p['id']}"
            detay_acik = st.session_state.get(detay_key, False)
            if st.button("✕ Kapat" if detay_acik else "Detay", key=f"tm_esleme_detay_btn_{index}_{p['id']}",
                         use_container_width=True, type="primary" if detay_acik else "secondary"):
                st.session_state[detay_key] = not detay_acik
        else:
            st.button("İlan Aç", key=f"tm_no_link_{index}", disabled=True, use_container_width=True)
    with a2:
        if st.button("✓ Seçildi" if selected else "Seç", key=f"tm_select_match_{talep_id}_{index}", use_container_width=True,
                     type="primary" if selected else "secondary"):
            _toggle_selected_portfolio(talep_id, sonuc, index)
            st.rerun(scope="app")
    with a3:
        note_toggle_key = f"tm_match_note_open_{talep_id}_{index}"
        not_acik = st.session_state.get(note_toggle_key, False)
        if st.button("✕ Kapat" if not_acik else "Not", key=f"tm_note_match_{talep_id}_{index}",
                     use_container_width=True, type="primary" if not_acik else "secondary"):
            st.session_state[note_toggle_key] = not not_acik

    st.markdown('<div class="match-action-note">Portföyü müşteriye göndermek için önce “Seç” ile gönderim paketine ekleyin.</div>', unsafe_allow_html=True)

    # ÖNEMLİ DÜZELTME: Detay paneli artık görünürlük tipine bakmaksızın,
    # id'si olan her portföy için açılabiliyor (eskiden sadece kapalı
    # portföy/kapalı adaylarda gösteriliyordu).
    if p.get("id"):
        detay_key = f"tm_esleme_detay_acik_{index}_{p['id']}"
        if st.session_state.get(detay_key, False):
            tam_kayit = next((v for v in _tum_portfoyler_esleme_icin() if str(v.get("id")) == str(p["id"])), None)
            if not tam_kayit:
                st.caption("Kayıt bulunamadı — silinmiş veya güncellenmiş olabilir.")
            else:
                tam_tarih_raw = (
                    tam_kayit.get("ilan_tarihi") or tam_kayit.get("mail_tarihi")
                    or tam_kayit.get("paylasim_tarihi") or tam_kayit.get("kayit_tarihi")
                    or tam_kayit.get("olusturma_tarihi") or ""
                )
                tam_tarih = tarih_sade(tam_tarih_raw) if tam_tarih_raw else "—"
                st.markdown(
                    f'''
                    <div class="soft-note">
                        <b>Danışman:</b> {htmlesc(tam_kayit.get("talep_eden_danisan") or "—")}<br>
                        <b>Ofis:</b> {htmlesc(ofis_etiketi(tam_kayit))}<br>
                        <b>Tarih:</b> {htmlesc(tam_tarih)}<br>
                        <b>Özet:</b> {htmlesc(tam_kayit.get("ozet") or "—")}<br>
                        <b>Özellikler:</b> {htmlesc(tam_kayit.get("ozellikler") or "—")}<br>
                        <b>Oda/m²:</b> {htmlesc(tam_kayit.get("oda_sayisi_m2") or "—")}<br>
                        <b>İşlem/Mülk:</b> {htmlesc(tam_kayit.get("islem_tipi") or "—")} · {htmlesc(tam_kayit.get("mulk_tipi") or "—")}
                    </div>
                    ''',
                    unsafe_allow_html=True,
                )
                tam_mail_icerik = tam_kayit.get("mail_icerigi") or ""
                if tam_mail_icerik:
                    with st.expander("📧 Mail İçeriği"):
                        st.text(_mail_metni_temizle(str(tam_mail_icerik))[:2000])

    if st.session_state.get(note_toggle_key):
        note_text = st.text_area("Eşleşme notu", key=f"tm_match_note_text_{talep_id}_{index}", height=70,
                                 placeholder="Bu portföyle ilgili kısa not...")
        nb1, nb2 = st.columns([1, 4])
        with nb1:
            if st.button("Kaydet", key=f"tm_match_note_save_{talep_id}_{index}", use_container_width=True):
                if note_text.strip() and talep_id:
                    try:
                        eski_not = (talep_kaydi or {}).get("not_alani") or ""
                        ek = f"[{datetime.now().strftime('%d.%m.%Y %H:%M')}] {baslik}: {note_text.strip()}"
                        yeni_not = (eski_not + "\n\n" + ek).strip() if eski_not else ek
                        get_client().table("alici_talepleri").update({"not_alani": yeni_not}).eq("id", talep_id).execute()
                        st.cache_data.clear()
                        st.session_state[note_toggle_key] = False
                        st.success("Not eklendi.")
                        st.rerun(scope="app")
                    except Exception as e:
                        st.error(f"Not kaydedilemedi: {e}")
                else:
                    st.warning("Not yazın.")


def _esleme_satiri_ciz(sonuc, index=0, talep_kaydi=None):
    """Eski çağrılar bozulmasın diye fonksiyon adı korunur."""
    render_eslesme_karti(sonuc, index=index, talep_kaydi=talep_kaydi)


def render_eslesmeler_panel(sel):
    kid = sel.get("id")
    session_key = f"tm_esleme_sonuc_{kid}"
    tarih_key = f"tm_esleme_tarih_{kid}"

    kayitli = st.session_state.get(session_key)
    if kayitli is None:
        kayitli = normalize_eslesme_sonuclari(sel.get("son_eslesme_json"))

    tarih_label = st.session_state.get(tarih_key)
    if not tarih_label:
        tarih_label = tarih_sade(sel.get("son_eslesme_tarihi")) if sel.get("son_eslesme_tarihi") else "—"

    st.markdown(f'<div class="tm-mini-title">🎯 Eşleşen Portföyler <span style="font-weight:600;color:#94a3b8;">· Son arama: {htmlesc(tarih_label)}</span></div>', unsafe_allow_html=True)

    if not kayitli:
        render_empty_state("⌕", "Uygun portföy bulunamadı.", "Kriterleri gevşeterek yeniden arama yapabilir veya portföy havuzunu daha sonra tekrar tarayabilirsin.")
        if st.button("🔄 Şimdi Tara", key=f"tm_esleme_ilk_ara_{kid}", use_container_width=False):
            with st.spinner("Eşleşen portföyler aranıyor..."):
                yeni = _esleme_ara_ve_kaydet(sel, kid)
                st.session_state[session_key] = yeni
                st.session_state[tarih_key] = "az önce"
                st.cache_data.clear()
                st.rerun()
        return

    for i, sonuc in enumerate(kayitli):
        render_eslesme_karti(sonuc, index=i, talep_kaydi=sel)

    st.caption("ℹ️ Skorlar ön değerlendirmedir. Müşteriye sunmadan önce portföyü mutlaka kontrol edin.")


def render_talep_detayi_panel(sel):
    kid = sel.get("id")
    ozet = sel.get("ozet") or sel.get("mail_konusu") or "—"
    islem = sel.get("islem_tipi", "") or "—"
    mulk = sel.get("mulk_tipi", "") or "—"
    il = sel.get("il", "") or "—"
    ilce = ilce_grubu(sel)
    bolge = sel.get("bolge_mahalle", "") or sel.get("bolge", "") or "—"
    oda = sel.get("oda_sayisi_m2", "") or "—"
    butce = fiyat_formatla(sel.get("max_butce"))
    kriterler = sel.get("ozel_kriterler", "") or "—"
    gd_isim = isim_ayikla(sel.get("giren_gd", "")) or isim_ayikla(sel.get("talep_eden_danisan", "")) or "—"
    favori = sel.get("favori", False)
    tip_bg, tip_fg, tip_lbl = tip_badge(islem)

    st.markdown(
        f'''
        <div style="background:#fff;border:1px solid #e2e8f0;border-radius:14px;padding:16px 18px;margin-bottom:12px;">
            <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:8px;">
                <div style="font-size:15px;font-weight:850;color:#172B4D;line-height:1.45;">{htmlesc(ozet)}</div>
                <span style="background:{tip_bg};color:{tip_fg};padding:4px 10px;border-radius:999px;font-size:11px;font-weight:800;white-space:nowrap;">{htmlesc(tip_lbl)}</span>
            </div>
        </div>
        ''',
        unsafe_allow_html=True,
    )

    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f'<p class="dp-label">Mülk Tipi</p><p class="dp-value">{htmlesc(mulk)}</p>', unsafe_allow_html=True)
        st.markdown(f'<p class="dp-label">İl / İlçe</p><p class="dp-value">{htmlesc(il)} / {htmlesc(ilce)}</p>', unsafe_allow_html=True)
        st.markdown(f'<p class="dp-label">Bölge</p><p class="dp-value">{htmlesc(bolge)}</p>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<p class="dp-label">Oda / m²</p><p class="dp-value">{htmlesc(oda)}</p>', unsafe_allow_html=True)
        st.markdown(f'<p class="dp-label">Maks. Bütçe</p><p class="dp-value" style="font-size:15px;color:#172B4D;">{htmlesc(butce)}</p>', unsafe_allow_html=True)
        st.markdown(f'<p class="dp-label">Danışman</p><p class="dp-value">{htmlesc(gd_isim)}</p>', unsafe_allow_html=True)

    if kriterler and kriterler != "—":
        st.markdown('<hr class="dp-divider">', unsafe_allow_html=True)
        st.markdown(f'<p class="dp-label">Özel Kriterler</p><p class="dp-value">{htmlesc(kriterler)}</p>', unsafe_allow_html=True)

    mail_icerik = sel.get("mail_icerigi", "")
    if mail_icerik:
        with st.expander("📧 Mail İçeriği"):
            st.text(_mail_metni_temizle(str(mail_icerik))[:2000])

    st.markdown('<hr class="dp-divider">', unsafe_allow_html=True)
    ab1, ab2 = st.columns([1, 1])
    with ab1:
        if st.button("★ Favoride" if favori else "☆ Favoriye Al", key=f"dp_fav_{kid}", use_container_width=True):
            favori_guncelle(kid, favori)
    with ab2:
        if st.button("✖ Seçimi Kapat", key=f"dp_kapat_{kid}", use_container_width=True):
            st.session_state.pop("tm_selected_id", None)
            st.session_state["tm_aktif_sekme"] = "bos"
            st.rerun(scope="app")


def render_musteri_panel(sel):
    kid = sel.get("id")
    musteriler = musteri_cek_talep(kid)
    musteri_form_key = f"tm_mf_{kid}"

    st.markdown('<div class="tm-mini-title">👤 Müşteri Bilgisi</div>', unsafe_allow_html=True)

    if musteriler:
        for m in musteriler:
            ad = m.get("musteri_adi", "") or "—"
            tel = m.get("telefon", "") or "—"
            initials = "".join(w[0].upper() for w in ad.split()[:2]) if ad != "—" else "?"
            st.markdown(
                f'''
                <div style="display:flex;align-items:center;gap:10px;padding:10px 12px;background:#F8FAFC;border-radius:12px;margin-bottom:8px;border:1px solid #e2e8f0;">
                    <div style="width:34px;height:34px;border-radius:50%;background:#EEF4FA;display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:800;color:#355C7D;flex-shrink:0;">{htmlesc(initials)}</div>
                    <div style="flex:1;">
                        <div style="font-size:13px;font-weight:800;color:#172B4D;">{htmlesc(ad)}</div>
                        <div style="font-size:11.5px;color:#64748b;">{htmlesc(tel)}</div>
                    </div>
                </div>
                ''',
                unsafe_allow_html=True,
            )
    else:
        render_empty_state("👤", "Bu talebe bağlı müşteri yok.", "Müşteri adı ve telefonu eklendiğinde seçili talep özetinde de görünecek.")

    if st.session_state.get(musteri_form_key, False):
        mc1, mc2, mc3 = st.columns([3, 3, 1])
        with mc1:
            yeni_ad = st.text_input("Müşteri adı", placeholder="Ad Soyad", key=f"tm_mad_{kid}")
        with mc2:
            yeni_tel = st.text_input("Telefon", placeholder="05xx xxx xx xx", key=f"tm_mtel_{kid}")
        with mc3:
            st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
            if st.button("💾", key=f"tm_mkyd_{kid}", use_container_width=True):
                if yeni_ad.strip():
                    try:
                        get_client().table("musteriler").insert({
                            "talep_id": str(kid),
                            "musteri_adi": yeni_ad.strip(),
                            "telefon": yeni_tel.strip(),
                            "ekleyen": user_name,
                            "danisan_id": user_name,
                        }).execute()
                        st.cache_data.clear()
                        st.session_state[musteri_form_key] = False
                        st.success("Müşteri eklendi!")
                        st.rerun(scope="app")
                    except Exception as e:
                        st.error(f"Hata: {e}")
                else:
                    st.warning("Ad girin.")
        if st.button("İptal", key=f"tm_miptl_{kid}"):
            st.session_state[musteri_form_key] = False
            st.rerun(scope="app")
    else:
        if st.button("+ Müşteri Ekle", key=f"tm_mekle_{kid}"):
            st.session_state[musteri_form_key] = True
            st.rerun(scope="app")


def render_notlar_panel(sel):
    kid = sel.get("id")
    not_a = sel.get("not_alani", "") or ""
    st.markdown('<div class="tm-mini-title">📝 Talep Notları</div>', unsafe_allow_html=True)
    yeni_not = st.text_area("Notum", value=not_a, key=f"not_{kid}", height=170, placeholder="Bu talep hakkında notlarınız...")
    n1, n2 = st.columns([1, 4])
    with n1:
        if st.button("💾 Kaydet", key=f"not_kyd_{kid}", use_container_width=True):
            try:
                get_client().table("alici_talepleri").update({"not_alani": yeni_not}).eq("id", kid).execute()
                st.cache_data.clear()
                st.success("Not kaydedildi.")
                st.rerun(scope="app")
            except Exception as e:
                st.error(f"Hata: {e}")



def render_top_actions(sel):
    kid = sel.get("id")
    a1, a2 = st.columns([1, 1.15], gap="small")
    with a1:
        if st.button("🔄 Yeniden Tara", key=f"tm_top_yeniden_tara_{kid}", use_container_width=True):
            with st.spinner("Eşleşen portföyler aranıyor..."):
                yeni = _esleme_ara_ve_kaydet(sel, kid)
                st.session_state[f"tm_esleme_sonuc_{kid}"] = yeni
                st.session_state[f"tm_esleme_tarih_{kid}"] = "az önce"
                st.session_state[f"tm_tab_{kid}"] = "🎯 Eşleşmeler"
                st.cache_data.clear()
                st.rerun()
    with a2:
        if st.button("⚙️ Kriterleri Düzenle", key=f"tm_top_kriter_{kid}", use_container_width=True):
            st.session_state[f"tm_kriter_editor_{kid}"] = not st.session_state.get(f"tm_kriter_editor_{kid}", False)

    if st.session_state.get(f"tm_kriter_editor_{kid}", False):
        render_kriter_editor(sel)




def render_talep_detay_band(sel):
    """Seçili talebi, eşleşmelerin üstünde tam sayfa karar bandı olarak gösterir."""
    o = talep_ozeti_olustur(sel, musteri_map_t)
    il = sel.get("il", "") or "—"
    ilce = ilce_grubu(sel)
    bolge = sel.get("bolge_mahalle", "") or sel.get("bolge", "") or sel.get("mahalle", "") or "—"
    mulk = sel.get("mulk_tipi", "") or "—"
    islem = sel.get("islem_tipi", "") or "—"
    oda = sel.get("oda_sayisi_m2", "") or "—"
    butce = fiyat_formatla(sel.get("max_butce"))
    kriterler = sel.get("ozel_kriterler", "") or ""
    kriter_html = ("<br><b>Özel kriter:</b> " + htmlesc(kriterler)) if kriterler else ""

    st.markdown(
        f"""
        <div class="talep-detail-band">
            <div class="talep-detail-band-title">📌 Talep Başlığı ve Kriter Özeti</div>
            <div class="talep-detail-grid">
                <div class="talep-detail-item"><div class="talep-detail-label">Müşteri</div><div class="talep-detail-value">{htmlesc(o["musteri"])}</div></div>
                <div class="talep-detail-item"><div class="talep-detail-label">İşlem</div><div class="talep-detail-value">{htmlesc(islem)}</div></div>
                <div class="talep-detail-item"><div class="talep-detail-label">Mülk</div><div class="talep-detail-value">{htmlesc(mulk)}</div></div>
                <div class="talep-detail-item"><div class="talep-detail-label">Bölge</div><div class="talep-detail-value">{htmlesc(il)} / {htmlesc(ilce)}</div></div>
                <div class="talep-detail-item"><div class="talep-detail-label">Bütçe</div><div class="talep-detail-value">{htmlesc(butce)}</div></div>
                <div class="talep-detail-item"><div class="talep-detail-label">Oda / m²</div><div class="talep-detail-value">{htmlesc(oda)}</div></div>
            </div>
            <div class="talep-detail-note"><b>Bölge/Mahalle:</b> {htmlesc(bolge)}{kriter_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )



def _dedupe_talepler(liste):
    sonuc, goruldu = [], set()
    for v in liste or []:
        kid = str(v.get("id", ""))
        if kid and kid not in goruldu:
            sonuc.append(v)
            goruldu.add(kid)
    return sonuc


def _talep_panel_age_days(v):
    d = tarih_parse(en_iyi_tarih(v))
    if not d:
        return 9999
    try:
        return max(0, (datetime.now().date() - d.date()).days)
    except Exception:
        return 9999


def _talep_panel_date_badge(v):
    d = tarih_parse(en_iyi_tarih(v))
    if not d:
        return "—", "#64748b", "#f8fafc"
    has_t = hasattr(d, "hour") and (d.hour != 0 or d.minute != 0)
    label = d.strftime("%d.%m %H:%M") if has_t else d.strftime("%d.%m.%Y")
    gun = _talep_panel_age_days(v)
    if gun <= 7:
        return label, "#166534", "#dcfce7"
    if gun <= 30:
        return label, "#713f12", "#fef9c3"
    if gun <= 90:
        return label, "#7c2d12", "#ffedd5"
    return label, "#64748b", "#f1f5f9"


def _talep_panel_ui_model(v, musteri_map=None):
    """Talep Tablosu'ndaki hiyerarşiyi Taleplerim üst paneline uyarlar."""
    kid = str(v.get("id", ""))
    musteri = (musteri_map or {}).get(kid, "") or v.get("musteri_adi", "") or "—"
    danisman = isim_ayikla(v.get("talep_eden_danisan", "")) or "—"
    ilce = ilce_grubu(v)
    islem = v.get("islem_tipi") or "—"
    mulk = v.get("mulk_tipi") or "—"
    oda = v.get("oda_sayisi_m2") or "—"
    butce = fiyat_formatla(v.get("max_butce"))
    bolge = v.get("mahalle") or v.get("bolge") or v.get("bolge_mahalle") or ""
    kriter = v.get("ozel_kriterler") or v.get("ozet") or v.get("mail_konusu") or ""

    baslik_parts = []
    if islem and islem != "—":
        baslik_parts.append(islem)
    if oda and oda != "—":
        baslik_parts.append(oda)
    if mulk and mulk != "—":
        baslik_parts.append(mulk)
    baslik = " ".join(baslik_parts).strip()
    if baslik:
        baslik = f"{baslik} Arayışı"
    else:
        baslik = str(kriter or "Gayrimenkul Talebi")[:80]

    desc_parts = []
    if danisman and danisman != "—":
        desc_parts.append(f"👤 {danisman}")
    if bolge:
        desc_parts.append(str(bolge))
    if kriter and str(kriter) != baslik:
        desc_parts.append(str(kriter)[:70])
    desc = " · ".join(desc_parts) or f"{mulk} · {oda} · {musteri}"

    return {
        "kid": kid,
        "musteri": musteri,
        "danisman": danisman,
        "ilce": ilce,
        "islem": islem,
        "mulk": mulk,
        "oda": oda,
        "butce": butce,
        "baslik": baslik,
        "desc": desc,
    }


def _talep_panel_status(v):
    son = normalize_eslesme_sonuclari(v.get("son_eslesme_json"))
    guclu = 0
    for s in son:
        try:
            if int(s.get("skor") or 0) >= 80:
                guclu += 1
        except Exception:
            pass
    if guclu:
        return f"{guclu} güçlü", "#166534", "#dcfce7"
    if son:
        return f"{len(son)} eşleşme", "#355C7D", "#EEF4FA"
    return "tarama yok", "#64748b", "#f8fafc"


def _tip_tag_style(islem):
    islem_l = str(islem or "").lower().replace("ı", "i")
    if "kiralik" in islem_l:
        return "Kiralık", "#166534", "#f0fdf4"
    if "satilik" in islem_l:
        return "Satılık", "#991b1b", "#fef2f2"
    return islem or "—", "#64748b", "#f8fafc"


def _kaynak_tag_style(v):
    """2_Talep_Tablosu.py'deki kaynak rozeti mantığının aynısı — Startkey /
    Zeta / Diğer ayrımını gösterir."""
    kaynak_raw = (v.get("kaynak") or "").lower().strip()
    if kaynak_raw in ("startkey_mail", ""):
        return "Startkey", "#355C7D", "#EEF4FA"
    if kaynak_raw in ("zeta1", "zeta2", "ofis", "zeta"):
        return "Zeta", "#0F6E56", "#E1F5EE"
    if kaynak_raw == "dis_kaynak":
        return "Köprü", "#92400e", "#fef3c7"
    return "Diğer", "#475569", "#f1f5f9"


# Bir talep listede birden fazla bölümde (örn. hem Takip Listem hem Benim
# Taleplerim) görünebilir. Seçili kayıt her ikisinde de render edilmeye
# çalışılırsa aynı widget key'leri çakışır. Bu flag, seçili panelin script
# çalıştırması başına sadece BİR kez (ilk karşılaşıldığı bölümde) açılmasını
# garanti eder. Modül seviyesinde tanımlı olduğu için her Streamlit rerun'ında
# (sayfa yeniden çalıştırıldığında) otomatik sıfırlanır.
_panel_render_flag = {"acildi": False}


# Zeta/Köprü bölümleri varsayılan kapalı (performans için). Bu bölümlerden
# birindeki bir kayda "Aç" denince, panelin görünebilmesi için ilgili
# toggle'ı da otomatik açık hale getiriyoruz — aksi halde "Aç"a basılsa bile
# bölüm kapalı kaldığı için panel hiç render edilmez, kafa karıştırıcı olur.
_PREFIX_TO_TOGGLE_KEY = {
    "ust_zeta": "tm_zeta_talepleri_acik",
    "ust_kopru": "tm_kopru_talepler_acik",
}


def _panel_toggle_ac(prefix):
    _toggle_key = _PREFIX_TO_TOGGLE_KEY.get(prefix)
    if _toggle_key:
        st.session_state[_toggle_key] = True


def _page_slice(liste, key, per_page):
    total = len(liste)
    total_pages = max(1, (total + per_page - 1) // per_page)
    page = int(st.session_state.get(key, 1) or 1)
    if page < 1 or page > total_pages:
        page = 1
        st.session_state[key] = 1
    start = (page - 1) * per_page
    return liste[start:start + per_page], page, total_pages, start


def _render_pagination_controls(key, page, total_pages, total, start, per_page, label_suffix=""):
    if total_pages <= 1:
        st.markdown(
            f'<div class="talep-pagination">Gösterilen: {1 if total else 0}-{total} / {total} talep{label_suffix}</div>',
            unsafe_allow_html=True,
        )
        return

    p1, p2, p3, p4 = st.columns([.75, 1.35, .75, 5.2], gap="small")
    with p1:
        if st.button("‹ Önceki", key=f"{key}_prev", use_container_width=True, disabled=page <= 1):
            st.session_state[key] = max(1, page - 1)
            st.rerun()
    with p2:
        yeni_page = st.selectbox(
            "Sayfa",
            list(range(1, total_pages + 1)),
            index=page - 1,
            key=f"{key}_select",
            label_visibility="collapsed",
        )
        if int(yeni_page) != page:
            st.session_state[key] = int(yeni_page)
            st.rerun()
    with p3:
        if st.button("Sonraki ›", key=f"{key}_next", use_container_width=True, disabled=page >= total_pages):
            st.session_state[key] = min(total_pages, page + 1)
            st.rerun()
    with p4:
        st.markdown(
            f'<div class="talep-pagination">Gösterilen: {start + 1}-{min(start + per_page, total)} / {total} talep · Sayfa {page}/{total_pages}{label_suffix}</div>',
            unsafe_allow_html=True,
        )


def render_talep_liste_view(liste, prefix, musteri_map=None):
    """Kompakt liste görünümü: maksimum 5 satır + sayfalama.
    Önceki sürümde HTML satırı ve Streamlit buton satırı ayrı üretildiği için satır araları büyüyordu.
    Bu sürüm hücreleri ve aksiyon butonlarını aynı columns satırında çizer."""
    per_page = 5
    page_key = f"tm_panel_liste_page_{prefix}"
    page_items, page, total_pages, start = _page_slice(liste, page_key, per_page)

    st.markdown(
        """
        <div class="talep-panel-compact-head">
            <div>İlçe</div><div>İşlem</div><div>Kaynak</div><div>Talep</div><div>Bütçe</div><div>Müşteri</div><div>Tarih</div><div>Durum</div><div></div><div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    for idx, v in enumerate(page_items):
        kid = str(v.get("id", ""))
        ui = _talep_panel_ui_model(v, musteri_map)
        secili = str(selected_id or "") == kid
        favori = v.get("favori", False)
        tip_lbl, tip_fg, tip_bg = _tip_tag_style(ui["islem"])
        kaynak_lbl, kaynak_fg, kaynak_bg = _kaynak_tag_style(v)
        tarih_lbl, tarih_fg, tarih_bg = _talep_panel_date_badge(v)
        durum_lbl, durum_fg, durum_bg = _talep_panel_status(v)
        row_bg = "#EEF4FA" if idx % 2 == 1 else "#ffffff"

        row_cols = st.columns([1.0, .7, .65, 2.15, 1.1, 1.0, .9, .75, .5, .38], gap="small")
        active_wrap_open = '<div class="talep-list-row-active-marker">' if secili else ''
        active_wrap_close = '</div>' if secili else ''

        with row_cols[0]:
            st.markdown(
                f'<div class="talep-compact-cell" style="background:{row_bg};">{active_wrap_open}<span class="talep-compact-tag" style="background:#EEF4FA;color:#355C7D;">{htmlesc(ui["ilce"])}</span>{active_wrap_close}</div>',
                unsafe_allow_html=True,
            )
        with row_cols[1]:
            st.markdown(
                f'<div class="talep-compact-cell" style="background:{row_bg};"><span class="talep-compact-tag" style="background:{tip_bg};color:{tip_fg};">{htmlesc(tip_lbl)}</span></div>',
                unsafe_allow_html=True,
            )
        with row_cols[2]:
            st.markdown(
                f'<div class="talep-compact-cell" style="background:{row_bg};"><span class="talep-compact-tag" style="background:{kaynak_bg};color:{kaynak_fg};">{htmlesc(kaynak_lbl)}</span></div>',
                unsafe_allow_html=True,
            )
        with row_cols[3]:
            st.markdown(
                f'<div class="talep-compact-cell" style="display:block;padding-top:4px;background:{row_bg};"><span class="talep-compact-title">{htmlesc(ui["baslik"])}</span><span class="talep-compact-desc">{htmlesc(ui["desc"])}</span></div>',
                unsafe_allow_html=True,
            )
        with row_cols[4]:
            st.markdown(f'<div class="talep-compact-cell" style="background:{row_bg};"><span class="talep-compact-price">{htmlesc(ui["butce"])}</span></div>', unsafe_allow_html=True)
        with row_cols[5]:
            st.markdown(f'<div class="talep-compact-cell" style="background:{row_bg};"><span class="talep-compact-muted">{htmlesc(ui["musteri"])}</span></div>', unsafe_allow_html=True)
        with row_cols[6]:
            st.markdown(f'<div class="talep-compact-cell" style="background:{row_bg};"><span class="talep-compact-date" style="background:{tarih_bg};color:{tarih_fg};">{htmlesc(tarih_lbl)}</span></div>', unsafe_allow_html=True)
        with row_cols[7]:
            st.markdown(f'<div class="talep-compact-cell" style="background:{row_bg};"><span class="talep-compact-kpi" style="background:{durum_bg};color:{durum_fg};">{htmlesc(durum_lbl)}</span></div>', unsafe_allow_html=True)
        with row_cols[8]:
            if st.button("✕" if secili else "Aç", key=f"{prefix}_liste_open_{kid}_{idx}", use_container_width=True,
                         type="primary" if secili else "secondary",
                         help="Kapat" if secili else "Talebi aç"):
                if secili:
                    st.session_state["tm_selected_id"] = None
                else:
                    st.session_state["tm_selected_id"] = int(kid) if kid.isdigit() else kid
                    st.session_state["tm_aktif_sekme"] = "bos"
                    st.session_state[f"tm_tab_{kid}"] = "🎯 Eşleşmeler"
                    _panel_toggle_ac(prefix)
                st.rerun()
        with row_cols[9]:
            if st.button("★" if favori else "☆", key=f"{prefix}_liste_fav_{kid}_{idx}", use_container_width=True):
                favori_guncelle(int(kid) if kid.isdigit() else kid, favori)

        if idx < len(page_items) - 1:
            st.markdown('<div class="talep-compact-row-sep"></div>', unsafe_allow_html=True)

        # ── Satır altı çalışma paneli ────────────────────────────────────────
        # Önceki sürümde seçili talebin detay/eşleşme paneli sayfanın en
        # altında, listeden ayrı bir yerde açılıyordu. Artık seçili satırın
        # HEMEN ALTINDA açılıyor — bağlam kaybı olmuyor, hangi talebe
        # baktığını kaydırmadan görebiliyorsun.
        if secili and not _panel_render_flag["acildi"]:
            _panel_render_flag["acildi"] = True
            st.markdown('<div class="talep-inline-panel-wrap">', unsafe_allow_html=True)
            render_talep_calisma_panel(v, musteri_map)
            st.markdown('</div>', unsafe_allow_html=True)

    _render_pagination_controls(page_key, page, total_pages, len(liste), start, per_page, " · Liste görünümünde maksimum 5 satır")

def render_talep_card_view(liste, prefix, musteri_map=None):
    """Kart görünümü: Talep Tablosu'ndaki 2 kolonlu kart hiyerarşisini üst panele uyarlar."""
    per_page = 6
    page_key = f"tm_panel_kart_page_{prefix}"
    page_items, page, total_pages, start = _page_slice(liste, page_key, per_page)

    for row_start in range(0, len(page_items), 2):
        cols = st.columns(2, gap="medium")
        for i, item in enumerate(page_items[row_start:row_start + 2]):
            with cols[i]:
                kid = str(item.get("id", ""))
                ui = _talep_panel_ui_model(item, musteri_map)
                secili = str(selected_id or "") == kid
                favori = item.get("favori", False)
                tip_lbl, tip_fg, tip_bg = _tip_tag_style(ui["islem"])
                kaynak_lbl, kaynak_fg, kaynak_bg = _kaynak_tag_style(item)
                tarih_lbl, tarih_fg, tarih_bg = _talep_panel_date_badge(item)
                durum_lbl, durum_fg, durum_bg = _talep_panel_status(item)
                card_cls = "talep-panel-card talep-panel-card-active" if secili else "talep-panel-card"
                st.markdown(
                    f"""
                    <div class="{card_cls}">
                        <div class="talep-card-badges">
                            <div>
                                <span class="talep-row-tag" style="background:#EEF4FA;color:#355C7D;">{htmlesc(ui["ilce"])}</span>
                                <span class="talep-row-tag" style="background:{tip_bg};color:{tip_fg};">{htmlesc(tip_lbl)}</span>
                                <span class="talep-row-tag" style="background:{kaynak_bg};color:{kaynak_fg};">{htmlesc(kaynak_lbl)}</span>
                            </div>
                            <span class="talep-row-kpi" style="background:{durum_bg};color:{durum_fg};">{htmlesc(durum_lbl)}</span>
                        </div>
                        <div class="talep-card-title">{htmlesc(ui["baslik"])}</div>
                        <div class="talep-card-desc">{htmlesc(ui["desc"])}</div>
                        <div class="talep-card-price">{htmlesc(ui["butce"])}</div>
                        <div class="talep-card-foot">
                            <span class="talep-row-muted">{htmlesc(ui["musteri"])} · <span style="background:{tarih_bg};color:{tarih_fg};padding:2px 6px;border-radius:5px;font-weight:700;">{htmlesc(tarih_lbl)}</span></span>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                c1, c2 = st.columns([4, 1], gap="small")
                with c1:
                    if st.button("✕ Kapat" if secili else "Talebi Aç", key=f"{prefix}_kart_open_{kid}", use_container_width=True, type="primary" if secili else "secondary"):
                        if secili:
                            st.session_state["tm_selected_id"] = None
                        else:
                            st.session_state["tm_selected_id"] = int(kid) if kid.isdigit() else kid
                            st.session_state["tm_aktif_sekme"] = "bos"
                            st.session_state[f"tm_tab_{kid}"] = "🎯 Eşleşmeler"
                            _panel_toggle_ac(prefix)
                        st.rerun()
                with c2:
                    if st.button("★" if favori else "☆", key=f"{prefix}_kart_fav_{kid}", use_container_width=True):
                        favori_guncelle(int(kid) if kid.isdigit() else kid, favori)

        # ── Satır altı çalışma paneli ────────────────────────────────────────
        # 2 kartlık grup render edildikten sonra, o gruptaki kartlardan biri
        # seçiliyse panel tam genişlikte (2 kartın altında) açılır — dar bir
        # kart sütununa sıkışmasın diye kart döngüsünün dışında render edilir.
        for item in page_items[row_start:row_start + 2]:
            kid = str(item.get("id", ""))
            if str(selected_id or "") == kid and not _panel_render_flag["acildi"]:
                _panel_render_flag["acildi"] = True
                st.markdown('<div class="talep-inline-panel-wrap">', unsafe_allow_html=True)
                render_talep_calisma_panel(item, musteri_map)
                st.markdown('</div>', unsafe_allow_html=True)

    _render_pagination_controls(page_key, page, total_pages, len(liste), start, per_page, " · Kart görünümü 2 kolonlu hiyerarşi")


def render_talep_ust_paneli(talep_gruplari, takip_kayitlar, musteri_map=None):
    """
    portfoylerím.py'deki KPI kartı + bölüm modelinin talep tarafı karşılığı.

    talep_gruplari: {"benim": [...], "zeta": [...], "kopru": [...]}
    (bkz. talepleri_kullaniciya_gore_sinifla())

    Yerleşim:
      - Takip Listem (varsa) — en üstte, her zaman açık
      - Benim Taleplerim — her zaman açık (ana çalışma listesi)
      - Zeta Talepleri — varsayılan kapalı, buton ile açılır (performans için)
      - Köprü Talepler — varsayılan kapalı, buton ile açılır
    """
    benim = talep_gruplari.get("benim", []) or []
    zeta = talep_gruplari.get("zeta", []) or []
    kopru = talep_gruplari.get("kopru", []) or []
    takip_kayitlar = takip_kayitlar or []

    st.markdown(
        """
        <div class="compact-panel-title">
            <div>📋 Talep Paneli</div>
            <span>Liste: 5 satır · Kart: sayfalı görünüm · Seçilen talep aşağıda tam sayfa açılır</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── KPI ÖZETİ ─────────────────────────────────────────────────────────────
    m1, m2, m3, m4, m5 = st.columns(5)
    with m1:
        st.metric("Benim Taleplerim", len(benim))
    with m2:
        st.metric("Zeta Talepleri", len(zeta))
    with m3:
        st.metric("Köprü Talepler", len(kopru))
    with m4:
        st.metric("Takip", len(takip_kayitlar))
    with m5:
        st.write("")
        if st.button("＋ Yeni Talep", key="btn_yeni_talep_top", use_container_width=True, type="primary"):
            st.session_state["tm_aktif_sekme"] = "yeni_talep"
            st.session_state.pop("tm_selected_id", None)
            st.rerun()

    gorunum = st.radio(
        "Görünüm", ["Liste", "Kart"], horizontal=True, key="tm_panel_gorunum", label_visibility="collapsed"
    )

    def _bolum_goster(liste, prefix):
        if gorunum == "Liste":
            render_talep_liste_view(liste, prefix, musteri_map)
        else:
            render_talep_card_view(liste, prefix, musteri_map)

    # ── TAKİP LİSTEM (varsa, en üstte, her zaman açık) ─────────────────────────
    if takip_kayitlar:
        st.markdown('<div class="compact-toolbar-note">⭐ Takip Listem</div>', unsafe_allow_html=True)
        _bolum_goster(takip_kayitlar, "ust_takip")

    # ── BENİM TALEPLERİM (her zaman açık, ana çalışma listesi) ─────────────────
    st.markdown('<div class="compact-toolbar-note">👤 Benim Taleplerim</div>', unsafe_allow_html=True)
    if benim:
        _bolum_goster(benim, "ust_benim")
    else:
        render_empty_state(
            "📋", "Bu listede talep yok.",
            "Yeni talep eklediğinde veya sana atandığında burada görünecek."
        )

    # ── ZETA TALEPLERİ (varsayılan kapalı — büyük olabileceği için) ────────────
    _zeta_ac_key = "tm_zeta_talepleri_acik"
    if st.button(f"🏛 Zeta Talepleri ({len(zeta)})", key="tm_zeta_toggle_btn", use_container_width=True):
        st.session_state[_zeta_ac_key] = not st.session_state.get(_zeta_ac_key, False)
    if st.session_state.get(_zeta_ac_key, False):
        if zeta:
            _bolum_goster(zeta, "ust_zeta")
        else:
            st.caption("Zeta 1 / Zeta 2 danışmanlarına ait talep bulunmuyor.")

    # ── KÖPRÜ TALEPLER (varsayılan kapalı) ──────────────────────────────────────
    _kopru_ac_key = "tm_kopru_talepler_acik"
    if st.button(f"🌉 Köprü Talepler ({len(kopru)})", key="tm_kopru_toggle_btn", use_container_width=True):
        st.session_state[_kopru_ac_key] = not st.session_state.get(_kopru_ac_key, False)
    if st.session_state.get(_kopru_ac_key, False):
        if kopru:
            _bolum_goster(kopru, "ust_kopru")
        else:
            st.caption("Köprü (dış kaynak) talep bulunmuyor.")


@st.dialog("🚀 Gönderime Hazırla", width="large")
def _gonderime_hazirla_dialog(sel):
    """Gönderim akışı artık ana panelden ayrıldı — popup içinde açılıyor.
    Bu sayede satır altındaki çalışma paneli hafif kalıyor, karmaşık
    gönderim akışı (portföy seçimi + mesaj + şablon) ayrı bir pencerede
    kendi başına çalışıyor ve kapanınca ana liste/seçim durumu korunuyor."""
    render_gonderim_ozeti(sel)


def render_talep_calisma_panel(sel, musteri_map=None):
    kid = sel.get("id")
    _mm = musteri_map if musteri_map is not None else musteri_map_t
    render_selected_summary(sel, _mm)
    render_top_actions(sel)
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    ust_c1, ust_c2 = st.columns([4, 1.3], gap="small")
    with ust_c1:
        tablar = ["🎯 Eşleşmeler", "📋 Talep Detayı", "👤 Müşteri", "📝 Notlar"]
        aktif = st.radio(
            "Talep çalışma sekmesi",
            tablar,
            horizontal=True,
            key=f"tm_tab_{kid}",
            label_visibility="collapsed",
        )
    with ust_c2:
        if st.button("🚀 Gönderime Hazırla", key=f"tm_gonderim_ac_{kid}", use_container_width=True, type="primary"):
            _gonderime_hazirla_dialog(sel)
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    if aktif == "🎯 Eşleşmeler":
        render_talep_detay_band(sel)
        render_eslesmeler_panel(sel)
    elif aktif == "📋 Talep Detayı":
        render_talep_detayi_panel(sel)
    elif aktif == "👤 Müşteri":
        render_musteri_panel(sel)
    elif aktif == "📝 Notlar":
        render_notlar_panel(sel)


def render_template_add_panel(sel):
    kid = sel.get("id", "genel")
    with st.expander("＋ GD hazır şablon ekle", expanded=False):
        st.caption("Canva'da oluşturduğun linki veya hazır PDF/görsel/HTML dosyanı ekleyebilirsin. Bu şablon gönderim paketinde seçilebilir olur.")
        kanal = st.selectbox("Şablon kanalı", ["WhatsApp", "HTML Mail", "PDF", "Görsel", "Genel"], key=f"tm_tpl_kanal_{kid}")
        baslik = st.text_input("Şablon adı", placeholder="Örn: Zeta 1+1 WhatsApp Sunum", key=f"tm_tpl_baslik_{kid}")
        url = st.text_input("Canva / paylaşım linki", placeholder="https://...", key=f"tm_tpl_url_{kid}")
        uploaded = st.file_uploader(
            "Şablon dosyası",
            type=["pdf", "png", "jpg", "jpeg", "webp", "html", "htm"],
            key=f"tm_tpl_file_{kid}",
        )
        if st.button("Şablonu Kaydet", key=f"tm_tpl_save_{kid}", use_container_width=True):
            try:
                _save_uploaded_template(uploaded, baslik, kanal, user_name, url=url)
                st.success("Hazır şablon kaydedildi.")
                st.rerun(scope="app")
            except Exception as e:
                st.warning(str(e))


def render_gonderim_ozeti(sel):
    kid = sel.get("id")
    o = talep_ozeti_olustur(sel, musteri_map_t)
    selected_items = _get_selected_portfolios(kid)
    templates = _load_templates()

    st.markdown('<div class="send-panel">', unsafe_allow_html=True)
    st.markdown('<div class="send-title">🚀 Gönderime Hazırla</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="send-label">Müşteri</div><div class="send-value">{htmlesc(o["musteri"])}</div>', unsafe_allow_html=True)

    kanal = st.radio("Kanal", ["WhatsApp", "HTML Mail"], horizontal=True, key=f"tm_gonderim_kanal_{kid}")
    paket = "Zeta Portföyü" if selected_items else "Portföy seçilmedi"
    st.markdown(f'<div class="send-label">Paket</div><div class="send-value">{htmlesc(paket)} · {len(selected_items)} portföy</div>', unsafe_allow_html=True)

    st.markdown('<div class="send-label">Seçilen Portföyler</div>', unsafe_allow_html=True)
    if selected_items:
        for i, item in enumerate(selected_items[:6]):
            st.markdown(
                f'''
                <div class="selected-mini">
                    <div>
                        <div class="selected-mini-title">{htmlesc(item.get("baslik"))}</div>
                        <div class="selected-mini-meta">{htmlesc(item.get("fiyat"))} · {htmlesc(item.get("ilce"))} · {htmlesc(item.get("skor"))}/100</div>
                    </div>
                </div>
                ''',
                unsafe_allow_html=True,
            )
            if st.button("Listeden çıkar", key=f"tm_remove_selected_{kid}_{item.get('pid')}_{i}", use_container_width=True):
                st.session_state[_selected_portfolios_key(kid)] = [x for x in selected_items if str(x.get("pid")) != str(item.get("pid"))]
                st.rerun(scope="app")
    else:
        st.markdown('<div class="send-soft-box">Eşleşen portföylerden “Seç” dediğinde burada gönderim paketi oluşur.</div>', unsafe_allow_html=True)

    st.markdown('<div class="send-label">Hazır Şablon</div>', unsafe_allow_html=True)
    if templates:
        labels = [_template_label(t) for t in templates]
        sec = st.selectbox("Şablon seç", ["Şablonsuz devam et"] + labels, key=f"tm_tpl_pick_{kid}", label_visibility="collapsed")
        if sec != "Şablonsuz devam et":
            idx = labels.index(sec)
            tpl = templates[idx]
            st.session_state[_selected_templates_key(kid)] = tpl
            if tpl.get("url"):
                st.markdown(f'<span class="template-pill">Canva/link hazır</span>', unsafe_allow_html=True)
                st.link_button("Şablonu Aç", tpl["url"], use_container_width=True)
            elif tpl.get("file_path") and os.path.exists(tpl.get("file_path")):
                ext = str(tpl.get("file_path")).split(".")[-1].lower()
                st.markdown(f'<span class="template-pill">{htmlesc(ext.upper())} dosya hazır</span>', unsafe_allow_html=True)
                with open(tpl.get("file_path"), "rb") as f:
                    st.download_button("Şablonu İndir", f, file_name=tpl.get("file_name") or "sablon", use_container_width=True)
        else:
            st.session_state.pop(_selected_templates_key(kid), None)
    else:
        st.markdown('<div class="send-soft-box">Henüz kayıtlı hazır şablon yok. Aşağıdan Canva linki veya dosya ekleyebilirsin.</div>', unsafe_allow_html=True)

    render_template_add_panel(sel)

    portfoy_satirlari = "\n".join([
        f"- {x.get('baslik')} | {x.get('fiyat')} | {x.get('ilce')} | Skor: {x.get('skor')}/100" for x in selected_items
    ]) or "- Henüz portföy seçilmedi."
    varsayilan_mesaj = (
        f"Merhaba {o['musteri'] if o['musteri'] != '—' else ''},\n"
        f"Talebinize uygun portföyleri hazırladım.\n\n"
        f"{portfoy_satirlari}\n\n"
        f"Uygun olduğunuzda birlikte değerlendirebiliriz.\nİyi günler dilerim."
    )
    st.markdown('<div class="send-label">Mesaj Önizleme</div>', unsafe_allow_html=True)
    mesaj = st.text_area("Mesaj Önizleme", value=varsayilan_mesaj, height=160, key=f"tm_gonderim_mesaj_{kid}", label_visibility="collapsed")

    if st.button("🚀 Gönderime Hazırla", key=f"tm_gonderime_hazirla_{kid}", use_container_width=True, type="primary"):
        if not selected_items:
            st.warning("Önce en az bir portföy seçin.")
        else:
            st.session_state[f"tm_gonderim_paketi_{kid}"] = {
                "talep_id": kid,
                "musteri": o["musteri"],
                "kanal": kanal,
                "portfoyler": selected_items,
                "sablon": st.session_state.get(_selected_templates_key(kid)),
                "mesaj": mesaj,
                "hazirlama_tarihi": datetime.now().isoformat(),
            }
            st.success("Gönderim paketi hazırlandı. Şimdi mesajı kopyalayabilir, seçilen şablonu açabilir veya dosyayı indirebilirsin.")

    paket = st.session_state.get(f"tm_gonderim_paketi_{kid}")
    if paket:
        st.markdown('<div class="send-soft-box"><b>Hazır paket var.</b><br>Portföyler, mesaj ve varsa hazır şablon bu oturumda saklandı.</div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)


def render_yeni_talep_formu():
    parse_sonuc = st.session_state.get("tm_parse_sonuc", {})

    st.markdown("""
    <div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:12px;padding:18px 20px;margin-bottom:12px;">
    <div style="font-size:14px;font-weight:700;color:#172B4D;margin-bottom:14px;">＋ Yeni Talep Ekle</div>
    """, unsafe_allow_html=True)

    gc1, gc2, gc3 = st.columns(3)
    with gc1:
        st.caption("Ofis")
        zeta_ofis = st.selectbox("Ofis", ["Seç...", "ZETA 1", "ZETA 2", "Diğer Ofis"], key="tm_ofis")
    with gc2:
        if zeta_ofis in ("ZETA 1", "ZETA 2", "Seç..."):
            st.caption("Zeta Danışmanı")
            gd_kaynak = gd_list_z1 if zeta_ofis == "ZETA 1" else gd_list_z2 if zeta_ofis == "ZETA 2" else gd_list_tum
            _default_gd = user_name if user_name in gd_kaynak else "Seç..."
            _opts = ["Seç..."] + gd_kaynak + ["Diğer (manuel gir)"]
            _default_idx = _opts.index(_default_gd) if _default_gd in _opts else 0
            gd_sec = st.selectbox("Danışman seçin", _opts, index=_default_idx, key="tm_gd_sec")
            gd_manuel = st.text_input("Danışman adı", key="tm_gd_manuel") if gd_sec == "Diğer (manuel gir)" else ""
            gd_ad = gd_manuel if gd_sec == "Diğer (manuel gir)" else (gd_sec if gd_sec != "Seç..." else user_name)
        else:
            st.caption("Ofis Adı")
            ofis_adi = st.text_input("Ofis adı", placeholder="Örn: RE/MAX Bornova", key="tm_ofis_adi")
            gd_ad = ""
    with gc3:
        if zeta_ofis == "Diğer Ofis":
            st.caption("Danışman Adı")
            gd_dis = st.text_input("Danışman adı", placeholder="Ad Soyad", key="tm_gd_dis")
            gd_ad = f"{gd_dis} - {ofis_adi}".strip(" -") if (gd_dis or ofis_adi) else ""
        else:
            st.empty()
    kaynak = "zeta1" if zeta_ofis == "ZETA 1" else "zeta2" if zeta_ofis == "ZETA 2" else "dis_kaynak" if zeta_ofis == "Diğer Ofis" else "ofis"

    st.markdown("---")
    st.markdown('<p style="font-size:12px;font-weight:600;color:#355C7D;margin-bottom:6px;">👤 Müşteri Bilgisi <span style="font-weight:400;color:#94a3b8;">(isteğe bağlı)</span></p>', unsafe_allow_html=True)
    mk1, mk2 = st.columns(2)
    with mk1:
        tm_musteri_adi = st.text_input("Müşteri adı", placeholder="Ad Soyad", key="tm_musteri_adi")
    with mk2:
        tm_musteri_tel = st.text_input("Telefon", placeholder="05xx xxx xx xx", key="tm_musteri_tel")
    st.markdown("---")

    yontem = st.radio("Giriş yöntemi", ["Yapay Zeka Ayrıştırma", "Form"], horizontal=True, key="tm_yontem")

    if yontem == "Yapay Zeka Ayrıştırma":
        metin = st.text_area(
            "Talep açıklaması",
            placeholder="Örn: Müşterim Bornova veya Karşıyaka'da 3+1 kiralık daire arıyor, max 25.000 TL...",
            height=90,
            key="tm_metin",
        )
        pa, pb = st.columns([1, 4])
        with pa:
            if st.button("AI ile Doldur", key="tm_parse_btn", type="primary"):
                if metin.strip():
                    with st.spinner("Analiz ediliyor..."):
                        sonuc = ai_parse_talep(metin)
                        mh_metin = sonuc.get("mahalle", "") or metin
                        lookup = mahalle_ile_ilce_bul(mh_metin)
                        if lookup:
                            sonuc["il"] = lookup.get("il", "")
                            sonuc["ilce"] = lookup.get("ilce", "")
                            if not sonuc.get("mahalle"):
                                sonuc["mahalle"] = lookup.get("mahalle", "")
                        st.session_state["tm_parse_sonuc"] = sonuc
                        st.rerun()
                else:
                    st.warning("Açıklama yazın.")
        if parse_sonuc:
            st.caption("✅ Aşağıdaki alanları kontrol edip düzenleyebilirsiniz.")

    if yontem == "Form" or parse_sonuc:
        f1, f2, f3 = st.columns(3)
        with f1:
            ozet = st.text_input("Özet", value=parse_sonuc.get("ozet", ""), key="tm_ozet")
            il = st.selectbox(
                "İl",
                ILLER,
                index=ILLER.index(parse_sonuc.get("il", "İzmir")) if parse_sonuc.get("il", "") in ILLER else 0,
                key="tm_il",
            )
            ilce_opts = ["İzmir Genel"] + ilce_sec
            ilce_raw = parse_sonuc.get("ilce", "")
            ilce_idx = ilce_opts.index(ilce_raw) if ilce_raw in ilce_opts else 0
            ilce_sec2 = st.selectbox("Birincil İlçe", ilce_opts, index=ilce_idx, key="tm_ilce")
            ilce_val = "" if ilce_sec2 == "İzmir Genel" else ilce_sec2
        with f2:
            mulk = st.selectbox(
                "Mülk Tipi",
                ["Konut", "İşyeri", "Arsa", "Belirsiz"],
                index=["Konut", "İşyeri", "Arsa", "Belirsiz"].index(parse_sonuc.get("mulk_tipi", "Belirsiz"))
                if parse_sonuc.get("mulk_tipi", "") in ["Konut", "İşyeri", "Arsa", "Belirsiz"] else 3,
                key="tm_mulk",
            )
            islem = st.selectbox(
                "İşlem Tipi",
                ["Satılık", "Kiralık", "Belirsiz"],
                index=["Satılık", "Kiralık", "Belirsiz"].index(parse_sonuc.get("islem_tipi", "Belirsiz"))
                if parse_sonuc.get("islem_tipi", "") in ["Satılık", "Kiralık", "Belirsiz"] else 2,
                key="tm_islem",
            )
            butce = st.text_input("Bütçe", value=parse_sonuc.get("max_butce", ""), key="tm_butce")
        with f3:
            oda = st.text_input("Oda/M²", value=parse_sonuc.get("oda_sayisi_m2", ""), key="tm_oda")
            mahalle = st.text_input("Mahalle", value=parse_sonuc.get("mahalle", ""), key="tm_mahalle")
            kriterler = st.text_area("Özel Kriterler", value=parse_sonuc.get("ozel_kriterler", ""), height=80, key="tm_kriter")

        ilceler_default = [i for i in (parse_sonuc.get("ilceler") or []) if i in ilce_sec]
        ilceler = st.multiselect("Tüm İlçeler", ilce_sec, default=ilceler_default, key="tm_ilceler")

        ka, kb = st.columns([1, 4])
        with ka:
            if st.button("💾 Kaydet", key="tm_kaydet", type="primary"):
                if not gd_ad:
                    st.warning("Danışman seçin.")
                else:
                    veri = {
                        "talep_eden_danisan": gd_ad,
                        "kategori": "alici_talebi",
                        "kaynak": kaynak,
                        "giren_gd": user_name,
                        "il": il,
                        "ilce": ilce_val,
                        "ilceler": ilceler if ilceler else ([ilce_val] if ilce_val else []),
                        "mulk_tipi": mulk,
                        "islem_tipi": islem,
                        "max_butce": butce,
                        "oda_sayisi_m2": oda,
                        "mahalle": mahalle,
                        "ozel_kriterler": kriterler,
                        "ozet": ozet,
                        "olusturma_tarihi": datetime.now().isoformat(),
                    }
                    if talep_kaydet(veri):
                        if tm_musteri_adi.strip():
                            try:
                                son_kayit = get_client().table("alici_talepleri")\
                                    .select("id").eq("giren_gd", user_name)\
                                    .order("olusturma_tarihi", desc=True).limit(1).execute()
                                yeni_talep_id = str(son_kayit.data[0]["id"]) if son_kayit.data else ""
                                get_client().table("musteriler").insert({
                                    "talep_id": yeni_talep_id,
                                    "musteri_adi": tm_musteri_adi.strip(),
                                    "telefon": tm_musteri_tel.strip(),
                                    "ekleyen": user_name,
                                    "danisan_id": user_name,
                                }).execute()
                            except Exception:
                                pass
                        st.session_state.pop("tm_parse_sonuc", None)
                        st.session_state["tm_aktif_sekme"] = "bos"
                        st.success("✅ Talep kaydedildi!")
                        st.rerun()
        with kb:
            if st.button("İptal", key="tm_iptal"):
                st.session_state.pop("tm_parse_sonuc", None)
                st.session_state["tm_aktif_sekme"] = "bos"
                st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)



# ── Ana layout ────────────────────────────────────────────────────────────────
# Akış: üstte yatay/paginated Talep Paneli → seçilen talep, tıklanan SATIRIN
# HEMEN ALTINDA açılır (bkz. render_talep_liste_view / render_talep_card_view
# içindeki "Satır altı çalışma paneli" bloğu). Bu bölüm artık sadece "Yeni
# Talep" formunu ve seçili kaydın hiçbir listede bulunamadığı durumu ele alır.
render_talep_ust_paneli(talep_gruplari, takip_kayitlar, musteri_map_t)

st.markdown('<div style="height:14px"></div>', unsafe_allow_html=True)

aktif_sekme = st.session_state.get("tm_aktif_sekme", "bos")

if aktif_sekme == "yeni_talep":
    render_yeni_talep_formu()
elif selected_id and not _panel_render_flag["acildi"]:
    render_empty_state(
        "!", "Kayıt bulunamadı.",
        "Talep silinmiş, güncellenmiş veya liste dışına çıkmış olabilir."
    )
