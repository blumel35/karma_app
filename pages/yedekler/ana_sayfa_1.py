# pages/ana_sayfa.py
# GD Kokpit — Danışmanın günlük çalışma merkezi
# Bölümler: Taleplerim | Portföylerim | Sunum Merkezi

import streamlit as st
import sys, os, re, json, requests
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.ui_helpers import render_navbar, render_page_header
from core.supabase_client import get_client
try:
    from core.gd_portfoy_view import gd_portfoy_goster
except Exception:
    gd_portfoy_goster = None
from datetime import datetime, date

# ── SESSION GUARD ─────────────────────────────────────────────────────────────
if not st.session_state.get("kullanici"):
    st.switch_page("pages/giris.py")

_k  = st.session_state.get("kullanici", {})
_ad = _k.get("ad_soyad") or _k.get("ad", "")
st.session_state["user_role"]     = _k.get("rol", "danisan")
st.session_state["user_name"]     = _ad
st.session_state["user_initials"] = "".join(w[0].upper() for w in _ad.split()[:2] if w)

render_navbar(
    user_role=st.session_state.get("user_role", "danisan"),
    user_name=st.session_state.get("user_name", ""),
    user_initials=st.session_state.get("user_initials", ""),
)

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
:root {
    --bg:#F4F7FB; --text:#0F172A; --muted:#64748B;
    --primary:#1E3A5F; --p2:#355C7D;
    --border:#DCE4EE; --chip:#EEF4FA; --hover:#F8FBFF;
    --green:#16a34a; --amber:#ca8a04;
}
.stApp{background:var(--bg);}
.block-container{padding-top:.5rem!important;padding-bottom:2rem!important;max-width:1400px!important;}
div[data-testid="stButton"]>button{
    border-radius:8px;border:1px solid var(--border);min-height:30px;
    padding:6px 12px;font-size:12px;font-weight:600;
    background:var(--chip);color:var(--text);transition:all .15s ease;
}
div[data-testid="stButton"]>button p{font-size:12px!important;margin:0!important;}
div[data-testid="stButton"]>button[kind="primary"]{background:var(--primary)!important;border-color:var(--primary)!important;color:#fff!important;}
div[data-testid="stButton"]>button[kind="secondary"]{background:var(--hover)!important;border:1px solid var(--border)!important;color:var(--text)!important;}
[data-testid="stContainer"]{border-radius:12px;border-color:var(--border)!important;background:#fff;box-shadow:0 2px 8px rgba(15,23,42,.04);}
div[data-baseweb="select"]>div{border-radius:6px!important;border-color:var(--border)!important;min-height:32px!important;font-size:12px!important;}
input,textarea{border-radius:6px!important;font-size:12px!important;}
label{color:#475569!important;font-weight:600!important;font-size:11px!important;}
.stTabs [data-baseweb="tab-list"]{gap:4px;}
.stTabs [data-baseweb="tab"]{border-radius:8px 8px 0 0;font-size:13px;font-weight:600;padding:8px 18px;}
.kokpit-bolum-baslik{
    font-size:11px;font-weight:700;color:var(--muted);
    text-transform:uppercase;letter-spacing:.08em;
    margin:0 0 10px 0;padding-bottom:8px;
    border-bottom:1px solid var(--border);
}
.talep-kart{
    border:1px solid var(--border);border-radius:10px;
    padding:10px 13px 8px;margin-bottom:6px;background:#fff;
    transition:border-color .12s;
}
.talep-kart:hover{border-color:#b0c4d8;}
.talep-kart-baslik{font-size:13px;font-weight:700;color:var(--text);margin-bottom:3px;
    white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.talep-kart-meta{font-size:11px;color:var(--muted);display:flex;gap:8px;flex-wrap:wrap;align-items:center;}
.badge{display:inline-flex;align-items:center;padding:2px 8px;border-radius:20px;font-size:10.5px;font-weight:600;}
.b-sat{background:#FCEBEB;color:#A32D2D;border:1px solid #f5c0c0;}
.b-kir{background:#FAEEDA;color:#854F0B;border:1px solid #f0d0a0;}
.b-kon{background:#f1f5f9;color:#475569;border:1px solid #e2e8f0;}
.b-yeni{background:#dcfce7;color:#166534;border:1px solid #bbf7d0;}
.sunum-btn{
    display:inline-flex;align-items:center;gap:6px;
    padding:8px 16px;border-radius:8px;font-size:12px;font-weight:600;
    border:1px solid var(--border);background:var(--chip);cursor:pointer;
}
</style>
""", unsafe_allow_html=True)

# ── DANIŞMAN KİMLİĞİ ─────────────────────────────────────────────────────────
def _kimlik():
    _id = str(_k.get("id","") or "").strip()
    _uk = str(_k.get("user_key","") or "").strip()
    _em = str(_k.get("email","") or "").strip()
    if _id: return ("danisan_id", _id)
    if _uk: return ("user_key", _uk)
    if _em: return ("danisan_email", _em)
    return ("","")
_id_alan, _id_deger = _kimlik()

# ── YARDIMCILAR ───────────────────────────────────────────────────────────────
def gun_f(s):
    if not s: return 9999
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f","%Y-%m-%dT%H:%M:%S","%Y-%m-%d %H:%M:%S","%Y-%m-%d"):
        try: return max((datetime.now()-datetime.strptime(str(s)[:19],fmt[:19])).days,0)
        except: continue
    return 9999

def tarih_et(g):
    if g==0: return "Bugün"
    if g==1: return "Dün"
    if g<=7: return f"{g} gün önce"
    if g<=30: return f"{g//7} hafta önce"
    return f"{g//30} ay önce"

def ilce_oz(v):
    lst=[i for i in (v.get("ilceler") or []) if i and i!="Diğer Bölge"]
    return " · ".join(lst[:2]) if lst else (v.get("ilce","") or "")

def bdg(et):
    if not et or et in ("Belirsiz","None",""): return ""
    c={"Satılık":"b-sat","Kiralık":"b-kir","Konut":"b-kon","İşyeri":"b-kon","Arsa":"b-kon"}.get(et,"b-kon")
    return f'<span class="badge {c}">{et}</span>'

def isim_ayikla(g):
    if not g: return ""
    m=re.match(r'^([^<]+)',g)
    return m.group(1).strip().strip('"') if m else g

# ── VERİ FONKSİYONLARI ───────────────────────────────────────────────────────
@st.cache_data(ttl=30)
def musteriler_cek(alan, deger):
    if not alan or not deger: return []
    try:
        r=get_client().table("musteriler").select("*").eq(alan,deger)\
            .order("olusturma_tarihi",desc=True).limit(100).execute()
        return r.data or []
    except: return []

@st.cache_data(ttl=30)
def portfoyler_cek(alan, deger):
    if not alan or not deger: return []
    try:
        r=get_client().table("portfoyler").select("*").eq(alan,deger)\
            .order("olusturma_tarihi",desc=True).limit(100).execute()
        return r.data or []
    except: return []

@st.cache_data(ttl=30)
def portfoyler_gd_cek(danisan_adi: str):
    """Admin: belirli bir danışmanın zeta1/zeta2 portföylerini çek."""
    try:
        r=get_client().table("portfoyler").select("*")            .in_("kaynak", ["zeta1","zeta2"])            .ilike("talep_eden_danisan", f"%{danisan_adi}%")            .order("ilan_tarihi", desc=True).limit(500).execute()
        return r.data or []
    except: return []

@st.cache_data(ttl=60)
def gd_listesi_cek():
    """Sadece zeta1/zeta2 kaynaklı portfoylerden benzersiz danışman listesi."""
    try:
        r=get_client().table("portfoyler")            .select("talep_eden_danisan")            .in_("kaynak", ["zeta1","zeta2"])            .not_.is_("talep_eden_danisan","null")            .limit(2000).execute()
        isimler = set()
        for row in (r.data or []):
            ad = (row.get("talep_eden_danisan","") or "").split("<")[0].strip().strip('"')
            if ad and len(ad) > 2: isimler.add(ad)
        return sorted(isimler)
    except: return []


@st.cache_data(ttl=3600)
def ilce_listesi():
    try:
        r=get_client().table("ilceler").select("ilce").execute()
        return sorted([x["ilce"] for x in r.data if x.get("ilce")])
    except: return []

@st.cache_data(ttl=3600)
def mahalle_lookup():
    try:
        r=get_client().table("mahalleler").select("il,ilce,mahalle").execute()
        return {row["mahalle"].strip().lower():(row["il"],row["ilce"]) for row in r.data}
    except: return {}

def mahalle_bul(metin):
    if not metin: return {}
    lk=mahalle_lookup(); ml=metin.lower()
    for mh,(il,ilce) in lk.items():
        if mh in ml: return {"il":il,"ilce":ilce,"mahalle":mh}
    return {}


# ── PAYLAŞIM FONKSİYONLARI ────────────────────────────────────────────────────
def ofise_paylas(musteri: dict, danisan_adi: str) -> bool:
    """musteriler kaydını alici_talepleri tablosuna (ofis kaynağıyla) ekler."""
    try:
        ilce_val = musteri.get("ilce","")
        ilceler_val = musteri.get("ilceler") or ([ilce_val] if ilce_val else [])
        veri = {
            "kategori":           "alici_talebi",
            "kaynak":             "ofis",
            "talep_eden_danisan": danisan_adi,
            "il":                 musteri.get("il","İzmir"),
            "ilce":               ilce_val,
            "ilceler":            ilceler_val,
            "mulk_tipi":          musteri.get("mulk_tipi",""),
            "islem_tipi":         musteri.get("islem_tipi",""),
            "max_butce":          musteri.get("butce",""),
            "oda_sayisi_m2":      musteri.get("oda_sayisi",""),
            "ozel_kriterler":     musteri.get("kriterler",""),
            "ozet":               musteri.get("ozet",""),
            "gizli":              False,
            "olusturma_tarihi":   datetime.now().isoformat(),
        }
        get_client().table("alici_talepleri").insert(veri).execute()
        return True
    except Exception as e:
        st.error(f"Ofis paylaşım hatası: {e}")
        return False


def startkey_mail_gonder(musteri: dict, danisan_adi: str) -> bool:
    """Talep özetini Yandex SMTP ile Startkey mail adresine gönderir."""
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart

    try:
        smtp_user  = st.secrets["email"]["user"]
        smtp_pass  = st.secrets["email"]["password"]
        smtp_host  = "smtp.yandex.com"
        smtp_port  = 465
        alici_mail = st.secrets["email"].get("startkey_talep_mail", smtp_user)

        ilce_ozet = " · ".join(
            [i for i in (musteri.get("ilceler") or []) if i and i != "Diğer Bölge"]
        ) or musteri.get("ilce","") or "—"

        html_body = f"""
<div style="font-family:Arial,sans-serif;max-width:580px;margin:0 auto;border:1px solid #DCE4EE;border-radius:12px;overflow:hidden;">
  <div style="background:#1E3A5F;padding:18px 24px;">
    <span style="color:#fff;font-size:16px;font-weight:700;">📋 Yeni Müşteri Talebi</span>
    <span style="color:#b0c8e4;font-size:12px;margin-left:12px;">Startkey Zeta</span>
  </div>
  <div style="padding:20px 24px;background:#fff;">
    <table style="width:100%;border-collapse:collapse;font-size:13px;">
      <tr><td style="color:#64748B;padding:6px 0;width:130px">Danışman</td><td style="font-weight:600;color:#0F172A">{danisan_adi}</td></tr>
      <tr><td style="color:#64748B;padding:6px 0">İşlem Tipi</td><td style="font-weight:600;color:#0F172A">{musteri.get("islem_tipi","—")}</td></tr>
      <tr><td style="color:#64748B;padding:6px 0">Mülk Tipi</td><td style="font-weight:600;color:#0F172A">{musteri.get("mulk_tipi","—")}</td></tr>
      <tr><td style="color:#64748B;padding:6px 0">Bölge</td><td style="font-weight:600;color:#0F172A">{ilce_ozet}</td></tr>
      <tr><td style="color:#64748B;padding:6px 0">Bütçe</td><td style="font-weight:600;color:#0F172A">{musteri.get("butce","—")}</td></tr>
      <tr><td style="color:#64748B;padding:6px 0">Oda / M²</td><td style="font-weight:600;color:#0F172A">{musteri.get("oda_sayisi","—")}</td></tr>
      <tr><td style="color:#64748B;padding:6px 0">Özel Kriterler</td><td style="color:#475569">{musteri.get("kriterler","—")}</td></tr>
      <tr><td style="color:#64748B;padding:6px 0">Özet</td><td style="color:#475569;font-style:italic">{musteri.get("ozet","—")}</td></tr>
    </table>
    <div style="margin-top:14px;padding:10px 14px;background:#FFF9ED;border-radius:8px;border-left:3px solid #F4B740;font-size:12px;color:#64748B;">
      ⚠️ Müşteri adı ve iletişim bilgileri bu mailde yer almamaktadır — gizlilik korunmaktadır.
    </div>
  </div>
  <div style="padding:12px 24px;background:#f8fafc;border-top:1px solid #DCE4EE;font-size:11px;color:#94a3b8;">
    Startkey Zeta · {datetime.now().strftime("%d.%m.%Y %H:%M")}
  </div>
</div>
"""
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"[Startkey Talep] {musteri.get('islem_tipi','')  } {musteri.get('mulk_tipi','')} · {ilce_ozet} · {danisan_adi}"
        msg["From"]    = smtp_user
        msg["To"]      = alici_mail
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        with smtplib.SMTP_SSL(smtp_host, smtp_port) as server:
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, alici_mail, msg.as_string())
        return True
    except Exception as e:
        st.error(f"Mail gönderilemedi: {e}")
        return False

def musteri_kaydet(veri):
    try: get_client().table("musteriler").insert(veri).execute(); st.cache_data.clear(); return True
    except Exception as e: st.error(f"Kayıt hatası: {e}"); return False

def portfoy_kaydet_fn(veri):
    try: get_client().table("portfoyler").insert(veri).execute(); st.cache_data.clear(); return True
    except Exception as e: st.error(f"Kayıt hatası: {e}"); return False

def ai_parse_talep(metin):
    try:
        api_key=st.secrets["anthropic"]["api_key"].strip()
        prompt=f"""Aşağıdaki gayrimenkul talep açıklamasını analiz et ve JSON olarak döndür.
Sadece JSON döndür, başka hiçbir şey yazma.

Talep:
{metin}

JSON formatı:
{{
  "il": "İzmir",
  "ilce": "birincil ilçe veya boş",
  "ilceler": ["ilçe1","ilçe2"],
  "mulk_tipi": "Konut/İşyeri/Arsa/Belirsiz",
  "islem_tipi": "Satılık/Kiralık/Belirsiz",
  "oda_sayisi_m2": "3+1 veya 120 m² gibi",
  "max_butce": "rakam ve para birimi",
  "mahalle": "mahalle/semt bilgisi",
  "ozel_kriterler": "özel istekler, notlar",
  "ozet": "talebi özetleyen kısa cümle"
}}"""
        resp=requests.post("https://api.anthropic.com/v1/messages",
            headers={"Content-Type":"application/json","x-api-key":api_key,"anthropic-version":"2023-06-01"},
            json={"model":"claude-sonnet-4-6","max_tokens":600,"messages":[{"role":"user","content":prompt}]},
            timeout=30)
        data=resp.json()
        if "error" in data: return {"_hata":data["error"].get("message","")}
        text=data["content"][0]["text"].strip().replace("```json","").replace("```","").strip()
        return json.loads(text)
    except Exception as e: return {"_hata":str(e)}

def ai_parse_portfoy(metin):
    try:
        api_key=st.secrets["anthropic"]["api_key"].strip()
        prompt=f"""Aşağıdaki gayrimenkul portföy açıklamasını analiz et ve JSON olarak döndür.
Sadece JSON döndür, başka hiçbir şey yazma.

Portföy:
{metin}

JSON formatı:
{{
  "il": "İzmir",
  "ilce": "birincil ilçe veya boş",
  "ilceler": ["ilçe1"],
  "mulk_tipi": "Konut/İşyeri/Arsa/Belirsiz",
  "islem_tipi": "Satılık/Kiralık/Belirsiz",
  "oda_sayisi_m2": "3+1 veya 120 m² gibi",
  "fiyat": "rakam ve para birimi",
  "mahalle": "mahalle/semt bilgisi",
  "ozellikler": "özellikler, notlar",
  "ozet": "mülkü özetleyen kısa cümle",
  "ilan_linki": "varsa ilan linki veya boş"
}}"""
        resp=requests.post("https://api.anthropic.com/v1/messages",
            headers={"Content-Type":"application/json","x-api-key":api_key,"anthropic-version":"2023-06-01"},
            json={"model":"claude-sonnet-4-6","max_tokens":600,"messages":[{"role":"user","content":prompt}]},
            timeout=30)
        data=resp.json()
        if "error" in data: return {"_hata":data["error"].get("message","")}
        text=data["content"][0]["text"].strip().replace("```json","").replace("```","").strip()
        return json.loads(text)
    except Exception as e: return {"_hata":str(e)}

# ── BAŞLIK ────────────────────────────────────────────────────────────────────
saat=datetime.now().hour
selam="Günaydın" if saat<12 else ("İyi akşamlar" if saat>=18 else "İyi günler")
isim_kisa=(_ad.split()[0]) if _ad else "Danışman"

col_hdr, col_yen = st.columns([9,1])
with col_hdr:
    st.markdown(
        f'<div style="padding:0 0 4px;">'
        f'<div style="font-size:11px;font-weight:600;color:var(--muted);letter-spacing:.06em;">'
        f'{datetime.now().strftime("%H:%M")} · {date.today().strftime("%d %B %Y")}</div>'
        f'<div style="font-size:22px;font-weight:700;color:#1E293B;letter-spacing:-.03em;">'
        f'{selam}, {isim_kisa}</div></div>',
        unsafe_allow_html=True
    )
with col_yen:
    st.markdown("<div style='margin-top:18px'>",unsafe_allow_html=True)
    if st.button("↺",key="kokpit_yen",help="Yenile"):
        st.cache_data.clear(); st.rerun()
    st.markdown("</div>",unsafe_allow_html=True)

st.markdown("<div style='height:8px'></div>",unsafe_allow_html=True)

# ── SABITLER ─────────────────────────────────────────────────────────────────
ILLER=["İzmir","Aydın","Manisa","Balıkesir","Muğla","İstanbul","Ankara","Diğer"]
MULK=["Konut","İşyeri","Arsa","Belirsiz"]
ISLEM=["Satılık","Kiralık","Belirsiz"]
TAKIP=["Aktif","Beklemede","Görüşülüyor","Teklif Verildi","Kapandı"]
_ILC=ilce_listesi()

# ── ANA SEKMELER ─────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs(["🏠 Portföylerim", "👤 Taleplerim", "📌 Takip Listem", "✨ Sunum Merkezi"])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2: TALEPLERİM  (artık 2. sekme)
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.markdown("""
    <div style="font-size:12px;color:#64748B;background:#EEF4FA;border-radius:8px;
    padding:8px 12px;margin-bottom:14px;border-left:3px solid #1E3A5F;">
    Müşteri talep kayıtlarınız. <strong>Müşteri adı ve notlar yalnızca size görünür.</strong>
    </div>""", unsafe_allow_html=True)

    # ── Yeni Talep Formu ──────────────────────────────────────────────────────
    if not st.session_state.get("t_form_ac", False):
        if st.button("+ Yeni Talep Ekle", key="t_form_btn", type="primary"):
            st.session_state["t_form_ac"]=True
            st.session_state.pop("t_parse",None)
            st.rerun()
    else:
        with st.container(border=True):
            st.markdown("**Yeni Müşteri Talebi**")

            # ── BÖLÜM 1: Müşteri bilgileri — sadece musteriler tablosuna, ofisle paylaşılmaz ──
            st.markdown(
                '<div style="font-size:11px;font-weight:700;color:#64748B;letter-spacing:.06em;' +
                'text-transform:uppercase;padding:6px 10px;background:#f1f5f9;border-radius:6px;margin-bottom:8px;">' +
                '🔒 Müşteri Bilgileri — Yalnızca Size Görünür</div>',
                unsafe_allow_html=True
            )
            _mc1, _mc2, _mc3 = st.columns(3)
            with _mc1:
                _t_musteri = st.text_input("Müşteri Adı *", key="t_musteri", placeholder="Ad Soyad")
            with _mc2:
                _t_tel = st.text_input("Telefon", key="t_tel", placeholder="+90 5xx xxx xx xx")
            with _mc3:
                _t_takip = st.selectbox("Takip Durumu", TAKIP, key="t_takip")

            st.markdown(
                '<div style="font-size:11px;font-weight:700;color:#64748B;letter-spacing:.06em;' +
                'text-transform:uppercase;padding:6px 10px;background:#EEF4FA;border-radius:6px;margin:10px 0 8px;">' +
                '🏢 Talep Kriterleri — Ofis Havuzuyla Paylaşılır</div>',
                unsafe_allow_html=True
            )

            # ── BÖLÜM 2: Talep kriterleri — AI veya Form ile girilir, havuza da gider ──
            yontem=st.radio("Giriş yöntemi",["🤖 AI ile Analiz","📝 Form"],
                horizontal=True, key="t_yontem", label_visibility="collapsed")

            parse=st.session_state.get("t_parse",{})

            if "AI" in yontem:
                _c1,_c2=st.columns([3,1])
                with _c1:
                    metin=st.text_area("Talep açıklaması", height=80, key="t_metin",
                        placeholder="Örn: Bornova veya Karşıyaka'da 3+1 kiralık daire arıyor, max 25.000 TL, eşyalı...",
                        label_visibility="collapsed")
                with _c2:
                    st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
                    if st.button("🤖 AI Analiz", key="t_ai_btn", type="primary", use_container_width=True):
                        if metin.strip():
                            with st.spinner("Analiz ediliyor..."):
                                sonuc=ai_parse_talep(metin)
                                if "_hata" in sonuc:
                                    st.error(f"AI hatası: {sonuc['_hata']}")
                                else:
                                    lk=mahalle_bul(sonuc.get("mahalle","") or metin)
                                    if lk:
                                        sonuc["il"]=lk.get("il","")
                                        sonuc["ilce"]=lk.get("ilce","")
                                        if not sonuc.get("mahalle"): sonuc["mahalle"]=lk.get("mahalle","")
                                    st.session_state["t_parse"]=sonuc; st.rerun()
                        else: st.warning("Açıklama girin.")
                if parse:
                    st.markdown("**✅ AI analiz tamamlandı — kontrol edip kaydedin:**")
            else:
                parse={}

            if "Form" in yontem or parse:
                _f1,_f2,_f3=st.columns(3)
                with _f1:
                    _t_il=st.selectbox("İl", ILLER, key="t_il",
                        index=ILLER.index(parse.get("il","İzmir")) if parse.get("il","") in ILLER else 0)
                    _t_islem=st.selectbox("İşlem Tipi", ISLEM, key="t_islem",
                        index=ISLEM.index(parse.get("islem_tipi","Belirsiz")) if parse.get("islem_tipi","") in ISLEM else 2)
                with _f2:
                    _t_mulk=st.selectbox("Mülk Tipi", MULK, key="t_mulk",
                        index=MULK.index(parse.get("mulk_tipi","Belirsiz")) if parse.get("mulk_tipi","") in MULK else 3)
                    _t_butce=st.text_input("Bütçe", key="t_butce", value=parse.get("max_butce",""),
                        placeholder="ör: 25.000 TL")
                with _f3:
                    _t_oda=st.text_input("Oda/M²", key="t_oda", value=parse.get("oda_sayisi_m2",""),
                        placeholder="ör: 3+1")
                    _t_ilce_raw=parse.get("ilce","")
                    _t_ilce=st.selectbox("Birincil İlçe", ["—"]+_ILC, key="t_ilce",
                        index=(["—"]+_ILC).index(_t_ilce_raw) if _t_ilce_raw in (["—"]+_ILC) else 0)

                _t_ilceler_def=[i for i in (parse.get("ilceler") or []) if i in _ILC]
                _t_ilceler=st.multiselect("Tüm İlçeler", _ILC, default=_t_ilceler_def, key="t_ilceler")
                _t_krit=st.text_area("Özel Kriterler", height=60, key="t_krit",
                    value=parse.get("ozel_kriterler",""),
                    placeholder="Eşyalı, site içi, asansörlü, kat tercihi...")
                _t_ozet=st.text_input("Özet", key="t_ozet", value=parse.get("ozet",""),
                    placeholder="ör: Bornova 3+1 kiralık arayışı")

                ka,kb=st.columns([1.2,6])
                with ka:
                    if st.button("💾 Kaydet", key="t_kaydet", type="primary"):
                        if not _t_musteri.strip():
                            st.warning("Müşteri adı zorunludur.")
                        elif not _id_alan:
                            st.error("Oturum bilgisi eksik.")
                        else:
                            _ilce_val="" if _t_ilce=="—" else _t_ilce
                            _ilceler_val=_t_ilceler or ([_ilce_val] if _ilce_val else [])
                            _islem_v=st.session_state.get("t_islem","Belirsiz")
                            _mulk_v=st.session_state.get("t_mulk","Belirsiz")
                            _il_v=st.session_state.get("t_il","İzmir")

                            # 1) musteriler — özel, sadece danışmana görünür
                            veri_m={
                                _id_alan:_id_deger,
                                "musteri_adi":_t_musteri.strip(),
                                "telefon":_t_tel.strip(),
                                "islem_tipi":_islem_v,
                                "mulk_tipi":_mulk_v,
                                "il":_il_v,
                                "ilce":_ilce_val,
                                "ilceler":_ilceler_val,
                                "butce":st.session_state.get("t_butce","").strip(),
                                "oda_sayisi":st.session_state.get("t_oda","").strip(),
                                "kriterler":st.session_state.get("t_krit","").strip(),
                                "ozet":st.session_state.get("t_ozet","").strip(),
                                "takip_durumu":_t_takip,
                                "olusturma_tarihi":datetime.now().isoformat(),
                            }

                            # 2) alici_talepleri — ofis havuzuyla paylaşılır (müşteri adı/tel yok)
                            veri_h={
                                "kategori":"alici_talebi",
                                "kaynak":"ofis",
                                "talep_eden_danisan":st.session_state.get("user_name",""),
                                "il":_il_v,
                                "ilce":_ilce_val,
                                "ilceler":_ilceler_val,
                                "mulk_tipi":_mulk_v,
                                "islem_tipi":_islem_v,
                                "max_butce":st.session_state.get("t_butce","").strip(),
                                "oda_sayisi_m2":st.session_state.get("t_oda","").strip(),
                                "ozel_kriterler":st.session_state.get("t_krit","").strip(),
                                "ozet":st.session_state.get("t_ozet","").strip(),
                                "gizli":False,
                                "olusturma_tarihi":datetime.now().isoformat(),
                            }

                            ok1=musteri_kaydet(veri_m)
                            if ok1:
                                try:
                                    get_client().table("alici_talepleri").insert(veri_h).execute()
                                except Exception as ex:
                                    st.warning(f"Havuz kaydı başarısız: {ex}")
                                st.session_state["t_form_ac"]=False
                                st.session_state.pop("t_parse",None)
                                st.success("✅ Talep kaydedildi ve ofis havuzuna eklendi!")
                                st.rerun()
                with kb:
                    if st.button("İptal", key="t_iptal"):
                        st.session_state["t_form_ac"]=False
                        st.session_state.pop("t_parse",None)
                        st.rerun()

    st.markdown("<div style='height:8px'></div>",unsafe_allow_html=True)

    # ── Kayıt listesi ─────────────────────────────────────────────────────────
    if not _id_alan:
        st.warning("Oturum bilgisi eksik. Lütfen çıkış yapıp tekrar giriş yapın.")
    else:
        musteriler=musteriler_cek(_id_alan,_id_deger)

        if not musteriler:
            st.info("Henüz talep kaydınız yok. Yukarıdan yeni talep ekleyin.")
        else:
            # Filtre
            _fa,_fb,_fc=st.columns([2,1.5,1.5])
            with _fa: _t_ara=st.text_input("Ara",key="tm_ara",placeholder="Müşteri, ilçe...",label_visibility="collapsed")
            with _fb: _t_isl_f=st.selectbox("İşlem",["Tümü"]+ISLEM[:-1],key="tm_isl",label_visibility="collapsed")
            with _fc: _t_tak_f=st.selectbox("Durum",["Tümü"]+TAKIP,key="tm_tak",label_visibility="collapsed")

            f=musteriler[:]
            if _t_ara: f=[v for v in f if any(_t_ara.lower() in str(v.get(k,"")).lower() for k in ["musteri_adi","kriterler","ilce","il","ozet"])]
            if _t_isl_f!="Tümü": f=[v for v in f if v.get("islem_tipi","")==_t_isl_f]
            if _t_tak_f!="Tümü": f=[v for v in f if v.get("takip_durumu","")==_t_tak_f]

            st.caption(f"{len(f)} kayıt")

            for v in f:
                kid=v.get("id","")
                musa=v.get("musteri_adi","") or "Müşteri"
                tel=v.get("telefon","")
                isl=v.get("islem_tipi","")
                mulk=v.get("mulk_tipi","")
                butce=v.get("butce","")
                krit=v.get("kriterler","")
                ozet=v.get("ozet","")
                takip=v.get("takip_durumu","")
                gun=gun_f(v.get("olusturma_tarihi",""))
                _ilce=ilce_oz(v)
                dot="#16a34a" if gun<=7 else "#355C7D"
                etiket=bdg(isl)+bdg(mulk)

                st.markdown(
                    f'<div class="talep-kart" style="border-left:3px solid {dot};">'
                    f'<div class="talep-kart-baslik">{musa}'
                    +(f' <span style="font-size:11px;color:#94a3b8;font-weight:400">· {tel}</span>' if tel else "")
                    +f'</div>'
                    f'<div class="talep-kart-meta">'
                    f'<span style="font-weight:600;color:#355C7D">{_ilce or "—"}</span>'
                    +(f'<span style="font-weight:700;color:#0F172A">{butce}</span>' if butce else "")
                    +(f'<span style="color:#475569">{takip}</span>' if takip else "")
                    +f'<span style="color:#94a3b8">{tarih_et(gun)}</span>'
                    +f'</div>'
                    +(f'<div style="font-size:11px;color:#64748B;margin-top:3px;font-style:italic;">{(ozet or krit)[:100]}</div>' if ozet or krit else "")
                    +f'<div style="margin-top:4px">{etiket}</div>'
                    f'</div>',
                    unsafe_allow_html=True
                )

                _ba,_bb,_bc,_bd,_be=st.columns([1,1.8,1.8,1,3])
                with _ba:
                    if st.button("✏",key=f"t_dz_{kid}",use_container_width=True,help="Düzenle"):
                        st.session_state[f"t_dz_a_{kid}"]=not st.session_state.get(f"t_dz_a_{kid}",False); st.rerun()
                with _bb:
                    _ofis_lbl = "✅ Ofiste" if st.session_state.get(f"t_ofis_{kid}") else "🏢 Ofise Paylaş"
                    if st.button(_ofis_lbl,key=f"t_ofis_{kid}_btn",use_container_width=True):
                        if ofise_paylas(v, st.session_state.get("user_name","")):
                            st.session_state[f"t_ofis_{kid}"]=True
                            st.toast("✅ Talep ofis havuzuna eklendi!")
                with _bc:
                    if st.button("📧 Startkey'e Gönder",key=f"t_mail_{kid}",use_container_width=True):
                        with st.spinner("Mail gönderiliyor..."):
                            if startkey_mail_gonder(v, st.session_state.get("user_name","")):
                                st.toast("✅ Talep Startkey'e mail olarak gönderildi!")
                with _bd:
                    if st.button("🗑",key=f"t_sil_{kid}",use_container_width=True,help="Sil"):
                        st.session_state[f"t_sil_onay_{kid}"]=True; st.rerun()

                if st.session_state.get(f"t_sil_onay_{kid}"):
                    st.warning(f"**{musa}** kaydını silmek istiyor musunuz?")
                    _sc1,_sc2=st.columns([1,4])
                    with _sc1:
                        if st.button("Evet, Sil",key=f"t_sil_evet_{kid}",type="primary"):
                            try:
                                get_client().table("musteriler").delete().eq("id",kid).execute()
                                st.cache_data.clear()
                                st.session_state.pop(f"t_sil_onay_{kid}",None)
                                st.rerun()
                            except Exception as e: st.error(f"Hata: {e}")
                    with _sc2:
                        if st.button("İptal",key=f"t_sil_iptal_{kid}"):
                            st.session_state.pop(f"t_sil_onay_{kid}",None); st.rerun()

                if st.session_state.get(f"t_dz_a_{kid}",False):
                    with st.container(border=True):
                        d1,d2,d3=st.columns(3)
                        with d1:
                            da=st.text_input("Müşteri Adı",value=v.get("musteri_adi",""),key=f"td_a_{kid}")
                            dt=st.text_input("Telefon",value=v.get("telefon",""),key=f"td_t_{kid}")
                            di=st.selectbox("İşlem",ISLEM,
                                index=ISLEM.index(v.get("islem_tipi","Belirsiz")) if v.get("islem_tipi") in ISLEM else 2,
                                key=f"td_i_{kid}")
                        with d2:
                            dm=st.selectbox("Mülk",MULK,
                                index=MULK.index(v.get("mulk_tipi","Belirsiz")) if v.get("mulk_tipi") in MULK else 3,
                                key=f"td_m_{kid}")
                            db=st.text_input("Bütçe",value=v.get("butce",""),key=f"td_b_{kid}")
                            do=st.text_input("Oda/M²",value=v.get("oda_sayisi",""),key=f"td_o_{kid}")
                        with d3:
                            dk=st.text_area("Kriterler/Notlar",value=v.get("kriterler",""),height=80,key=f"td_k_{kid}")
                            dtk=st.selectbox("Takip",TAKIP,
                                index=TAKIP.index(v.get("takip_durumu","Aktif")) if v.get("takip_durumu") in TAKIP else 0,
                                key=f"td_tk_{kid}")
                        s1,s2=st.columns([1,4])
                        with s1:
                            if st.button("💾 Kaydet",key=f"td_sv_{kid}",type="primary"):
                                try:
                                    get_client().table("musteriler").update({
                                        "musteri_adi":da,"telefon":dt,"islem_tipi":di,
                                        "mulk_tipi":dm,"butce":db,"oda_sayisi":do,
                                        "kriterler":dk,"takip_durumu":dtk
                                    }).eq("id",kid).execute()
                                    st.cache_data.clear()
                                    st.session_state[f"t_dz_a_{kid}"]=False
                                    st.success("Güncellendi!"); st.rerun()
                                except Exception as e: st.error(f"Hata: {e}")
                        with s2:
                            if st.button("İptal",key=f"td_ip_{kid}"):
                                st.session_state[f"t_dz_a_{kid}"]=False; st.rerun()

                st.markdown("<div style='height:2px'></div>",unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1: PORTFÖYLERİM  (artık 1. sekme)
# ══════════════════════════════════════════════════════════════════════════════
with tab1:
    # ── Admin GD seçici ───────────────────────────────────────────────────────
    _rol = st.session_state.get("user_role","danisan")
    _gorunum_gd = None  # None = kendi portföyleri, string = seçili GD

    if _rol in ("admin","yonetici"):
        _gd_listesi = gd_listesi_cek()
        _gd_col1, _gd_col2 = st.columns([2,5])
        with _gd_col1:
            _gd_sec = st.selectbox(
                "👁 GD Görünümü",
                ["— Kendi Portföylerim —"] + _gd_listesi,
                key="admin_gd_sec",
                help="Admin: başka bir danışmanın portföylerini görüntüle"
            )
        if _gd_sec != "— Kendi Portföylerim —":
            _gorunum_gd = _gd_sec
            st.markdown(
                f'<div style="font-size:12px;background:#FFF9ED;border-radius:8px;' +
                f'padding:8px 12px;margin-bottom:10px;border-left:3px solid #F4B740;">' +
                f'<strong>👁 Yönetici Görünümü:</strong> {_gd_sec} portföyleri gösteriliyor.' +
                f'</div>',
                unsafe_allow_html=True
            )
        else:
            st.markdown("""
            <div style="font-size:12px;color:#64748B;background:#EEF4FA;border-radius:8px;
            padding:8px 12px;margin-bottom:14px;border-left:3px solid #1E3A5F;">
            Kendi portföy kayıtlarınız. <strong>Malik bilgileri yalnızca size görünür.</strong>
            </div>""", unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="font-size:12px;color:#64748B;background:#EEF4FA;border-radius:8px;
        padding:8px 12px;margin-bottom:14px;border-left:3px solid #1E3A5F;">
        Kendi portföy kayıtlarınız. <strong>Malik bilgileri yalnızca size görünür.</strong>
        </div>""", unsafe_allow_html=True)

    # ── Yeni Portföy Formu ────────────────────────────────────────────────────
    if not _gorunum_gd:  # Admin başka GD'yi izlerken yeni portföy ekleyemez
        if not st.session_state.get("p_form_ac",False):
            if st.button("+ Yeni Portföy Ekle",key="p_form_btn",type="primary"):
                st.session_state["p_form_ac"]=True
                st.session_state.pop("p_parse",None)
                st.rerun()
        else:
            with st.container(border=True):
                st.markdown("**Yeni Portföy**")

                yontem_p=st.radio("Giriş yöntemi",["🤖 AI ile Analiz","📝 Form"],
                    horizontal=True,key="p_yontem",label_visibility="collapsed")

                parse_p=st.session_state.get("p_parse",{})

                if "AI" in yontem_p:
                    _pc1,_pc2=st.columns([3,1])
                    with _pc1:
                        metin_p=st.text_area("Portföy açıklaması",height=80,key="p_metin",
                            placeholder="Örn: Bornova'da 3+1 satılık daire, 8.5 milyon TL, 120 m², yeni bina, asansörlü...",
                            label_visibility="collapsed")
                    with _pc2:
                        st.markdown("<div style='height:28px'></div>",unsafe_allow_html=True)
                        if st.button("🤖 AI Analiz",key="p_ai_btn",type="primary",use_container_width=True):
                            if metin_p.strip():
                                with st.spinner("Analiz ediliyor..."):
                                    sonuc_p=ai_parse_portfoy(metin_p)
                                    if "_hata" in sonuc_p: st.error(f"AI hatası: {sonuc_p['_hata']}")
                                    else:
                                        lk_p=mahalle_bul(sonuc_p.get("mahalle","") or metin_p)
                                        if lk_p:
                                            sonuc_p["il"]=lk_p.get("il","")
                                            sonuc_p["ilce"]=lk_p.get("ilce","")
                                            if not sonuc_p.get("mahalle"): sonuc_p["mahalle"]=lk_p.get("mahalle","")
                                        st.session_state["p_parse"]=sonuc_p; st.rerun()
                            else: st.warning("Açıklama girin.")
                    if parse_p: st.markdown("**✅ AI analiz tamamlandı — düzenleyebilirsiniz:**")
                else:
                    parse_p={}

                if "Form" in yontem_p or parse_p:
                    _pf1,_pf2,_pf3=st.columns(3)
                    with _pf1:
                        _p_malik=st.text_input("Malik Adı *",key="p_malik",placeholder="Ad Soyad")
                        _p_tel=st.text_input("Malik Telefonu",key="p_tel",placeholder="+90 5xx")
                        _p_il=st.selectbox("İl",ILLER,key="p_il",
                            index=ILLER.index(parse_p.get("il","İzmir")) if parse_p.get("il","") in ILLER else 0)
                    with _pf2:
                        _p_islem=st.selectbox("İşlem Tipi",ISLEM,key="p_islem",
                            index=ISLEM.index(parse_p.get("islem_tipi","Belirsiz")) if parse_p.get("islem_tipi","") in ISLEM else 2)
                        _p_mulk=st.selectbox("Mülk Tipi",MULK,key="p_mulk",
                            index=MULK.index(parse_p.get("mulk_tipi","Belirsiz")) if parse_p.get("mulk_tipi","") in MULK else 3)
                        _p_fiyat=st.text_input("Fiyat",key="p_fiyat",value=parse_p.get("fiyat",""),
                            placeholder="ör: 8.500.000 TL")
                    with _pf3:
                        _p_oda=st.text_input("Oda/M²",key="p_oda",value=parse_p.get("oda_sayisi_m2",""),
                            placeholder="ör: 3+1")
                        _p_ilce_raw=parse_p.get("ilce","")
                        _p_ilce=st.selectbox("Birincil İlçe",["—"]+_ILC,key="p_ilce",
                            index=([""]+_ILC).index(_p_ilce_raw)+1 if _p_ilce_raw in _ILC else 0)
                        _p_kapali=st.checkbox("Kapalı Portföy (fiyat gizli)",key="p_kapali")

                    _p_mahalle=st.text_input("Mahalle/Semt",key="p_mahalle",value=parse_p.get("mahalle",""))
                    _p_ozet=st.text_input("Özet",key="p_ozet",value=parse_p.get("ozet",""),
                        placeholder="ör: Bornova satılık 3+1 daire, yeni bina")
                    _p_ozel=st.text_area("Özellikler / İç Notlar",height=70,key="p_ozel",
                        value=parse_p.get("ozellikler",""),
                        placeholder="Eşyalı, asansörlü, otoparklı... Malik notları")
                    _p_link=st.text_input("İlan Linki (opsiyonel)",key="p_link",value=parse_p.get("ilan_linki",""))

                    pka,pkb=st.columns([1.2,6])
                    with pka:
                        if st.button("💾 Kaydet",key="p_kaydet",type="primary"):
                            if not _id_alan:
                                st.error("Oturum bilgisi eksik.")
                            else:
                                _p_ilce_val="" if _p_ilce=="—" else _p_ilce
                                veri_p={
                                    _id_alan:_id_deger,
                                    "malik_adi":_p_malik.strip(),
                                    "malik_tel":_p_tel.strip(),
                                    "islem_tipi":_p_islem,
                                    "mulk_tipi":_p_mulk,
                                    "il":_p_il,
                                    "ilce":_p_ilce_val,
                                    "ilceler":[_p_ilce_val] if _p_ilce_val else [],
                                    "fiyat":_p_fiyat.strip(),
                                    "oda_sayisi_m2":_p_oda.strip(),
                                    "bolge_mahalle":_p_mahalle.strip(),
                                    "ozet":_p_ozet.strip(),
                                    "ozellikler":_p_ozel.strip(),
                                    "ilan_linki":_p_link.strip(),
                                    "kapali_portfoy":_p_kapali,
                                    "talep_eden_danisan":st.session_state.get("user_name",""),
                                    "kaynak":"danisan",
                                    "gizli":False,
                                    "olusturma_tarihi":datetime.now().isoformat(),
                                }
                                if portfoy_kaydet_fn(veri_p):
                                    st.session_state["p_form_ac"]=False
                                    st.session_state.pop("p_parse",None)
                                    st.success("✅ Portföy kaydedildi!")
                                    st.rerun()
                    with pkb:
                        if st.button("İptal",key="p_iptal"):
                            st.session_state["p_form_ac"]=False
                            st.session_state.pop("p_parse",None)
                            st.rerun()

    st.markdown("<div style='height:8px'></div>",unsafe_allow_html=True)

    # ── Portföy listesi ───────────────────────────────────────────────────────
    if not _id_alan:
        st.warning("Oturum bilgisi eksik.")
    else:
        if _gorunum_gd:
            portfoyler = portfoyler_gd_cek(_gorunum_gd)
            # Admin GD görünümü — Ofis Paneli filtre/liste/kart/tablo altyapısı
            if gd_portfoy_goster:
                gd_portfoy_goster(portfoyler, prefix=f"gd_{_gorunum_gd[:8].replace(' ','_')}")
            else:
                st.warning("gd_portfoy_view modülü yüklenemedi.")
                for v in portfoyler[:5]:
                    st.json(v)
            st.stop()
        else:
            portfoyler = portfoyler_cek(_id_alan,_id_deger)

        if not portfoyler:
            st.info("Henüz portföy kaydınız yok. Yukarıdan yeni portföy ekleyin.")
        else:
            _pfa,_pfb,_pfc=st.columns([2,1.5,1.5])
            with _pfa: _p_ara=st.text_input("Ara",key="pm_ara",placeholder="İlçe, özet, malik...",label_visibility="collapsed")
            with _pfb: _p_isl_f=st.selectbox("İşlem",["Tümü"]+ISLEM[:-1],key="pm_isl",label_visibility="collapsed")
            with _pfc: _p_mul_f=st.selectbox("Mülk",["Tümü"]+MULK[:-1],key="pm_mul",label_visibility="collapsed")

            pf=portfoyler[:]
            if _p_ara: pf=[v for v in pf if any(_p_ara.lower() in str(v.get(k,"")).lower() for k in ["malik_adi","ozet","ilce","il","bolge_mahalle","ozellikler"])]
            if _p_isl_f!="Tümü": pf=[v for v in pf if v.get("islem_tipi","")==_p_isl_f]
            if _p_mul_f!="Tümü": pf=[v for v in pf if v.get("mulk_tipi","")==_p_mul_f]

            st.caption(f"{len(pf)} portföy")

            for v in pf:
                kid=v.get("id","")
                malik=v.get("malik_adi","") or "Malik"
                mtel=v.get("malik_tel","")
                isl=v.get("islem_tipi","")
                mulk=v.get("mulk_tipi","")
                fiyat=v.get("fiyat","")
                oda=v.get("oda_sayisi_m2","")
                ozet=v.get("ozet","")
                ozel=v.get("ozellikler","")
                gun=gun_f(v.get("olusturma_tarihi",""))
                _ilce=ilce_oz(v) or v.get("bolge_mahalle","") or ""
                kap=v.get("kapali_portfoy",False)
                dot="#1E3A5F" if gun<=7 else "#94a3b8"
                etiket=bdg(isl)+bdg(mulk)
                if kap: etiket+='<span class="badge" style="background:#fef9c3;color:#713f12;border:1px solid #fde68a;">Kapalı</span>'

                st.markdown(
                    f'<div class="talep-kart" style="border-left:3px solid {dot};">'
                    f'<div class="talep-kart-baslik">{ozet or f"{isl} {mulk}".strip() or "Portföy"}'
                    +f'</div>'
                    f'<div class="talep-kart-meta">'
                    f'<span style="font-weight:600;color:#355C7D">{_ilce or "—"}</span>'
                    +(f'<span style="background:#EEF4FA;color:#1E3A5F;border:1px solid #DCE4EE;border-radius:8px;font-weight:700;padding:1px 8px;">{fiyat}</span>' if fiyat and not kap else "")
                    +(f'<span style="color:#475569">{oda}</span>' if oda else "")
                    +f'<span style="color:#64748B;font-weight:600">Malik: {malik}'+(f" · {mtel}" if mtel else "")+'</span>'
                    +f'<span style="color:#94a3b8">{tarih_et(gun)}</span>'
                    +f'</div>'
                    +(f'<div style="font-size:11px;color:#64748B;margin-top:3px;font-style:italic;">{ozel[:100]}</div>' if ozel else "")
                    +f'<div style="margin-top:4px">{etiket}</div>'
                    f'</div>',
                    unsafe_allow_html=True
                )

                _pba,_pbb,_pbc=st.columns([1,1,5])
                with _pba:
                    if st.button("✏",key=f"p_dz_{kid}",use_container_width=True,help="Düzenle"):
                        st.session_state[f"p_dz_a_{kid}"]=not st.session_state.get(f"p_dz_a_{kid}",False); st.rerun()
                with _pbb:
                    if st.button("🗑",key=f"p_sil_{kid}",use_container_width=True,help="Sil"):
                        st.session_state[f"p_sil_onay_{kid}"]=True; st.rerun()

                if st.session_state.get(f"p_sil_onay_{kid}"):
                    st.warning(f"Bu portföyü silmek istiyor musunuz?")
                    _ps1,_ps2=st.columns([1,4])
                    with _ps1:
                        if st.button("Evet, Sil",key=f"p_sil_evet_{kid}",type="primary"):
                            try:
                                get_client().table("portfoyler").delete().eq("id",kid).execute()
                                st.cache_data.clear()
                                st.session_state.pop(f"p_sil_onay_{kid}",None)
                                st.rerun()
                            except Exception as e: st.error(f"Hata: {e}")
                    with _ps2:
                        if st.button("İptal",key=f"p_sil_iptal_{kid}"):
                            st.session_state.pop(f"p_sil_onay_{kid}",None); st.rerun()

                if st.session_state.get(f"p_dz_a_{kid}",False):
                    with st.container(border=True):
                        d1,d2,d3=st.columns(3)
                        with d1:
                            dm_a=st.text_input("Malik Adı",value=v.get("malik_adi",""),key=f"pd_a_{kid}")
                            dm_t=st.text_input("Malik Tel",value=v.get("malik_tel",""),key=f"pd_t_{kid}")
                            dm_i=st.selectbox("İşlem",ISLEM,
                                index=ISLEM.index(v.get("islem_tipi","Belirsiz")) if v.get("islem_tipi") in ISLEM else 2,
                                key=f"pd_i_{kid}")
                        with d2:
                            dm_m=st.selectbox("Mülk",MULK,
                                index=MULK.index(v.get("mulk_tipi","Belirsiz")) if v.get("mulk_tipi") in MULK else 3,
                                key=f"pd_m_{kid}")
                            dm_f=st.text_input("Fiyat",value=v.get("fiyat",""),key=f"pd_f_{kid}")
                            dm_o=st.text_input("Oda/M²",value=v.get("oda_sayisi_m2",""),key=f"pd_o_{kid}")
                        with d3:
                            dm_oz=st.text_input("Özet",value=v.get("ozet",""),key=f"pd_oz_{kid}")
                            dm_ozel=st.text_area("İç Notlar",value=v.get("ozellikler",""),height=80,key=f"pd_ozel_{kid}")
                            dm_kap=st.checkbox("Kapalı",value=v.get("kapali_portfoy",False),key=f"pd_kap_{kid}")
                        s1,s2=st.columns([1,4])
                        with s1:
                            if st.button("💾 Kaydet",key=f"pd_sv_{kid}",type="primary"):
                                try:
                                    get_client().table("portfoyler").update({
                                        "malik_adi":dm_a,"malik_tel":dm_t,"islem_tipi":dm_i,
                                        "mulk_tipi":dm_m,"fiyat":dm_f,"oda_sayisi_m2":dm_o,
                                        "ozet":dm_oz,"ozellikler":dm_ozel,"kapali_portfoy":dm_kap
                                    }).eq("id",kid).execute()
                                    st.cache_data.clear()
                                    st.session_state[f"p_dz_a_{kid}"]=False
                                    st.success("Güncellendi!"); st.rerun()
                                except Exception as e: st.error(f"Hata: {e}")
                        with s2:
                            if st.button("İptal",key=f"pd_ip_{kid}"):
                                st.session_state[f"p_dz_a_{kid}"]=False; st.rerun()

                st.markdown("<div style='height:2px'></div>",unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# ══════════════════════════════════════════════════════════════════════════════
# ══════════════════════════════════════════════════════════════════════════════
# TAB 3: TAKİP LİSTEM
# ══════════════════════════════════════════════════════════════════════════════
with tab3:
    st.markdown("""
    <div style="font-size:12px;color:#64748B;background:#FFF9ED;border-radius:8px;
    padding:8px 12px;margin-bottom:14px;border-left:3px solid #F4B740;">
    Talep ve Portföy Havuzundan takibe aldığınız kayıtlar.
    <strong>Bilgileri düzenleyip sunuma hazırlayabilirsiniz.</strong>
    </div>""", unsafe_allow_html=True)

    _takip_listesi = st.session_state.get("takip_listesi", {})

    if not _takip_listesi:
        st.info("Henüz takip listesinde kayıt yok.\n\nTalep Havuzu, Portföy Havuzu veya Ofis Paneli'nden '☆ Takibe Al' butonuyla kayıt ekleyebilirsiniz.")
    else:
        _takip_portfoy = {k:v for k,v in _takip_listesi.items()
                          if v.get("_takip_kaynak") in ("portfoy_havuzu","ofis_paneli","gd_kokpit")}
        _takip_talep   = {k:v for k,v in _takip_listesi.items()
                          if v.get("_takip_kaynak") not in ("portfoy_havuzu","ofis_paneli","gd_kokpit")}

        _tk_tab1, _tk_tab2 = st.tabs([
            f"🏠 Portföyler ({len(_takip_portfoy)})",
            f"📋 Talepler ({len(_takip_talep)})",
        ])

        def _render_takip(items_dict):
            if not items_dict:
                st.info("Bu kategoride takip kaydı yok.")
                return

            for _tkid, _tv in list(items_dict.items()):
                _tkaynak = _tv.get("_takip_kaynak","")
                _tkaynak_lbl = {
                    "talep_havuzu":"📋 Talep",
                    "portfoy_havuzu":"🏠 Portföy",
                    "ofis_paneli":"🏢 Ofis",
                    "gd_kokpit":"🏠 GD",
                }.get(_tkaynak, _tkaynak)

                # Mevcut değerleri al (düzenlendiyse günceli kullan)
                _tisl   = _tv.get("islem_tipi","") or ""
                _tmulk  = _tv.get("mulk_tipi","") or ""
                _tilce  = _tv.get("ilce","") or ""
                _tmah   = _tv.get("mahalle","") or _tv.get("bolge_mahalle","") or ""
                _tfiyat = _tv.get("fiyat","") or _tv.get("max_butce","") or _tv.get("butce","") or ""
                _toda   = _tv.get("oda_sayisi_m2","") or _tv.get("oda_sayisi","") or ""
                _tm2    = str(_tv.get("m2","") or "")
                _tozet  = _tv.get("ozet","") or _tv.get("baslik","") or f"{_tisl} {_tmulk}".strip()
                _tozel  = _tv.get("ozellikler","") or _tv.get("ozel_kriterler","") or ""
                _tkat   = str(_tv.get("kat","") or "")
                _tyas   = str(_tv.get("bina_yasi","") or "")
                _tdan   = (_tv.get("talep_eden_danisan","") or "").split("<")[0].strip().strip('"')
                _tlink  = _tv.get("ilan_linki","") or _tv.get("startkey_detay_link","") or ""
                _tnot   = st.session_state.get(f"tnot_{_tkid}", _tv.get("_not",""))
                _dz_ac  = st.session_state.get(f"tdz_{_tkid}", False)

                # Kart
                st.markdown(
                    f'<div style="border:1px solid #e2e8f0;border-left:4px solid #F4B740;'
                    f'border-radius:12px;background:#fff;margin-bottom:4px;overflow:hidden;">'
                    f'<div style="padding:10px 15px 8px;">'
                    f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:2px;">'
                    f'<span style="font-size:11px;font-weight:700;color:#355C7D;">'
                    f'{(_tilce or "—") + (" · " + _tmah if _tmah else "")}</span>'
                    f'<span style="font-size:10px;font-weight:600;background:#FFF9ED;color:#92400e;'
                    f'padding:1px 8px;border-radius:999px;">{_tkaynak_lbl}</span>'
                    f'</div>'
                    f'<div style="font-size:13px;font-weight:700;color:#0F172A;margin-bottom:3px;'
                    f'white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{str(_tozet)[:70]}</div>'
                    f'<div style="font-size:11px;color:#64748B;display:flex;gap:8px;flex-wrap:wrap;">'
                    +(f'<span style="font-size:13px;font-weight:800;color:#0F172A;">{_tfiyat}</span>' if _tfiyat else "")
                    +(f'<span>{_toda}</span>' if _toda else "")
                    +(f'<span>{_tm2} m²</span>' if _tm2 and _tm2 not in ("","None","nan") else "")
                    +f'<span style="color:#94a3b8;">{_tdan}</span>'
                    +f'</div>'
                    +(_tnot and f'<div style="font-size:11px;color:#355C7D;margin-top:3px;'
                      f'background:#EEF4FA;border-radius:6px;padding:3px 8px;">📝 {_tnot[:80]}</div>' or "")
                    +f'</div>'
                    f'<div style="border-top:1px solid #f1f5f9;padding:5px 15px;background:#f8fafc;"></div>'
                    f'</div>',
                    unsafe_allow_html=True
                )

                # Butonlar
                _b1, _b2, _b3, _ = st.columns([1.8, 1.6, 1.2, 3.4])
                with _b1:
                    if st.button("📊 Sunuma Hazırla", key=f"tk_sun_{_tkid}",
                                 use_container_width=True, type="primary"):
                        st.session_state["sunum_portfoy"] = dict(_tv)
                        st.session_state["sunum_kaynak"]  = "takip_listesi"
                        st.switch_page("pages/Sunum_Merkezi_V2_Demo.py")
                with _b2:
                    _dz_lbl = "✏ Düzenlemeyi Kapat" if _dz_ac else "✏ Düzenle"
                    if st.button(_dz_lbl, key=f"tk_dz_btn_{_tkid}", use_container_width=True):
                        st.session_state[f"tdz_{_tkid}"] = not _dz_ac
                        st.rerun()
                with _b3:
                    if st.button("🗑 Kaldır", key=f"tk_sil_{_tkid}", use_container_width=True):
                        _takip_listesi.pop(_tkid, None)
                        for _pfx in ["takip_t_","takip_p_","takip_o_"]:
                            st.session_state.pop(f"{_pfx}{_tkid}", None)
                        st.toast("Takip listesinden kaldırıldı.")
                        st.rerun()

                # Düzenleme formu
                if _dz_ac:
                    with st.container(border=True):
                        st.markdown("**✏ Bilgileri Düzenle** — Sunum başlığı, fiyat, konum ve özellikler")
                        _f1, _f2, _f3 = st.columns(3)
                        with _f1:
                            _ISLEM = ["Satılık","Kiralık","Belirsiz"]
                            _dz_islem = st.selectbox("İşlem Tipi", _ISLEM,
                                index=_ISLEM.index(_tisl) if _tisl in _ISLEM else 2,
                                key=f"tdf_islem_{_tkid}")
                            _MULK = ["Konut","İşyeri","Arsa","Belirsiz"]
                            _dz_mulk = st.selectbox("Mülk Tipi", _MULK,
                                index=_MULK.index(_tmulk) if _tmulk in _MULK else 3,
                                key=f"tdf_mulk_{_tkid}")
                            _dz_fiyat = st.text_input("Fiyat / Bütçe",
                                value=_tfiyat, key=f"tdf_fiyat_{_tkid}",
                                placeholder="ör: 8.500.000 TL")
                        with _f2:
                            _dz_ilce = st.text_input("İlçe",
                                value=_tilce, key=f"tdf_ilce_{_tkid}")
                            _dz_mah = st.text_input("Mahalle / Semt",
                                value=_tmah, key=f"tdf_mah_{_tkid}")
                            _dz_oda = st.text_input("Oda / M²",
                                value=_toda, key=f"tdf_oda_{_tkid}",
                                placeholder="ör: 3+1")
                        with _f3:
                            _dz_m2 = st.text_input("Brüt M²",
                                value=_tm2, key=f"tdf_m2_{_tkid}",
                                placeholder="ör: 120")
                            _dz_kat = st.text_input("Kat",
                                value=_tkat, key=f"tdf_kat_{_tkid}",
                                placeholder="ör: 3. Kat")
                            _dz_yas = st.text_input("Bina Yaşı",
                                value=_tyas, key=f"tdf_yas_{_tkid}",
                                placeholder="ör: 5-10 yıl")

                        _dz_ozet = st.text_input("Sunum Başlığı",
                            value=_tozet[:80], key=f"tdf_ozet_{_tkid}",
                            placeholder="Sunumda görünecek başlık")
                        _dz_ozel = st.text_area("Özellikler / Açıklama",
                            value=_tozel, height=80, key=f"tdf_ozel_{_tkid}",
                            placeholder="Eşyalı, site içi, asansörlü, deniz manzaralı...")
                        _dz_not = st.text_area("Özel Notunuz (sunuma dahil olmaz)",
                            value=_tnot, height=60, key=f"tdf_not_{_tkid}",
                            placeholder="Kendinize özel not...")

                        _link_txt = st.text_input("İlan Linki",
                            value=_tlink, key=f"tdf_link_{_tkid}")

                        _sv1, _sv2 = st.columns([1.2, 6])
                        with _sv1:
                            if st.button("💾 Güncelle", key=f"tk_sv_{_tkid}", type="primary"):
                                _takip_listesi[_tkid].update({
                                    "islem_tipi":    _dz_islem,
                                    "mulk_tipi":     _dz_mulk,
                                    "fiyat":         _dz_fiyat,
                                    "ilce":          _dz_ilce,
                                    "mahalle":       _dz_mah,
                                    "bolge_mahalle": _dz_mah,
                                    "oda_sayisi_m2": _dz_oda,
                                    "oda_sayisi":    _dz_oda,
                                    "m2":            _dz_m2,
                                    "kat":           _dz_kat,
                                    "bina_yasi":     _dz_yas,
                                    "ozet":          _dz_ozet,
                                    "ozellikler":    _dz_ozel,
                                    "ilan_linki":    _link_txt,
                                    "_not":          _dz_not,
                                })
                                st.session_state[f"tnot_{_tkid}"] = _dz_not
                                st.session_state[f"tdz_{_tkid}"]  = False
                                st.success("✅ Güncellendi! Artık sunuma hazırlayabilirsiniz.")
                                st.rerun()
                        with _sv2:
                            if st.button("İptal", key=f"tk_ip_{_tkid}"):
                                st.session_state[f"tdz_{_tkid}"] = False
                                st.rerun()

                st.markdown("<div style='height:2px'></div>", unsafe_allow_html=True)

        with _tk_tab1:
            _render_takip(_takip_portfoy)
        with _tk_tab2:
            _render_takip(_takip_talep)

# TAB 4: SUNUM MERKEZİ
# ══════════════════════════════════════════════════════════════════════════════
with tab4:
    st.markdown("""
    <div style="font-size:12px;color:#64748B;background:#FFF9ED;border-radius:8px;
    padding:8px 12px;margin-bottom:20px;border-left:3px solid #F4B740;">
    Portföy veya talep seçerek sunum materyali oluşturun.
    </div>""", unsafe_allow_html=True)

    sunum_items=[
        ("📄","Noname Broşür","Portföy sahibini gizleyen, kendi iletişim bilgilerinizle paylaşabileceğiniz broşür","Sunum_Merkezi_V2_Demo.py"),
        ("✉️","Mail Sunumu","Müşterinize göndermek için hazır HTML mail şablonu","Sunum_Merkezi_V2_Demo.py"),
        ("💬","WhatsApp Kartı","WhatsApp'ta paylaşmak için kart görseli","Sunum_Merkezi_V2_Demo.py"),
        ("📱","Story Tasarımı","Instagram/WhatsApp story formatı","Sunum_Merkezi_V2_Demo.py"),
        ("🌐","Landing Page","Paylaşılabilir ilan sayfası","Sunum_Merkezi_V2_Demo.py"),
    ]

    cols=st.columns(len(sunum_items),gap="small")
    for col,(ikon,baslik,aciklama,hedef) in zip(cols,sunum_items):
        with col:
            st.markdown(
                f'<div style="border:1px solid var(--border);border-radius:12px;padding:16px 14px;'
                f'background:#fff;text-align:center;min-height:130px;">'
                f'<div style="font-size:24px;margin-bottom:8px;">{ikon}</div>'
                f'<div style="font-size:12px;font-weight:700;color:var(--text);margin-bottom:6px;">{baslik}</div>'
                f'<div style="font-size:10.5px;color:var(--muted);line-height:1.5;">{aciklama}</div>'
                f'</div>',
                unsafe_allow_html=True
            )
            if st.button(f"{baslik} →",key=f"sunum_{baslik}",use_container_width=True,type="primary"):
                st.switch_page(f"pages/{hedef}")

# ── ALT BİLGİ ────────────────────────────────────────────────────────────────
st.markdown("""
<div style="text-align:center;margin-top:24px;padding-top:12px;border-top:1px solid #e2e8f0;">
  <span style="font-size:11px;color:#94a3b8;font-weight:500;">Zeta Panel · Startkey Gayrimenkul</span>
</div>""", unsafe_allow_html=True)
