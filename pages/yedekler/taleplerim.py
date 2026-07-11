import streamlit as st
import sys, os, re
from datetime import datetime
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
@st.cache_data(ttl=120)
def _tum_portfoyler_esleme_icin():
    """Eşleşme motoru için TÜM portföyleri çeker — aktif/pasif ayrımını
    match_engine kendi içinde yapıyor (coalesce(aktif,true) mantığı),
    burada filtre uygulamıyoruz. Sadece okuma, veritabanına yazmıyor."""
    try:
        r = get_client().table("portfoyler").select("*").execute()
        return r.data or []
    except Exception:
        return []


@st.cache_data(ttl=120)
def _startkey_agi_ilanlari_esleme_icin():
    """izmir_pazar_ilanlar'dan Startkey ağı ilanlarını çeker (marka filtresi
    match_engine içinde uygulanıyor, burada sadece aktif olanları çekip
    veri boyutunu makul tutuyoruz). Sadece okuma."""
    try:
        r = (
            get_client().table("izmir_pazar_ilanlar")
            .select("*")
            .eq("marka", "startkey")
            .eq("aktif", True)
            .execute()
        )
        return r.data or []
    except Exception:
        return []


def _esleme_satiri_ciz(sonuc, index=0):
    """Tek bir eşleşme sonucunu (skor+gerekçe+portföy özeti) kart olarak çizer
    ve kaynağa göre tıklanabilir bir aksiyon ekler:
    - Startkey Ağı kayıtları -> gerçek ilan linkine git
    - Zeta Portföyü / Kapalı kayıtlar -> Portföylerim'de o kayıt seçili açılır"""
    p = sonuc["portfoy"]
    renk = "#16A34A" if sonuc["seviye"] == "güçlü" else "#D97706"
    ozet_s = str(p.get("ozet") or "—").replace("<", "&lt;").replace(">", "&gt;")
    fiyat_s = str(p.get("fiyat") or "—")
    ilce_s = str(p.get("ilce") or "—")
    gorunurluk_etiket = {
        "kapali_portfoy": "🔒 Kapalı Portföy",
        "kapali_adayi": "🔒 Kapalı Aday",
        "ilandaki_portfoy": "🏠 Zeta Portföyü",
        "startkey_agi": "🌐 Startkey Ağı",
    }.get(p.get("portfoy_gorunurluk", ""), p.get("portfoy_gorunurluk") or "—")

    st.markdown(
        f'<div style="background:#fff;border:1px solid #e2e8f0;border-radius:10px;'
        f'padding:12px 14px;margin-bottom:4px;">'
        f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">'
        f'<span style="font-weight:700;color:{renk};font-size:14px;">{sonuc["skor"]}/100 · {sonuc["seviye"]}</span>'
        f'<span style="font-size:11px;color:#64748b;">{gorunurluk_etiket}</span>'
        f'</div>'
        f'<div style="font-size:13px;font-weight:600;color:#172B4D;margin-bottom:2px;">{ozet_s}</div>'
        f'<div style="font-size:12px;color:#64748b;">{ilce_s} · {fiyat_s}</div>'
        f'<div style="font-size:11px;color:#94a3b8;margin-top:4px;">{sonuc.get("gerekce","")}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    if p.get("ilan_linki"):
        st.link_button("🔗 İlanı Görüntüle", p["ilan_linki"], use_container_width=True)
    elif p.get("id"):
        _kapali_mi = p.get("portfoy_gorunurluk") in ("kapali_portfoy", "kapali_adayi")

        if _kapali_mi:
            # Kapalı fırsatlar için sayfa değiştirmiyoruz — 3_Portfoy_Tablosu.py
            # varsayılan olarak "Son 7 gün" hızlı tarih filtresiyle çalışıyor
            # ve bu, eski kapalı kayıtları sessizce gizliyor (kırılgan bir
            # yönlendirme olurdu). Bunun yerine tam kaydı BURADA, hiç sayfa
            # değiştirmeden gösteriyoruz — motor zaten tüm veriyi belleğinde
            # tutuyor.
            _detay_ac_key = f"tm_esleme_detay_acik_{index}_{p['id']}"
            if st.button("🔍 Detayları Gör", key=f"tm_esleme_detay_btn_{index}_{p['id']}",
                          use_container_width=True):
                st.session_state[_detay_ac_key] = not st.session_state.get(_detay_ac_key, False)

            if st.session_state.get(_detay_ac_key, False):
                _tam_kayit = next(
                    (v for v in _tum_portfoyler_esleme_icin() if str(v.get("id")) == str(p["id"])),
                    None,
                )
                if not _tam_kayit:
                    st.caption("Kayıt bulunamadı — silinmiş veya güncellenmiş olabilir.")
                else:
                    st.markdown(
                        f'<div style="background:#F8FAFC;border:1px dashed #cbd5e1;'
                        f'border-radius:8px;padding:10px 12px;margin-bottom:8px;'
                        f'font-size:12.5px;color:#334155;">'
                        f'<b>Danışman:</b> {str(_tam_kayit.get("talep_eden_danisan") or "—")}<br>'
                        f'<b>Özellikler:</b> {str(_tam_kayit.get("ozellikler") or "—")}<br>'
                        f'<b>Oda/m²:</b> {str(_tam_kayit.get("oda_sayisi_m2") or "—")}<br>'
                        f'<b>İşlem/Mülk:</b> {str(_tam_kayit.get("islem_tipi") or "—")} · '
                        f'{str(_tam_kayit.get("mulk_tipi") or "—")}'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
        else:
            if st.button("📂 Portföylerim'de Aç", key=f"tm_esleme_git_{index}_{p['id']}",
                          use_container_width=True):
                st.session_state["pm_selected_id"] = p["id"]
                st.session_state["pm_aktif_sekme"] = "detay"
                st.switch_page("pages/portfoylerím.py")
    st.markdown("<div style='margin-bottom:8px;'></div>", unsafe_allow_html=True)


def isim_ayikla(g):
    if not g: return ""
    if "<" in g: g = g[:g.index("<")].strip()
    return re.sub(r"[\"']", "", g).strip()

def tarih_parse(s):
    if not s: return None
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f%z","%Y-%m-%dT%H:%M:%S%z",
                "%Y-%m-%d %H:%M:%S","%Y-%m-%d","%d.%m.%Y"):
        try: return datetime.strptime(s[:25], fmt[:len(s[:25])])
        except: pass
    return None

def en_iyi_tarih(v):
    for k in ["kayit_tarihi","mail_tarihi","olusturma_tarihi","created_at"]:
        val = v.get(k)
        if val: return str(val)
    return ""

def tarih_str(v):
    d = tarih_parse(en_iyi_tarih(v))
    if not d: return "—"
    has_t = hasattr(d,"hour") and (d.hour!=0 or d.minute!=0)
    return d.strftime("%d.%m.%Y %H:%M") if has_t else d.strftime("%d.%m.%Y")

def ilce_grubu(v):
    ilceler = v.get("ilceler") or []
    ilce = v.get("ilce","") or ""
    tum = ([ilce] if ilce else []) + [i for i in ilceler if i!=ilce]
    tum = [i for i in tum if i and i!="Diğer Bölge"]
    return " · ".join(tum[:3]) if tum else (v.get("bolge_mahalle","") or "—")

def tip_badge(islem):
    islem = (islem or "").lower()
    if "kiralık" in islem or "kiralik" in islem: return "#f0fdf4","#166534","Kiralık"
    if "satılık" in islem or "satilik" in islem: return "#fef2f2","#991b1b","Satılık"
    return "#f8fafc","#64748b", islem or "—"

ILLER = ["İzmir","Aydın","Manisa","Balıkesir","Muğla","İstanbul","Ankara","Diğer"]

# ── Veri fonksiyonları ────────────────────────────────────────────────────────
@st.cache_data(ttl=60)
def ilce_listesi_cek():
    try:
        r = get_client().table("ilceler").select("ilce").execute()
        return sorted([x["ilce"] for x in r.data if x.get("ilce")])
    except: return []

@st.cache_data(ttl=60)
def zeta_gd_listesi():
    """Zeta 1 ve Zeta 2 portföylerindeki danışman isimlerini döndürür."""
    try:
        z1 = sorted(set(
            isim_ayikla(v.get("talep_eden_danisan",""))
            for v in (get_client().table("portfoyler").select("talep_eden_danisan")
                      .in_("kaynak",["zeta1"]).execute().data or [])
            if v.get("talep_eden_danisan","")
        ))
        z2 = sorted(set(
            isim_ayikla(v.get("talep_eden_danisan",""))
            for v in (get_client().table("portfoyler").select("talep_eden_danisan")
                      .in_("kaynak",["zeta2"]).execute().data or [])
            if v.get("talep_eden_danisan","")
        ))
        return z1, z2, sorted(set(z1+z2))
    except: return [], [], []

@st.cache_data(ttl=60)
def mahalle_lookup_cek():
    try:
        r = get_client().table("mahalleler").select("il,ilce,mahalle").execute()
        return {row["mahalle"].strip().lower(): (row["il"], row["ilce"]) for row in r.data}
    except: return {}

def mahalle_ile_ilce_bul(metin):
    if not metin: return {}
    lookup = mahalle_lookup_cek()
    metin_lower = metin.lower()
    eslesme = {}
    for mh_lower,(il,ilce) in lookup.items():
        if mh_lower in metin_lower:
            if not eslesme or len(mh_lower)>len(list(eslesme.keys())[0]):
                eslesme = {mh_lower:(il,ilce,mh_lower)}
    if eslesme:
        _,(il,ilce,mh) = list(eslesme.items())[0]
        return {"il":il,"ilce":ilce,"mahalle":mh}
    return {}

def talep_kaydet(veri):
    try:
        get_client().table("alici_talepleri").insert(veri).execute()
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Kayıt hatası: {e}"); return False

def favori_guncelle(kid, mevcut):
    try:
        get_client().table("alici_talepleri").update({"favori": not mevcut}).eq("id", kid).execute()
        st.cache_data.clear(); st.rerun(scope="app")
    except Exception as e:
        st.error(f"Hata: {e}")

def ai_parse_talep(metin):
    import requests, json
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
        resp = requests.post("https://api.anthropic.com/v1/messages",
            headers={"Content-Type":"application/json","x-api-key":api_key,"anthropic-version":"2023-06-01"},
            json={"model":"claude-sonnet-4-6","max_tokens":600,"messages":[{"role":"user","content":prompt}]},
            timeout=30)
        data = resp.json()
        if "error" in data: return {"_parse_hatasi": data["error"].get("message",str(data["error"]))}
        text = data["content"][0]["text"].strip().replace("```json","").replace("```","").strip()
        return json.loads(text)
    except Exception as e:
        return {"ozet":metin,"_parse_hatasi":str(e)}

@st.cache_data(ttl=60)
def benim_taleplerim(user_id, user_name):
    try:
        tum = get_client().table("alici_talepleri").select("*").eq("kategori","alici_talebi")\
            .order("olusturma_tarihi",desc=True).limit(500).execute().data or []
        sonuc = []
        goruldu = set()
        for v in tum:
            vid = v.get("id")
            if vid in goruldu: continue
            if user_id and v.get("user_id")==user_id:
                sonuc.append(v); goruldu.add(vid); continue
            if user_name and user_name.strip():
                un = user_name.lower().strip()
                gd = isim_ayikla(v.get("talep_eden_danisan","")).lower()
                if un in gd or gd in un:
                    sonuc.append(v); goruldu.add(vid); continue
                gg = isim_ayikla(v.get("giren_gd","")).lower()
                if gg and (un in gg or gg in un):
                    sonuc.append(v); goruldu.add(vid); continue
        return sonuc
    except Exception as e:
        st.error(f"Hata: {e}"); return []

@st.cache_data(ttl=60)
def favori_talepler():
    try:
        r = get_client().table("alici_talepleri").select("*").eq("favori",True)\
            .eq("kategori","alici_talebi").order("olusturma_tarihi",desc=True).limit(200).execute()
        return r.data or []
    except: return []

# ── Session ───────────────────────────────────────────────────────────────────
_k = st.session_state.get("kullanici", {})
user_id   = _k.get("id","")
user_name = _k.get("ad_soyad") or _k.get("ad","")

ilce_sec  = ilce_listesi_cek()
gd_list_z1, gd_list_z2, gd_list_tum = zeta_gd_listesi()

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
.tm-section-label {
    font-size:10px;font-weight:700;color:#94a3b8;text-transform:uppercase;
    letter-spacing:.08em;margin:16px 0 8px;border-bottom:1px solid #f1f5f9;padding-bottom:6px;
}
.dp-label{font-size:10px;font-weight:600;color:#94a3b8;text-transform:uppercase;letter-spacing:.06em;margin-bottom:2px;}
.dp-value{font-size:13px;color:#1e293b;font-weight:500;margin-bottom:10px;}
.dp-divider{border:none;border-top:1px solid #f1f5f9;margin:12px 0;}
</style>
""", unsafe_allow_html=True)

# ── Başlık ────────────────────────────────────────────────────────────────────
render_page_header("👤 Taleplerim", f"Takip listem ve kendi kayıtlarım · {user_name}")

# ── Veri ─────────────────────────────────────────────────────────────────────
talepler      = benim_taleplerim(user_id, user_name)
fav_talepler  = favori_talepler()
takip_sess    = st.session_state.get("takip_listesi", {})
fav_idler     = {str(v["id"]) for v in fav_talepler}
takip_kayitlar = list(fav_talepler)
for k, v in takip_sess.items():
    if str(k) not in fav_idler and "talep" in v.get("_takip_kaynak",""):
        takip_kayitlar.append(v)

selected_id = st.session_state.get("tm_selected_id")

# ── Satır render ──────────────────────────────────────────────────────────────
def satir_render(v, prefix):
    kid = str(v.get("id",""))
    ozet   = v.get("ozet") or v.get("mail_konusu") or "Talep"
    ilce   = ilce_grubu(v)
    islem  = v.get("islem_tipi","")
    favori = v.get("favori",False)
    tarih  = tarih_str(v)
    tip_bg,tip_fg,tip_lbl = tip_badge(islem)
    secili = str(selected_id or "")== kid
@st.cache_data(ttl=60)
def talep_musteri_map():
    try:
        r = get_client().table("musteriler").select("talep_id,musteri_adi").execute()
        return {str(row["talep_id"]): row["musteri_adi"] for row in (r.data or []) if row.get("talep_id")}
    except: return {}

# ── Satır render ──────────────────────────────────────────────────────────────
def satir_render(v, prefix, musteri_map=None):
    kid    = str(v.get("id",""))
    ozet   = v.get("ozet") or v.get("mail_konusu") or "Talep"
    ilce   = ilce_grubu(v)
    islem  = v.get("islem_tipi","")
    butce  = v.get("max_butce","") or ""
    favori = v.get("favori",False)
    tip_bg,tip_fg,tip_lbl = tip_badge(islem)
    secili = str(selected_id or "")==kid
    dot_c  = "#f59e0b" if favori else "#22c55e"
    musteri_adi = (musteri_map or {}).get(kid, "")

    musteri_adi = (musteri_map or {}).get(kid, "")
    brd = "#355C7D" if secili else "#e2e8f0"
    butce_str = f' · {butce[:14]}' if butce else ""
    musteri_str = f' · 👤{musteri_adi}' if musteri_adi else ""

    c_kart, c_fav = st.columns([20, 1])
    with c_kart:
        clicked = st.button(
            f"{'🔵' if secili else '⚪'} {ozet[:55]}  |  {ilce}{butce_str}  [{tip_lbl}]{musteri_str}",
            key=f"{prefix}_sel_{kid}",
            use_container_width=True,
            type="primary" if secili else "secondary",
        )
        if clicked:
            st.session_state["tm_selected_id"] = int(kid) if kid.isdigit() else kid
            st.session_state["tm_aktif_sekme"] = "detay"
            st.rerun()
    with c_fav:
        if st.button("★" if favori else "☆", key=f"{prefix}_fav_{kid}"):
            favori_guncelle(int(kid) if kid.isdigit() else kid, favori)

# ── Ana layout ────────────────────────────────────────────────────────────────
musteri_map_t = talep_musteri_map()
sol, sag = st.columns([1, 1.5], gap="medium")

with sol:
    # TAKİP
    st.markdown(f'<div class="tm-section-label">⭐ Takip Listem ({len(takip_kayitlar)})</div>', unsafe_allow_html=True)
    if not takip_kayitlar:
        st.caption("Henüz favorilediğin veya takibe aldığın talep yok.")
    else:
        for v in takip_kayitlar[:30]:
            satir_render(v, "tk", musteri_map_t)

    # BENİM TALEPLERİM
    st.markdown(f'<div class="tm-section-label">📋 Benim Taleplerim ({len(talepler)})</div>', unsafe_allow_html=True)
    if not talepler:
        st.caption("Senin adına kayıtlı talep yok.")
    for v in talepler:
        satir_render(v, "bm", musteri_map_t)

    # YENİ TALEP BUTONU
    st.markdown('<div style="height:10px;"></div>', unsafe_allow_html=True)
    if st.button("＋ Yeni Talep Ekle", key="btn_yeni_talep", use_container_width=True, type="primary"):
        st.session_state["tm_aktif_sekme"] = "yeni_talep"
        st.session_state.pop("tm_selected_id", None)
        st.rerun()

@st.fragment
def render_talep_detay_panel(sel):
    kid     = sel.get("id")
    ozet    = sel.get("ozet") or sel.get("mail_konusu") or "—"
    islem   = sel.get("islem_tipi","") or "—"
    mulk    = sel.get("mulk_tipi","") or "—"
    il      = sel.get("il","") or "—"
    ilce    = ilce_grubu(sel)
    bolge   = sel.get("bolge_mahalle","") or sel.get("bolge","") or "—"
    oda     = sel.get("oda_sayisi_m2","") or "—"
    butce   = sel.get("max_butce","") or "—"
    kriterler = sel.get("ozel_kriterler","") or "—"
    not_a   = sel.get("not_alani","") or ""
    gd_isim = isim_ayikla(sel.get("giren_gd","")) or isim_ayikla(sel.get("talep_eden_danisan","")) or "—"
    favori  = sel.get("favori",False)
    tip_bg,tip_fg,tip_lbl = tip_badge(islem)
    ozet_safe = str(ozet).replace("<","&lt;").replace(">","&gt;")

    st.markdown(
        f'<div style="background:#fff;border:1px solid #e2e8f0;border-radius:12px;padding:20px 22px;margin-bottom:8px;">'
        f'<div style="display:flex;align-items:flex-start;justify-content:space-between;gap:8px;">'
        f'<div style="font-size:15px;font-weight:700;color:#172B4D;line-height:1.4;">{ozet_safe}</div>'
        f'<span style="background:{tip_bg};color:{tip_fg};padding:3px 10px;border-radius:6px;font-size:11px;font-weight:700;white-space:nowrap;flex-shrink:0;">{tip_lbl}</span>'
        f'</div></div>',
        unsafe_allow_html=True
    )

    c1,c2 = st.columns(2)
    with c1:
        st.markdown('<p class="dp-label">Mülk Tipi</p><p class="dp-value">'+mulk+'</p>', unsafe_allow_html=True)
        st.markdown('<p class="dp-label">İl / İlçe</p><p class="dp-value">'+il+' / '+ilce+'</p>', unsafe_allow_html=True)
        st.markdown('<p class="dp-label">Bölge</p><p class="dp-value">'+bolge+'</p>', unsafe_allow_html=True)
    with c2:
        st.markdown('<p class="dp-label">Oda / m²</p><p class="dp-value">'+oda+'</p>', unsafe_allow_html=True)
        st.markdown('<p class="dp-label">Maks. Bütçe</p><p class="dp-value" style="font-weight:600;color:#172B4D;font-size:15px;">'+butce+'</p>', unsafe_allow_html=True)
        st.markdown('<p class="dp-label">Danışman</p><p class="dp-value">'+gd_isim+'</p>', unsafe_allow_html=True)

    if kriterler and kriterler != "—":
        st.markdown('<hr class="dp-divider">', unsafe_allow_html=True)
        st.markdown('<p class="dp-label">Özel Kriterler</p><p class="dp-value">'+kriterler+'</p>', unsafe_allow_html=True)

    # ── Müşteri kutusu
    st.markdown('<hr class="dp-divider">', unsafe_allow_html=True)
    st.markdown('<p class="dp-label">Müşteri</p>', unsafe_allow_html=True)

    musteri_form_key = f"tm_mf_{kid}"

    @st.cache_data(ttl=60)
    def musteri_cek_talep(talep_id):
        try:
            r = get_client().table("musteriler").select("*")\
                .eq("talep_id", str(talep_id)).execute()
            return r.data or []
        except: return []

    musteriler = musteri_cek_talep(kid)

    if musteriler:
        for m in musteriler:
            ad  = m.get("musteri_adi","") or "—"
            tel = m.get("telefon","") or "—"
            initials = "".join(w[0].upper() for w in ad.split()[:2]) if ad != "—" else "?"
            st.markdown(
                f'<div style="display:flex;align-items:center;gap:10px;padding:8px 12px;'
                f'background:#F8FAFC;border-radius:8px;margin-bottom:6px;border:0.5px solid #e2e8f0;">'
                f'<div style="width:32px;height:32px;border-radius:50%;background:#EEF4FA;'
                f'display:flex;align-items:center;justify-content:center;font-size:11px;'
                f'font-weight:600;color:#355C7D;flex-shrink:0;">{initials}</div>'
                f'<div style="flex:1;">'
                f'<div style="font-size:13px;font-weight:600;color:#172B4D;">{ad}</div>'
                f'<div style="font-size:11px;color:#64748b;">{tel}</div>'
                f'</div></div>',
                unsafe_allow_html=True
            )

    if st.session_state.get(musteri_form_key, False):
        mc1,mc2,mc3 = st.columns([3,3,1])
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
                        st.rerun()
                    except Exception as e:
                        st.error(f"Hata: {e}")
                else:
                    st.warning("Ad girin.")
        if st.button("İptal", key=f"tm_miptl_{kid}"):
            st.session_state[musteri_form_key] = False
            st.rerun()
    else:
        if st.button("+ Müşteri Ekle", key=f"tm_mekle_{kid}"):
            st.session_state[musteri_form_key] = True
            st.rerun()

    st.markdown('<hr class="dp-divider">', unsafe_allow_html=True)

    _kayitli_sonuc = sel.get("son_eslesme_json")
    _kayitli_tarih = sel.get("son_eslesme_tarihi")

    def _sonuc_serialize_listesi(sonuclar):
        """Motor sonucunu (portfoy alt-sözlüğü dahil TÜM alanlarla)
        değil, sadece EKRANDA GÖSTERİLEN alanlarla hafifletilmiş
        JSON'a çevirir — hem depolama hem yükleme hızı için."""
        cikti = []
        for s in sonuclar:
            p = s.get("portfoy", {}) or {}
            cikti.append({
                "skor": s.get("skor"),
                "seviye": s.get("seviye"),
                "gerekce": s.get("gerekce", ""),
                "grup": s.get("grup"),
                "portfoy": {
                    "id": p.get("id"),
                    "ozet": p.get("ozet"),
                    "ilce": p.get("ilce"),
                    "fiyat": p.get("fiyat"),
                    "portfoy_gorunurluk": p.get("portfoy_gorunurluk"),
                    "ilan_linki": p.get("ilan_linki"),
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
                "son_eslesme_tarihi": datetime.utcnow().isoformat(),
            }).eq("id", talep_id).execute()
        except Exception as e:
            st.warning(f"Eşleşme sonucu kaydedilemedi (sonuçlar yine de gösteriliyor): {e}")
        return _hafif

    if _kayitli_sonuc:
        _tarih_goster = str(_kayitli_tarih)[:16].replace("T", " ") if _kayitli_tarih else "—"
        st.markdown(f"**🔍 Eşleşen Portföyler** — son arama: {_tarih_goster}")

        if st.button("🔄 Yeniden Ara", key=f"tm_esleme_yenile_{kid}", use_container_width=True):
            with st.spinner("Yeniden aranıyor..."):
                # NOT: Sonucu hemen bu ekranda göstermek için doğrudan
                # kullanıyoruz — st.rerun()'a ve DB'nin başarılı yazmasına
                # bağımlı kalmıyoruz (önceki hata buydu: yazma sessizce
                # başarısız olursa sonuç hiç görünmüyordu). cache.clear()
                # de KASITLI OLARAK kullanılmıyor — talep listesini de
                # temizleyip sayfanın seçili kaydı kaybetmesine (istem
                # dışı "ana listeye dönme" hissi) yol açıyordu.
                _kayitli_sonuc = _esleme_ara_ve_kaydet(sel, kid)
                _tarih_goster = "az önce"

        if not _kayitli_sonuc:
            st.caption("Bu talebe uygun bir eşleşme bulunamadı.")
        else:
            for _i, _s in enumerate(_kayitli_sonuc):
                _esleme_satiri_ciz(_s, index=_i)
            st.caption(
                "ℹ️ Skorlar bir ön değerlendirmedir, müşteriye sunmadan önce "
                "portföyü mutlaka kontrol edin."
            )
    else:
        if st.button("🔍 Eşleşen Portföyler", key=f"tm_esleme_btn_{kid}", use_container_width=True):
            with st.spinner("Eşleşen portföyler aranıyor..."):
                _yeni_sonuc = _esleme_ara_ve_kaydet(sel, kid)

            if not _yeni_sonuc:
                st.caption("Bu talebe uygun bir eşleşme bulunamadı.")
            else:
                st.markdown("**🔍 Eşleşen Portföyler** — az önce arandı")
                for _i, _s in enumerate(_yeni_sonuc):
                    _esleme_satiri_ciz(_s, index=_i)
                st.caption(
                    "ℹ️ Skorlar bir ön değerlendirmedir, müşteriye sunmadan önce "
                    "portföyü mutlaka kontrol edin."
                )

    st.markdown('<hr class="dp-divider">', unsafe_allow_html=True)
    yeni_not = st.text_area("📝 Notum", value=not_a, key=f"not_{kid}", height=70,
                            placeholder="Bu talep hakkında notlarınız...")
    if st.button("💾 Notu Kaydet", key=f"not_kyd_{kid}"):
        try:
            get_client().table("alici_talepleri").update({"not_alani":yeni_not}).eq("id",kid).execute()
            st.cache_data.clear(); st.success("Not kaydedildi.")
        except Exception as e: st.error(f"Hata: {e}")

    st.markdown('<hr class="dp-divider">', unsafe_allow_html=True)
    ab1,ab2,ab3 = st.columns(3)
    with ab1:
        if st.button("★ Favoride" if favori else "☆ Favoriye Al", key=f"dp_fav_{kid}", use_container_width=True):
            favori_guncelle(kid, favori)
    with ab2:
        if st.button("＋ Yeni Talep", key=f"dp_yeni_{kid}", use_container_width=True):
            st.session_state["tm_aktif_sekme"] = "yeni_talep"
            st.session_state.pop("tm_selected_id", None)
            st.rerun(scope="app")
    with ab3:
        if st.button("✖ Kapat", key=f"dp_kapat_{kid}", use_container_width=True):
            st.session_state.pop("tm_selected_id", None)
            st.session_state["tm_aktif_sekme"] = "bos"
            st.rerun(scope="app")

    mail_icerik = sel.get("mail_icerigi","")
    if mail_icerik:
        with st.expander("📧 Mail İçeriği"):
            st.text(mail_icerik[:2000])


with sag:
    aktif_sekme = st.session_state.get("tm_aktif_sekme", "bos")

    if aktif_sekme in ("yeni_talep", "detay"):
        sek1, sek2, sek_bosluk = st.columns([1, 1, 2])
        with sek1:
            if st.button("📋 Detay", key="tm_sek_detay", use_container_width=True,
                         type="primary" if aktif_sekme == "detay" else "secondary"):
                st.session_state["tm_aktif_sekme"] = "detay"
                st.rerun()
        with sek2:
            if st.button("＋ Yeni Talep", key="tm_sek_yeni", use_container_width=True,
                         type="primary" if aktif_sekme == "yeni_talep" else "secondary"):
                st.session_state["tm_aktif_sekme"] = "yeni_talep"
                st.rerun()
        st.markdown('<div style="height:8px;"></div>', unsafe_allow_html=True)

    # ── YENİ TALEP FORMU ─────────────────────────────────────────────────────
    if aktif_sekme == "yeni_talep":
        parse_sonuc = st.session_state.get("tm_parse_sonuc", {})

        st.markdown("""
        <div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:12px;padding:18px 20px;margin-bottom:12px;">
        <div style="font-size:14px;font-weight:700;color:#172B4D;margin-bottom:14px;">＋ Yeni Talep Ekle</div>
        """, unsafe_allow_html=True)

        gc1, gc2, gc3 = st.columns(3)
        with gc1:
            st.caption("Ofis")
            zeta_ofis = st.selectbox("Ofis", ["Seç...","ZETA 1","ZETA 2","Diğer Ofis"], key="tm_ofis")
        with gc2:
            if zeta_ofis in ("ZETA 1","ZETA 2","Seç..."):
                st.caption("Zeta Danışmanı")
                gd_kaynak = gd_list_z1 if zeta_ofis=="ZETA 1" else gd_list_z2 if zeta_ofis=="ZETA 2" else gd_list_tum
                # Oturum açan kullanıcıyı varsayılan seç
                _default_gd = user_name if user_name in gd_kaynak else "Seç..."
                _default_idx = (["Seç..."]+gd_kaynak+["Diğer (manuel gir)"]).index(_default_gd) if _default_gd in (["Seç..."]+gd_kaynak) else 0
                gd_sec = st.selectbox("Danışman seçin", ["Seç..."]+gd_kaynak+["Diğer (manuel gir)"],
                    index=_default_idx, key="tm_gd_sec")
                gd_manuel = st.text_input("Danışman adı", key="tm_gd_manuel") if gd_sec=="Diğer (manuel gir)" else ""
                gd_ad = gd_manuel if gd_sec=="Diğer (manuel gir)" else (gd_sec if gd_sec!="Seç..." else user_name)
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
        kaynak = "zeta1" if zeta_ofis=="ZETA 1" else "zeta2" if zeta_ofis=="ZETA 2" else "dis_kaynak" if zeta_ofis=="Diğer Ofis" else "ofis"

        st.markdown("---")
        st.markdown('<p style="font-size:12px;font-weight:600;color:#355C7D;margin-bottom:6px;">👤 Müşteri Bilgisi <span style="font-weight:400;color:#94a3b8;">(isteğe bağlı)</span></p>', unsafe_allow_html=True)
        mk1, mk2 = st.columns(2)
        with mk1:
            tm_musteri_adi = st.text_input("Müşteri adı", placeholder="Ad Soyad", key="tm_musteri_adi")
        with mk2:
            tm_musteri_tel = st.text_input("Telefon", placeholder="05xx xxx xx xx", key="tm_musteri_tel")
        st.markdown("---")

        yontem = st.radio("Giriş yöntemi", ["Yapay Zeka Ayrıştırma","Form"], horizontal=True, key="tm_yontem")

        if yontem == "Yapay Zeka Ayrıştırma":
            metin = st.text_area("Talep açıklaması",
                placeholder="Örn: Müşterim Bornova veya Karşıyaka'da 3+1 kiralık daire arıyor, max 25.000 TL...",
                height=90, key="tm_metin")
            pa, pb = st.columns([1,4])
            with pa:
                if st.button("AI ile Doldur", key="tm_parse_btn", type="primary"):
                    if metin.strip():
                        with st.spinner("Analiz ediliyor..."):
                            sonuc = ai_parse_talep(metin)
                            mh_metin = sonuc.get("mahalle","") or metin
                            lookup = mahalle_ile_ilce_bul(mh_metin)
                            if lookup:
                                sonuc["il"] = lookup.get("il","")
                                sonuc["ilce"] = lookup.get("ilce","")
                                if not sonuc.get("mahalle"): sonuc["mahalle"] = lookup.get("mahalle","")
                            st.session_state["tm_parse_sonuc"] = sonuc
                            st.rerun()
                    else:
                        st.warning("Açıklama yazın.")
            if parse_sonuc:
                st.caption("✅ Aşağıdaki alanları kontrol edip düzenleyebilirsiniz.")

        if yontem == "Form" or parse_sonuc:
            f1,f2,f3 = st.columns(3)
            with f1:
                ozet  = st.text_input("Özet", value=parse_sonuc.get("ozet",""), key="tm_ozet")
                il    = st.selectbox("İl", ILLER,
                    index=ILLER.index(parse_sonuc.get("il","İzmir")) if parse_sonuc.get("il","") in ILLER else 0,
                    key="tm_il")
                ilce_opts = ["İzmir Genel"] + ilce_sec
                ilce_raw  = parse_sonuc.get("ilce","")
                ilce_idx  = ilce_opts.index(ilce_raw) if ilce_raw in ilce_opts else 0
                ilce_sec2 = st.selectbox("Birincil İlçe", ilce_opts, index=ilce_idx, key="tm_ilce")
                ilce_val  = "" if ilce_sec2=="İzmir Genel" else ilce_sec2
            with f2:
                mulk  = st.selectbox("Mülk Tipi",["Konut","İşyeri","Arsa","Belirsiz"],
                    index=["Konut","İşyeri","Arsa","Belirsiz"].index(parse_sonuc.get("mulk_tipi","Belirsiz"))
                    if parse_sonuc.get("mulk_tipi","") in ["Konut","İşyeri","Arsa","Belirsiz"] else 3,
                    key="tm_mulk")
                islem = st.selectbox("İşlem Tipi",["Satılık","Kiralık","Belirsiz"],
                    index=["Satılık","Kiralık","Belirsiz"].index(parse_sonuc.get("islem_tipi","Belirsiz"))
                    if parse_sonuc.get("islem_tipi","") in ["Satılık","Kiralık","Belirsiz"] else 2,
                    key="tm_islem")
                butce = st.text_input("Bütçe", value=parse_sonuc.get("max_butce",""), key="tm_butce")
            with f3:
                oda       = st.text_input("Oda/M²", value=parse_sonuc.get("oda_sayisi_m2",""), key="tm_oda")
                mahalle   = st.text_input("Mahalle", value=parse_sonuc.get("mahalle",""), key="tm_mahalle")
                kriterler = st.text_area("Özel Kriterler", value=parse_sonuc.get("ozel_kriterler",""),
                    height=80, key="tm_kriter")

            ilceler_default = [i for i in (parse_sonuc.get("ilceler") or []) if i in ilce_sec]
            ilceler = st.multiselect("Tüm İlçeler", ilce_sec, default=ilceler_default, key="tm_ilceler")

            ka,kb = st.columns([1,4])
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
                            "il": il, "ilce": ilce_val,
                            "ilceler": ilceler if ilceler else ([ilce_val] if ilce_val else []),
                            "mulk_tipi": mulk, "islem_tipi": islem,
                            "max_butce": butce, "oda_sayisi_m2": oda,
                            "mahalle": mahalle, "ozel_kriterler": kriterler,
                            "ozet": ozet,
                            "olusturma_tarihi": datetime.now().isoformat(),
                        }
                        if talep_kaydet(veri):
                            # Müşteri kaydı
                            if tm_musteri_adi.strip():
                                try:
                                    # Kaydedilen talebin ID'sini al
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
                                except: pass
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

    # ── DETAY PANELİ ─────────────────────────────────────────────────────────
    elif aktif_sekme == "detay" and selected_id:
        tum_liste = takip_kayitlar + talepler
        sel = next((v for v in tum_liste if str(v.get("id",""))==str(selected_id)), None)

        if not sel:
            st.info("Kayıt bulunamadı.")
        else:
            render_talep_detay_panel(sel)
    else:
        st.markdown("""
        <div style="height:280px;display:flex;flex-direction:column;align-items:center;
            justify-content:center;color:#94a3b8;gap:8px;border:1px dashed #e2e8f0;border-radius:12px;">
            <div style="font-size:32px;">📋</div>
            <div style="font-size:13px;font-weight:500;">Detay için bir kayıt seç</div>
            <div style="font-size:11px;">veya sol alttaki butona tıklayarak yeni talep ekle</div>
        </div>""", unsafe_allow_html=True)
