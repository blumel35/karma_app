import streamlit as st
import sys, os, re
from datetime import datetime
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.ui_helpers import render_navbar, render_page_header
from core.supabase_client import get_client

render_navbar(
    user_role=st.session_state.get("user_role", "danisan"),
    user_name=st.session_state.get("user_name", ""),
    user_initials=st.session_state.get("user_initials", ""),
)

# ── Helpers ─────────────────────────────────────────────────────────────────
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
    for k in ["ilan_tarihi","mail_tarihi","olusturma_tarihi","created_at"]:
        val = v.get(k)
        if val: return str(val)
    return ""

def tarih_str(v):
    d = tarih_parse(en_iyi_tarih(v))
    if not d: return "—"
    return d.strftime("%d.%m.%Y")

def ilce_grubu(v):
    ilceler = v.get("ilceler") or []
    ilce = v.get("ilce","") or ""
    tum = ([ilce] if ilce else []) + [i for i in ilceler if i!=ilce]
    tum = [i for i in tum if i and i!="Diğer Bölge"]
    return " · ".join(tum[:2]) if tum else (v.get("mahalle","") or "—")

def tip_badge(islem):
    islem = (islem or "").lower()
    if "kiralık" in islem or "kiralik" in islem: return "#f0fdf4","#166534","Kiralık"
    if "satılık" in islem or "satilik" in islem: return "#fef2f2","#991b1b","Satılık"
    return "#f8fafc","#64748b", islem or "—"

ILLER = ["İzmir","Aydın","Manisa","Balıkesir","Muğla","İstanbul","Ankara","Diğer"]
BUCKET = "portfoy-fotograflari"

# ── Veri fonksiyonları ────────────────────────────────────────────────────────
@st.cache_data(ttl=60)
def ilce_listesi_cek():
    try:
        r = get_client().table("ilceler").select("ilce").execute()
        return sorted([x["ilce"] for x in r.data if x.get("ilce")])
    except: return []

@st.cache_data(ttl=60)
def mahalle_lookup_cek():
    try:
        r = get_client().table("mahalleler").select("il,ilce,mahalle").execute()
        return {row["mahalle"].strip().lower():(row["il"],row["ilce"]) for row in r.data}
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

def portfoy_kaydet(veri):
    try:
        get_client().table("portfoyler").insert(veri).execute()
        st.cache_data.clear(); return True
    except Exception as e:
        st.error(f"Kayıt hatası: {e}"); return False

def foto_yukle(portfoy_id, dosyalar):
    import uuid, mimetypes
    client = get_client(); urls = []
    for dosya in dosyalar:
        try:
            ext = dosya.name.split(".")[-1].lower()
            dosya_adi = f"{portfoy_id}/{uuid.uuid4()}.{ext}"
            mime = mimetypes.guess_type(dosya.name)[0] or "image/jpeg"
            client.storage.from_(BUCKET).upload(path=dosya_adi, file=dosya.getvalue(),
                file_options={"content-type":mime,"upsert":"true"})
            url = client.storage.from_(BUCKET).get_public_url(dosya_adi)
            if url: urls.append(url)
        except: pass
    return urls

def favori_guncelle(kid, mevcut):
    try:
        get_client().table("portfoyler").update({"favori":not mevcut}).eq("id",kid).execute()
        st.cache_data.clear(); st.rerun()
    except Exception as e: st.error(f"Hata: {e}")

def ai_parse_portfoy(metin):
    import requests, json
    prompt = f"""Aşağıdaki gayrimenkul portföy açıklamasını analiz et ve JSON olarak döndür.
Sadece JSON döndür, başka hiçbir şey yazma.
Portföy: {metin}
JSON: {{"il":"İzmir","ilce":"","ilceler":[],"mulk_tipi":"Konut/İşyeri/Arsa/Belirsiz",
"islem_tipi":"Satılık/Kiralık/Belirsiz","oda_sayisi_m2":"","fiyat":"",
"mahalle":"","ozel_kriterler":"","ozet":"","ilan_linki":""}}"""
    try:
        api_key = st.secrets["anthropic"]["api_key"].strip()
        resp = requests.post("https://api.anthropic.com/v1/messages",
            headers={"Content-Type":"application/json","x-api-key":api_key,"anthropic-version":"2023-06-01"},
            json={"model":"claude-sonnet-4-6","max_tokens":600,"messages":[{"role":"user","content":prompt}]},
            timeout=30)
        data = resp.json()
        if "error" in data: return {"_hata":str(data["error"])}
        text = data["content"][0]["text"].strip().replace("```json","").replace("```","").strip()
        return json.loads(text)
    except Exception as e: return {"_hata":str(e)}

@st.cache_data(ttl=60)
def benim_portfoylerím(user_id, user_name):
    try:
        tum = get_client().table("portfoyler").select("*")\
            .order("olusturma_tarihi",desc=True).limit(500).execute().data or []
        sonuc = []; goruldu = set()
        for v in tum:
            vid = v.get("id")
            if vid in goruldu: continue
            if user_id and v.get("user_id")==user_id: sonuc.append(v); goruldu.add(vid); continue
            if user_name and user_name.strip():
                un = user_name.lower().strip()
                gd = isim_ayikla(v.get("talep_eden_danisan","")).lower()
                if un in gd or gd in un: sonuc.append(v); goruldu.add(vid); continue
                gg = isim_ayikla(v.get("giren_gd","")).lower()
                if gg and (un in gg or gg in un): sonuc.append(v); goruldu.add(vid); continue
        return sonuc
    except Exception as e: st.error(f"Hata: {e}"); return []

@st.cache_data(ttl=60)
def favori_portfoyler():
    try:
        r = get_client().table("portfoyler").select("*").eq("favori",True)\
            .order("olusturma_tarihi",desc=True).limit(200).execute()
        return r.data or []
    except: return []

@st.cache_data(ttl=60)
def gd_listesi_zeta():
    try:
        z1 = sorted(set(v.get("talep_eden_danisan","")
            for v in (get_client().table("portfoyler").select("talep_eden_danisan").in_("kaynak",["zeta1"]).execute().data or [])
            if v.get("talep_eden_danisan","")))
        z2 = sorted(set(v.get("talep_eden_danisan","")
            for v in (get_client().table("portfoyler").select("talep_eden_danisan").in_("kaynak",["zeta2"]).execute().data or [])
            if v.get("talep_eden_danisan","")))
        return z1, z2, sorted(set(z1+z2))
    except: return [],[],[]

@st.cache_data(ttl=60)
def tum_musteri_map():
    """id (str) → musteri_adi — hem integer hem UUID ile eşleşir"""
    try:
        r = get_client().table("musteriler").select("portfoy_id,musteri_adi,musteri_soyadi").execute()
        result = {}
        for row in (r.data or []):
            pid = str(row.get("portfoy_id",""))
            ad  = " ".join(filter(None,[row.get("musteri_adi",""),row.get("musteri_soyadi","")])).strip()
            if pid and ad: result[pid] = ad
        return result
    except: return {}

@st.cache_data(ttl=60)
def musteri_listesi_cek(portfoy_id_str):
    try:
        r = get_client().table("musteriler").select("*")\
            .eq("portfoy_id", portfoy_id_str).execute()
        return r.data or []
    except: return []

# ── Session ───────────────────────────────────────────────────────────────────
_k = st.session_state.get("kullanici", {})
user_id   = _k.get("id","")
user_name = _k.get("ad_soyad") or _k.get("ad","")
ilce_sec  = ilce_listesi_cek()
gd_list_z1, gd_list_z2, gd_list_tum = gd_listesi_zeta()
musteri_map = tum_musteri_map()

# ── CSS ─────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
.pm-lbl{font-size:9px;font-weight:700;color:#94a3b8;text-transform:uppercase;letter-spacing:.07em;margin:14px 0 3px;}
.pm-val{font-size:13px;color:#1e293b;font-weight:500;margin-bottom:6px;}
.pm-divider{border:none;border-top:0.5px solid #f1f5f9;margin:10px 0;}
.pm-sec{font-size:10px;font-weight:700;color:#94a3b8;text-transform:uppercase;letter-spacing:.08em;
    margin:12px 0 6px;border-bottom:0.5px solid #f1f5f9;padding-bottom:5px;}
</style>
""", unsafe_allow_html=True)

# ── Başlık ───────────────────────────────────────────────────────────────────
hc1, hc2 = st.columns([1, 0.1])
with hc1:
    render_page_header("🏠 Portföylerim", f"Takip listem ve kendi portföylerim · {user_name}")
with hc2:
    if st.button("↺", key="pm_yenile", help="Yenile"):
        st.cache_data.clear(); st.rerun()

# ── Veri ─────────────────────────────────────────────────────────────────────
portfoyler     = benim_portfoylerím(user_id, user_name)
fav_portfoyler = favori_portfoyler()
takip_sess     = st.session_state.get("takip_listesi", {})
fav_idler      = {str(v["id"]) for v in fav_portfoyler}
takip_kayitlar = list(fav_portfoyler)
for k, v in takip_sess.items():
    if str(k) not in fav_idler and "portfoy" in v.get("_takip_kaynak",""):
        takip_kayitlar.append(v)

aktif_sekme = st.session_state.get("pm_aktif_sekme","bos")
selected_id = st.session_state.get("pm_selected_id")

# ── ÜST: LİSTE + YENİ PORTFÖY BUTONU ────────────────────────────────────────
if takip_kayitlar:
    st.markdown('<div class="pm-sec">⭐ Takip Listem</div>', unsafe_allow_html=True)
    for v in takip_kayitlar[:20]:
        kid = str(v.get("id",""))
        ozet = v.get("ozet") or v.get("mail_konusu") or "Portföy"
        ilce = ilce_grubu(v)
        islem = v.get("islem_tipi","")
        fiyat = v.get("fiyat","") or ""
        favori = v.get("favori",False)
        tip_bg,tip_fg,tip_lbl = tip_badge(islem)
        musteri = musteri_map.get(kid,"")
        secili = str(selected_id or "")==kid

        c1,c2,c3 = st.columns([10,1,1])
        with c1:
            label = f"{'●' if secili else '○'} {ozet[:50]}  ·  {ilce}{' · '+fiyat[:12] if fiyat else ''}  [{tip_lbl}]{' · 👤'+musteri if musteri else ''}"
            if st.button(label, key=f"ptk_sel_{kid}", use_container_width=True,
                         type="primary" if secili else "secondary"):
                st.session_state["pm_selected_id"] = int(kid) if kid.isdigit() else kid
                st.session_state["pm_aktif_sekme"] = "detay"
                st.rerun()
        with c2:
            if st.button("★" if favori else "☆", key=f"ptk_fav_{kid}"):
                favori_guncelle(int(kid) if kid.isdigit() else kid, favori)
        with c3:
            st.caption(tarih_str(v))

st.markdown('<div class="pm-sec">🏠 Benim Portföylerim</div>', unsafe_allow_html=True)

l_cols = st.columns([10,1,1])
with l_cols[0]: st.markdown('<span style="font-size:10px;color:#94a3b8;">Portföy</span>', unsafe_allow_html=True)
with l_cols[1]: st.markdown('<span style="font-size:10px;color:#94a3b8;">Fav</span>', unsafe_allow_html=True)
with l_cols[2]: st.markdown('<span style="font-size:10px;color:#94a3b8;">Tarih</span>', unsafe_allow_html=True)

if not portfoyler:
    st.caption("Senin adına kayıtlı portföy yok.")
else:
    for v in portfoyler:
        kid = str(v.get("id",""))
        ozet = v.get("ozet") or v.get("mail_konusu") or "Portföy"
        ilce = ilce_grubu(v)
        islem = v.get("islem_tipi","")
        fiyat = v.get("fiyat","") or ""
        favori = v.get("favori",False)
        tip_bg,tip_fg,tip_lbl = tip_badge(islem)
        musteri = musteri_map.get(kid,"")
        secili = str(selected_id or "")==kid

        c1,c2,c3 = st.columns([10,1,1])
        with c1:
            label = f"{'●' if secili else '○'} {ozet[:50]}  ·  {ilce}{' · '+fiyat[:12] if fiyat else ''}  [{tip_lbl}]{' · 👤'+musteri if musteri else ''}"
            if st.button(label, key=f"pbm_sel_{kid}", use_container_width=True,
                         type="primary" if secili else "secondary"):
                st.session_state["pm_selected_id"] = int(kid) if kid.isdigit() else kid
                st.session_state["pm_aktif_sekme"] = "detay"
                st.rerun()
        with c2:
            if st.button("★" if favori else "☆", key=f"pbm_fav_{kid}"):
                favori_guncelle(int(kid) if kid.isdigit() else kid, favori)
        with c3:
            st.caption(tarih_str(v))

st.markdown('<div style="height:8px;"></div>', unsafe_allow_html=True)
if st.button("＋ Yeni Portföy Ekle", key="btn_yeni_portfoy", type="primary"):
    st.session_state["pm_aktif_sekme"] = "yeni_portfoy"
    st.session_state.pop("pm_selected_id",None)
    st.rerun()

st.markdown("---")

# ── ALT: DETAY veya FORM ─────────────────────────────────────────────────────
if aktif_sekme == "yeni_portfoy":
    parse_sonuc = st.session_state.get("pm_parse_sonuc",{})

    st.markdown("### ＋ Yeni Portföy Ekle")

    gc1,gc2,gc3 = st.columns(3)
    with gc1:
        st.caption("Ofis")
        zeta_ofis = st.selectbox("Ofis",["Seç...","ZETA 1","ZETA 2","Diğer Ofis"],key="pm_ofis")
    with gc2:
        if zeta_ofis in ("ZETA 1","ZETA 2","Seç..."):
            st.caption("Portföyü Paylaşan GD")
            gd_kaynak = gd_list_z1 if zeta_ofis=="ZETA 1" else gd_list_z2 if zeta_ofis=="ZETA 2" else gd_list_tum
            _def = user_name if user_name in gd_kaynak else "Seç..."
            _idx = (["Seç..."]+gd_kaynak+["Diğer (manuel gir)"]).index(_def) if _def in (["Seç..."]+gd_kaynak) else 0
            gd_sec = st.selectbox("Danışman seçin",["Seç..."]+gd_kaynak+["Diğer (manuel gir)"],index=_idx,key="pm_gd_sec")
            gd_sec_val = gd_sec
            gd_ad = "" if gd_sec_val=="Seç..." else (gd_sec_val if gd_sec_val!="Diğer (manuel gir)" else user_name)
            ofis_adi=""
        else:
            st.caption("Ofis Adı")
            ofis_adi = st.text_input("Ofis adı",placeholder="Örn: RE/MAX Bornova",key="pm_ofis_adi")
            gd_sec_val = "Seç..."; gd_ad=""
    with gc3:
        if zeta_ofis=="Diğer Ofis":
            st.caption("Danışman Adı")
            gd_dis = st.text_input("Danışman adı",placeholder="Ad Soyad",key="pm_gd_dis")
            gd_ad = f"{gd_dis} - {ofis_adi}".strip(" -") if (gd_dis or ofis_adi) else ""
        elif gd_sec_val=="Diğer (manuel gir)":
            gd_ad = st.text_input("Danışman adı",key="pm_gd_manuel")
        else:
            st.empty()
    if not gd_ad: gd_ad = user_name
    kaynak = "zeta1" if zeta_ofis=="ZETA 1" else "zeta2" if zeta_ofis=="ZETA 2" else "dis_kaynak" if zeta_ofis=="Diğer Ofis" else "ofis"

    st.markdown("---")
    st.markdown('<p style="font-size:12px;font-weight:600;color:#355C7D;">👤 Müşteri Bilgisi <span style="font-weight:400;color:#94a3b8;">(isteğe bağlı)</span></p>', unsafe_allow_html=True)
    mk1,mk2,mk3 = st.columns(3)
    with mk1: pm_musteri_adi = st.text_input("Müşteri adı",placeholder="Ad",key="pm_musteri_adi")
    with mk2: pm_musteri_soyadi = st.text_input("Soyadı",placeholder="Soyad",key="pm_musteri_soyadi")
    with mk3: pm_musteri_tel = st.text_input("Telefon",placeholder="05xx xxx xx xx",key="pm_musteri_tel")

    st.markdown("---")
    yontem = st.radio("Portföy bilgileri",["Metin Yaz → Sistem Doldursun","Formu Kendim Doldurayım"],horizontal=True,key="pm_yontem")

    if yontem=="Metin Yaz → Sistem Doldursun":
        metin = st.text_area("Portföy açıklaması",placeholder="Örn: Bornova Erzene'de 3+1 satılık daire, 120 m², 4.5 milyon TL...",height=80,key="pm_metin")
        if st.button("Metni Yorumla",key="pm_parse_btn",type="primary"):
            if metin.strip():
                with st.spinner("Analiz ediliyor..."):
                    sonuc = ai_parse_portfoy(metin)
                    if "_hata" not in sonuc:
                        lookup = mahalle_ile_ilce_bul(sonuc.get("mahalle","") or metin)
                        if lookup:
                            sonuc["il"] = lookup.get("il",""); sonuc["ilce"] = lookup.get("ilce","")
                            if not sonuc.get("mahalle"): sonuc["mahalle"] = lookup.get("mahalle","")
                        st.session_state["pm_parse_sonuc"] = sonuc; parse_sonuc = sonuc
                        st.success("Dolduruldu — kontrol edin."); st.rerun()
                    else: st.error(f"Hata: {sonuc['_hata']}")
            else: st.warning("Açıklama yazın.")
        if parse_sonuc: st.caption("✅ Aşağıdaki alanları kontrol edip düzenleyebilirsiniz.")

    if yontem=="Formu Kendim Doldurayım" or parse_sonuc:
        f1,f2,f3 = st.columns(3)
        with f1:
            ozet  = st.text_input("Özet / Başlık",value=parse_sonuc.get("ozet",""),key="pm_ozet")
            il    = st.selectbox("İl",ILLER,index=ILLER.index(parse_sonuc.get("il","İzmir")) if parse_sonuc.get("il","") in ILLER else 0,key="pm_il")
            ilce_opts=["İzmir Genel"]+ilce_sec; ilce_raw=parse_sonuc.get("ilce","")
            ilce_sec2=st.selectbox("Birincil İlçe",ilce_opts,index=ilce_opts.index(ilce_raw) if ilce_raw in ilce_opts else 0,key="pm_ilce")
            ilce_val="" if ilce_sec2=="İzmir Genel" else ilce_sec2
        with f2:
            mulk  = st.selectbox("Mülk Tipi",["Konut","İşyeri","Arsa","Belirsiz"],
                index=["Konut","İşyeri","Arsa","Belirsiz"].index(parse_sonuc.get("mulk_tipi","Belirsiz")) if parse_sonuc.get("mulk_tipi","") in ["Konut","İşyeri","Arsa","Belirsiz"] else 3,key="pm_mulk")
            islem = st.selectbox("İşlem Tipi",["Satılık","Kiralık","Belirsiz"],
                index=["Satılık","Kiralık","Belirsiz"].index(parse_sonuc.get("islem_tipi","Belirsiz")) if parse_sonuc.get("islem_tipi","") in ["Satılık","Kiralık","Belirsiz"] else 2,key="pm_islem")
            fiyat = st.text_input("Fiyat",value=parse_sonuc.get("fiyat",""),placeholder="Örn: 4.500.000 TL",key="pm_fiyat")
        with f3:
            oda     = st.text_input("Oda / M²",value=parse_sonuc.get("oda_sayisi_m2",""),placeholder="Örn: 3+1 / 120 m²",key="pm_oda")
            mahalle = st.text_input("Mahalle / Semt",value=parse_sonuc.get("mahalle",""),key="pm_mahalle")
            link    = st.text_input("İlan Linki",value=parse_sonuc.get("ilan_linki",""),key="pm_link")
        ilceler_default=[i for i in (parse_sonuc.get("ilceler") or []) if i in ilce_sec]
        ilceler = st.multiselect("Tüm İlçeler",ilce_sec,default=ilceler_default,key="pm_ilceler")
        ozel = st.text_area("Özellikler / Notlar",value=parse_sonuc.get("ozel_kriterler",""),height=60,key="pm_ozel")

        st.markdown("**Fotoğraflar** *(isteğe bağlı)*")
        yuklenen = st.file_uploader("Fotoğraf yükle",type=["jpg","jpeg","png","webp"],accept_multiple_files=True,key="pm_foto")
        if yuklenen:
            import base64
            imgs_html=""
            for dosya in yuklenen:
                b64=base64.b64encode(dosya.read()).decode(); dosya.seek(0)
                mime="image/jpeg" if dosya.name.lower().endswith(("jpg","jpeg")) else "image/png"
                imgs_html+=f'<img src="data:{mime};base64,{b64}" style="width:110px;height:85px;object-fit:cover;border-radius:6px;margin:3px;"/>'
            st.markdown(f'<div style="display:flex;flex-wrap:wrap;gap:3px;">{imgs_html}</div>',unsafe_allow_html=True)

        st.markdown("---")
        ka,kb = st.columns([1,5])
        with ka:
            if st.button("💾 Kaydet",key="pm_kaydet",type="primary"):
                with st.spinner("Kaydediliyor..."):
                    import uuid as _uuid
                    portfoy_id = str(_uuid.uuid4())
                    foto_urls_list = foto_yukle(portfoy_id,yuklenen) if yuklenen else []
                    veri = {
                        "talep_eden_danisan":gd_ad,"kaynak":kaynak,"giren_gd":user_name,
                        "il":il,"ilce":ilce_val,"ilceler":ilceler if ilceler else ([ilce_val] if ilce_val else []),
                        "mulk_tipi":mulk,"islem_tipi":islem,"fiyat":fiyat,"oda_sayisi_m2":oda,
                        "mahalle":mahalle,"ilan_linki":link,"ozet":ozet,"ozel_kriterler":ozel,
                        "foto_url":",".join(foto_urls_list) if foto_urls_list else "",
                        "olusturma_tarihi":datetime.now().isoformat(),
                    }
                    if portfoy_kaydet(veri):
                        if pm_musteri_adi.strip():
                            try:
                                get_client().table("musteriler").insert({
                                    "portfoy_id":portfoy_id,
                                    "musteri_adi":pm_musteri_adi.strip(),
                                    "musteri_soyadi":pm_musteri_soyadi.strip(),
                                    "telefon":pm_musteri_tel.strip(),
                                    "ekleyen":user_name,"danisan_id":user_name,
                                }).execute()
                            except: pass
                        st.session_state.pop("pm_parse_sonuc",None)
                        st.session_state["pm_aktif_sekme"]="bos"
                        st.success("✅ Portföy kaydedildi!"); st.rerun()
        with kb:
            if st.button("İptal",key="pm_iptal"):
                st.session_state.pop("pm_parse_sonuc",None)
                st.session_state["pm_aktif_sekme"]="bos"; st.rerun()

elif aktif_sekme=="detay" and selected_id:
    tum_liste = takip_kayitlar + portfoyler
    sel = next((v for v in tum_liste if str(v.get("id",""))==str(selected_id)),None)

    if not sel:
        st.info("Kayıt bulunamadı.")
    else:
        kid     = sel.get("id")
        ozet    = sel.get("ozet") or sel.get("mail_konusu") or "—"
        islem   = sel.get("islem_tipi","") or "—"
        mulk    = sel.get("mulk_tipi","") or "—"
        il      = sel.get("il","") or "—"
        ilce    = ilce_grubu(sel)
        bolge   = sel.get("bolge_mahalle","") or sel.get("mahalle","") or "—"
        oda     = sel.get("oda_sayisi_m2","") or "—"
        fiyat   = sel.get("fiyat","") or "—"
        ozellik = sel.get("ozellikler","") or sel.get("ozel_kriterler","") or "—"
        link    = sel.get("ilan_linki","") or ""
        kapali  = sel.get("kapali_portfoy",False)
        not_a   = sel.get("not_alani","") or ""
        gd_isim = isim_ayikla(sel.get("giren_gd","")) or isim_ayikla(sel.get("talep_eden_danisan","")) or "—"
        favori  = sel.get("favori",False)
        foto_url_raw = sel.get("foto_url","") or ""
        tip_bg,tip_fg,tip_lbl = tip_badge(islem)
        ozet_safe = str(ozet).replace("<","&lt;").replace(">","&gt;")

        # ── 1. BAŞLIK
        kapali_str = " 🔒" if kapali else ""
        st.markdown(
            f'<div style="font-size:16px;font-weight:700;color:#172B4D;line-height:1.4;margin-bottom:6px;">'
            f'{ozet_safe}{kapali_str} '
            f'<span style="background:{tip_bg};color:{tip_fg};padding:2px 8px;border-radius:4px;font-size:11px;font-weight:600;">{tip_lbl}</span>'
            f'</div>',
            unsafe_allow_html=True
        )

        # ── 2. MÜŞTERİ BİLGİSİ (öne çıkarılmış)
        st.markdown('<hr style="border:none;border-top:0.5px solid #e2e8f0;margin:8px 0;">', unsafe_allow_html=True)
        st.markdown('<p class="pm-lbl">👤 Müşteri / Alıcı</p>', unsafe_allow_html=True)
        musteriler = musteri_listesi_cek(str(kid))
        if musteriler:
            for m in musteriler:
                ad  = " ".join(filter(None,[m.get("musteri_adi",""),m.get("musteri_soyadi","")])).strip() or "—"
                tel = m.get("telefon","") or "—"
                initials = "".join(w[0].upper() for w in ad.split()[:2]) if ad!="—" else "?"
                st.markdown(
                    f'<div style="display:inline-flex;align-items:center;gap:10px;padding:7px 12px;'
                    f'background:#EEF4FA;border-radius:8px;border:0.5px solid #c7d9ed;margin-bottom:5px;">'
                    f'<div style="width:30px;height:30px;border-radius:50%;background:#355C7D;'
                    f'display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:600;color:#fff;">{initials}</div>'
                    f'<div><div style="font-size:13px;font-weight:600;color:#172B4D;">{ad}</div>'
                    f'<div style="font-size:11px;color:#64748b;">{tel}</div></div></div>',
                    unsafe_allow_html=True
                )

        musteri_form_key = f"pm_mf_{kid}"
        if st.session_state.get(musteri_form_key, False):
            mc1,mc2,mc3,mc4 = st.columns([2,2,2,1])
            with mc1: y_ad = st.text_input("Adı", placeholder="Ad", key=f"pm_mad_{kid}")
            with mc2: y_soyad = st.text_input("Soyadı", placeholder="Soyad", key=f"pm_msoyad_{kid}")
            with mc3: y_tel = st.text_input("Telefon", placeholder="05xx", key=f"pm_mtel_{kid}")
            with mc4:
                st.markdown("<div style='height:27px'></div>", unsafe_allow_html=True)
                if st.button("💾", key=f"pm_mkyd_{kid}", use_container_width=True):
                    if y_ad.strip():
                        try:
                            get_client().table("musteriler").insert({
                                "portfoy_id": str(kid), "musteri_adi": y_ad.strip(),
                                "musteri_soyadi": y_soyad.strip(), "telefon": y_tel.strip(),
                                "ekleyen": user_name, "danisan_id": user_name,
                            }).execute()
                            st.cache_data.clear()
                            st.session_state[musteri_form_key] = False
                            st.success("Müşteri eklendi!"); st.rerun()
                        except Exception as e: st.error(f"Hata: {e}")
                    else: st.warning("Ad girin.")
            if st.button("İptal", key=f"pm_miptl_{kid}"):
                st.session_state[musteri_form_key] = False; st.rerun()
        else:
            if st.button("+ Müşteri / Alıcı Ekle", key=f"pm_mekle_{kid}"):
                st.session_state[musteri_form_key] = True; st.rerun()

        # ── 3. FOTOĞRAFLAR
        foto_urls = [u.strip() for u in foto_url_raw.split(",") if u.strip().startswith("http")]
        if foto_urls:
            st.markdown('<hr style="border:none;border-top:0.5px solid #e2e8f0;margin:8px 0;">', unsafe_allow_html=True)
            st.markdown('<p class="pm-lbl">Fotoğraflar</p>', unsafe_allow_html=True)
            foto_cols = st.columns(min(len(foto_urls), 5))
            for i, url in enumerate(foto_urls[:5]):
                with foto_cols[i]: st.image(url, use_container_width=True)

        # ── 4. BİLGİ GRID
        st.markdown('<hr style="border:none;border-top:0.5px solid #e2e8f0;margin:8px 0;">', unsafe_allow_html=True)
        d1,d2,d3 = st.columns(3)
        with d1:
            st.markdown(f'<p class="pm-lbl">Mülk Tipi</p><p class="pm-val">{mulk}</p>', unsafe_allow_html=True)
            st.markdown(f'<p class="pm-lbl">İl / İlçe</p><p class="pm-val">{il} / {ilce}</p>', unsafe_allow_html=True)
            st.markdown(f'<p class="pm-lbl">Bölge / Mahalle</p><p class="pm-val">{bolge}</p>', unsafe_allow_html=True)
        with d2:
            st.markdown(f'<p class="pm-lbl">Oda / m²</p><p class="pm-val">{oda}</p>', unsafe_allow_html=True)
            st.markdown(f'<p class="pm-lbl">Fiyat</p><p class="pm-val" style="font-size:15px;font-weight:700;color:#172B4D;">{fiyat}</p>', unsafe_allow_html=True)
            st.markdown(f'<p class="pm-lbl">Danışman</p><p class="pm-val">{gd_isim}</p>', unsafe_allow_html=True)
        with d3:
            if ozellik and ozellik != "—":
                st.markdown(f'<p class="pm-lbl">Özellikler</p><p class="pm-val">{ozellik}</p>', unsafe_allow_html=True)
            st.markdown(f'<p class="pm-lbl">Tarih</p><p class="pm-val">{tarih_str(sel)}</p>', unsafe_allow_html=True)
            if link and link != "—":
                st.markdown(f'<p class="pm-lbl">İlan</p><a href="{link}" target="_blank" style="font-size:12px;color:#355C7D;">🔗 İlan Linki</a>', unsafe_allow_html=True)

        # ── 5. NOT
        st.markdown('<hr style="border:none;border-top:0.5px solid #e2e8f0;margin:8px 0;">', unsafe_allow_html=True)
        yeni_not = st.text_area("📝 Notum", value=not_a, key=f"pnot_{kid}", height=80,
                                placeholder="Bu portföy hakkında notlarınız...")
        if st.button("💾 Notu Kaydet", key=f"pnot_kyd_{kid}"):
            try:
                get_client().table("portfoyler").update({"not_alani": yeni_not}).eq("id", kid).execute()
                st.cache_data.clear(); st.success("Not kaydedildi.")
            except Exception as e: st.error(f"Hata: {e}")

        # ── 6. PAYLAŞ
        st.markdown('<hr style="border:none;border-top:0.5px solid #e2e8f0;margin:8px 0;">', unsafe_allow_html=True)
        st.markdown('<p class="pm-lbl">Paylaş</p>', unsafe_allow_html=True)
        p1, p2 = st.columns(2)

        with p1:
            # Startkey Paylaş — tüm danışmanlara mail
            paylasim_key = f"pm_paylasim_{kid}"
            if st.session_state.get(paylasim_key, False):
                konu_default = f"Portföy Paylaşımı: {ozet[:60]}"
                mail_konu = st.text_input("Mail konusu", value=konu_default, key=f"pm_mk_{kid}")
                mail_mesaj_default = (
                    f"Merhaba,\n\n"
                    f"Aşağıdaki portföyü paylaşıyorum:\n\n"
                    f"📍 {ozet}\n"
                    f"🏠 {mulk} · {islem}\n"
                    f"📌 {il} / {ilce}{' · ' + bolge if bolge and bolge!='—' else ''}\n"
                    f"🛏 {oda}\n"
                    f"💰 {fiyat}\n"
                    + (f"🔗 {link}\n" if link and link!="—" else "")
                    + f"\n{ozellik if ozellik and ozellik!='—' else ''}\n\n"
                    f"İyi çalışmalar,\n{gd_isim}"
                )
                mail_mesaj = st.text_area("Mesaj", value=mail_mesaj_default, key=f"pm_mm_{kid}", height=160)
                pb1, pb2 = st.columns(2)
                with pb1:
                    if st.button("📧 Gönder", key=f"pm_send_{kid}", type="primary", use_container_width=True):
                        try:
                            import imaplib, smtplib
                            from email.mime.multipart import MIMEMultipart
                            from email.mime.text import MIMEText
                            user_mail = st.secrets["email"]["user"]
                            password  = st.secrets["email"]["password"]
                            smtp_host = st.secrets["email"].get("smtp", "smtp.yandex.com")
                            smtp_port = int(st.secrets["email"].get("smtp_port", 465))

                            # Alıcıları çek — kullanicilar tablosundan
                            alicilar_r = get_client().table("kullanicilar").select("email").execute()
                            alicilar = [r["email"] for r in (alicilar_r.data or []) if r.get("email") and r["email"] != user_mail]

                            if not alicilar:
                                st.warning("Gönderilecek danışman bulunamadı.")
                            else:
                                msg = MIMEMultipart("alternative")
                                msg["Subject"] = mail_konu
                                msg["From"]    = user_mail
                                msg["To"]      = ", ".join(alicilar)
                                msg.attach(MIMEText(mail_mesaj, "plain", "utf-8"))

                                with smtplib.SMTP_SSL(smtp_host, smtp_port) as server:
                                    server.login(user_mail, password)
                                    server.sendmail(user_mail, alicilar, msg.as_string())

                                st.success(f"✅ {len(alicilar)} danışmana gönderildi!")
                                st.session_state[paylasim_key] = False
                                st.rerun()
                        except Exception as e:
                            st.error(f"Mail gönderilemedi: {e}")
                with pb2:
                    if st.button("İptal", key=f"pm_send_ipt_{kid}", use_container_width=True):
                        st.session_state[paylasim_key] = False; st.rerun()
            else:
                if st.button("📧 Startkey'e Paylaş", key=f"pm_startkey_{kid}", use_container_width=True):
                    st.session_state[paylasim_key] = True; st.rerun()

        with p2:
            # Ofis ile Paylaş — kaynak güncelle
            ofis_key = f"pm_ofis_paylasim_{kid}"
            mevcut_kaynak = sel.get("kaynak","")
            zeta_paylasildi = mevcut_kaynak in ("zeta1","zeta2","ofis")

            if zeta_paylasildi:
                zeta_label = {"zeta1":"ZETA 1","zeta2":"ZETA 2","ofis":"Zeta Ofis"}.get(mevcut_kaynak,mevcut_kaynak)
                st.markdown(
                    f'<div style="padding:8px 12px;background:#f0fdf4;border-radius:8px;'
                    f'border:0.5px solid #bbf7d0;font-size:12px;color:#166534;">'
                    f'✅ {zeta_label} ile paylaşıldı</div>',
                    unsafe_allow_html=True
                )
                if st.button("↩ Paylaşımı Geri Al", key=f"pm_geri_{kid}", use_container_width=True):
                    try:
                        get_client().table("portfoyler").update({"kaynak":"ofis_gizli"}).eq("id",kid).execute()
                        st.cache_data.clear(); st.success("Paylaşım geri alındı."); st.rerun()
                    except Exception as e: st.error(f"Hata: {e}")
            else:
                if st.session_state.get(ofis_key, False):
                    zeta_sec = st.selectbox("Hangi ofisle?", ["ZETA 1","ZETA 2","Her İkisi"], key=f"pm_zeta_sec_{kid}")
                    oz1, oz2 = st.columns(2)
                    with oz1:
                        if st.button("✅ Paylaş", key=f"pm_ofis_gonder_{kid}", type="primary", use_container_width=True):
                            try:
                                yeni_kaynak = "zeta1" if zeta_sec=="ZETA 1" else "zeta2" if zeta_sec=="ZETA 2" else "ofis"
                                get_client().table("portfoyler").update({"kaynak":yeni_kaynak}).eq("id",kid).execute()
                                st.cache_data.clear()
                                st.session_state[ofis_key] = False
                                st.success(f"✅ {zeta_sec} havuzuna eklendi!"); st.rerun()
                            except Exception as e: st.error(f"Hata: {e}")
                    with oz2:
                        if st.button("İptal", key=f"pm_ofis_ipt_{kid}", use_container_width=True):
                            st.session_state[ofis_key] = False; st.rerun()
                else:
                    if st.button("🏢 Ofis ile Paylaş", key=f"pm_ofis_{kid}", use_container_width=True):
                        st.session_state[ofis_key] = True; st.rerun()

        # ── 7. ANA BUTONLAR
        st.markdown('<hr style="border:none;border-top:0.5px solid #e2e8f0;margin:10px 0;">', unsafe_allow_html=True)
        ab1,ab2,ab3,ab4 = st.columns(4)
        with ab1:
            if st.button("★ Favori" if favori else "☆ Favoriye Al", key=f"dp_fav_{kid}", use_container_width=True):
                favori_guncelle(kid, favori)
        with ab2:
            if st.button("🎨 Sunuma Hazırla", key=f"dp_sunum_{kid}", use_container_width=True, type="primary"):
                st.session_state["sunum_portfoy"] = sel
                st.switch_page("pages/Sunum_Merkezi_V2_Demo.py")
        with ab3:
            if st.button("＋ Yeni Portföy", key=f"dp_yeni_{kid}", use_container_width=True):
                st.session_state["pm_aktif_sekme"] = "yeni_portfoy"
                st.session_state.pop("pm_selected_id", None); st.rerun()
        with ab4:
            if st.button("✖ Kapat", key=f"dp_kapat_{kid}", use_container_width=True):
                st.session_state.pop("pm_selected_id", None)
                st.session_state["pm_aktif_sekme"] = "bos"; st.rerun()

        mail_icerik = sel.get("mail_icerigi","")
        if mail_icerik:
            with st.expander("📧 Mail İçeriği"):
                st.text(mail_icerik[:2000])
