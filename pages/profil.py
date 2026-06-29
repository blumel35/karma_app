# pages/profil.py
# Danışman Profil Sayfası — fotoğraf yükleme, bilgi güncelleme

import streamlit as st
import io, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from PIL import Image
from core.auth import oturum_kontrol, profil_guncelle, foto_yukle, cikis_yap

# Session sync — her zaman kullanici dict'inden yaz
_k = st.session_state.get("kullanici", {})
if _k:
    _ad = _k.get("ad_soyad") or _k.get("ad", "")
    st.session_state["user_role"]     = _k.get("rol", "danisan")
    st.session_state["user_name"]     = _ad
    st.session_state["user_initials"] = "".join(w[0].upper() for w in _ad.split()[:2] if w)

if not st.session_state.get("kullanici"):
    st.switch_page("pages/giris.py")

from core.ui_helpers import render_navbar, render_page_header

render_navbar(
    user_role=st.session_state.get("user_role", "danisan"),
    user_name=st.session_state.get("user_name", ""),
    user_initials=st.session_state.get("user_initials", ""),
)

render_page_header("👤 Profilim", "Bilgilerinizi güncelleyin, sunum şablonlarında otomatik kullanılır.")

kullanici = st.session_state.get("kullanici", {})

# ─────────────────────────────────────────────────────────────────────────────
# YARDIMCILAR
# ─────────────────────────────────────────────────────────────────────────────
def _pil_to_bytes(f, quality=88) -> bytes:
    if f is None:
        return b""
    try:
        f.seek(0)
        img = Image.open(f).convert("RGB")
        w, h = img.size
        # Boy fotoğraf — üst kısmı al
        if h > w * 1.2:
            crop_h = int(w * 1.0)
            img = img.crop((0, 0, w, crop_h))
        # Kareye çevir
        w2, h2 = img.size
        if w2 != h2:
            mn = min(w2, h2)
            left = (w2 - mn) // 2
            img = img.crop((left, 0, left + mn, mn))
        # Boyutu küçült (7.9MB çok büyük)
        img = img.resize((600, 600), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=quality)
        return buf.getvalue()
    except Exception:
        return b""


def _circle_img(raw: bytes, size: int = 120) -> Image.Image | None:
    if not raw:
        return None
    try:
        from PIL import ImageDraw
        img = Image.open(io.BytesIO(raw)).convert("RGBA")
        w, h = img.size
        # Boy fotoğraf için üst %40'ı al (yüz genellikle orada)
        if h > w * 1.2:
            crop_h = int(w * 1.0)
            img = img.crop((0, 0, w, crop_h))
        # Kareye çevir (ortadan)
        w2, h2 = img.size
        if w2 != h2:
            mn = min(w2, h2)
            left = (w2 - mn) // 2
            top = 0  # üstten başla — yüz genelde üstte
            img = img.crop((left, top, left + mn, top + mn))
        img = img.resize((size, size), Image.LANCZOS)
        mask = Image.new("L", (size, size), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, size, size), fill=255)
        img.putalpha(mask)
        return img
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────────────────────
# LAYOUT
# ─────────────────────────────────────────────────────────────────────────────
# Profil özeti üst kısım
p_col, info_col = st.columns([1, 3], gap="large")

with p_col:
    foto_url   = kullanici.get("foto_url", "")
    foto_bytes = kullanici.get("foto_bytes")
    foto_path  = kullanici.get("foto_path", "")

    _profil_foto_shown = False
    if foto_bytes:
        _circ = _circle_img(foto_bytes, 120)
        if _circ:
            st.image(_circ, width=120)
            _profil_foto_shown = True
    if not _profil_foto_shown and foto_path and os.path.exists(foto_path):
        try:
            with open(foto_path, "rb") as _pf:
                _raw = _pf.read()
            _circ = _circle_img(_raw, 120)
            if _circ:
                st.image(_circ, width=120)
                _profil_foto_shown = True
        except Exception:
            pass
    if not _profil_foto_shown and foto_url and foto_url.startswith("http"):
        st.image(foto_url, width=120, caption="Mevcut fotoğraf")
        _profil_foto_shown = True
    if not _profil_foto_shown:
        st.markdown("""
        <div style="width:120px;height:120px;border-radius:60px;
                    background:#1E3A5F;display:flex;align-items:center;
                    justify-content:center;font-size:40px;color:#fff;">
            👤
        </div>""", unsafe_allow_html=True)

with info_col:
    _profil_ad = kullanici.get("ad_soyad") or kullanici.get("ad", "Kullanıcı")
    st.markdown(f"### {_profil_ad}")
    rol_label = {
        "admin":         "Admin",
        "broker":        "Broker",
        "danisan":       "Danışman",
        "ofis":          "Ofis Yöneticisi",
        "yonetici":      "Yönetici",
        "gd":            "Gayrimenkul Danışmanı",
        "ofis_asistani": "Ofis Asistanı",
        "medya":         "Medya",
    }.get(kullanici.get("rol", ""), kullanici.get("rol", ""))
    st.caption(f"{rol_label}  ·  {kullanici.get('email','')}")
    if kullanici.get("ofis_adi"):
        st.caption(f"🏢 {kullanici['ofis_adi']}")
    if st.button("🚪 Çıkış Yap", key="cikis_btn"):
        cikis_yap()
        st.switch_page("pages/giris.py")

st.markdown("---")

# ─────────────────────────────────────────────────────────────────────────────
# FORM
# ─────────────────────────────────────────────────────────────────────────────
tab1, tab2 = st.tabs(["📋 Bilgiler", "📷 Fotoğraf & Logo"])

with tab1:
    c1, c2 = st.columns(2)
    with c1:
        ad       = st.text_input("Ad Soyad", value=kullanici.get("ad",""), key="p_ad")
        telefon  = st.text_input("Telefon", value=kullanici.get("telefon",""),
                                 key="p_tel", placeholder="+90 532 000 00 00")
        unvan    = st.text_input("Unvan", value=kullanici.get("unvan","Gayrimenkul Danışmanı"),
                                 key="p_unvan")
    with c2:
        ofis_adi = st.text_input("Ofis / Şirket", value=kullanici.get("ofis_adi",""),
                                 key="p_ofis", disabled=False)
        website  = st.text_input("Web Sitesi", value=kullanici.get("website",""),
                                 key="p_web", placeholder="https://...")
        instagram = st.text_input("Instagram", value=kullanici.get("instagram",""),
                                  key="p_ig", placeholder="@kullanici")

    if st.button("💾 Bilgileri Kaydet", type="primary", key="save_info"):
        ok = profil_guncelle(kullanici["id"], {
            "ad": ad, "telefon": telefon, "unvan": unvan,
            "website": website, "instagram": instagram,
        })
        if ok:
            # Session güncelle
            st.session_state["kullanici"].update({
                "ad": ad, "telefon": telefon, "unvan": unvan,
            })
            st.session_state["user_name"] = ad
            st.session_state["user_initials"] = "".join(
                w[0].upper() for w in ad.split()[:2]
            )
            st.success("✅ Bilgiler güncellendi!")
        else:
            st.warning("Kaydedilemedi (Supabase bağlantısı yok). Oturum boyunca geçerli.")
            st.session_state["kullanici"].update({"ad": ad, "telefon": telefon})

with tab2:
    st.markdown("**Profil Fotoğrafı**")
    st.caption("Sunum şablonlarında ve ofis panelinde görünür. Yuvarlak kırpılır.")

    foto_file = st.file_uploader("Fotoğraf Yükle", type=["jpg","jpeg","png","webp"],
                                  key="foto_upload")

    if foto_file:
        foto_raw = _pil_to_bytes(foto_file)
        circ = _circle_img(foto_raw, 120)
        if circ:
            st.image(circ, width=120, caption="Önizleme")

        if st.button("📤 Profil Fotoğrafını Kaydet", type="primary", key="save_foto"):
            # Her durumda önce session'a yaz — sidebar anında güncellenir
            st.session_state["kullanici"]["foto_bytes"] = foto_raw
            with st.spinner("Kaydediliyor..."):
                url = foto_yukle(kullanici["id"], foto_raw, "profil.jpg", "image/jpeg")
            if url:
                profil_guncelle(kullanici["id"], {"foto_url": url})
                st.session_state["kullanici"]["foto_url"] = url
                st.toast("✅ Profil fotoğrafı kaydedildi!")
            else:
                st.toast("✅ Fotoğraf oturum boyunca kaydedildi.")
            st.rerun()
    elif kullanici.get("foto_url"):
        st.image(kullanici["foto_url"], width=120)

    st.markdown("---")
    st.markdown("**Ofis Logosu**")
    st.caption("Sunum şablonlarının köşesinde görünür.")

    logo_file = st.file_uploader("Logo Yükle", type=["jpg","jpeg","png","webp"],
                                  key="logo_upload")

    if logo_file:
        logo_file.seek(0)
        logo_raw = logo_file.read()
        st.image(logo_raw, width=200, caption="Logo önizleme")

        if st.button("📤 Logoyu Kaydet", type="primary", key="save_logo"):
            st.session_state["kullanici"]["logo_bytes"] = logo_raw
            with st.spinner("Kaydediliyor..."):
                url = foto_yukle(kullanici["id"], logo_raw, "logo.png", "image/png")
            if url:
                profil_guncelle(kullanici["id"], {"logo_url": url})
                st.session_state["kullanici"]["logo_url"] = url
                st.toast("✅ Logo kaydedildi!")
            else:
                st.toast("✅ Logo oturum boyunca kaydedildi.")
            st.rerun()
    elif kullanici.get("logo_url"):
        st.image(kullanici["logo_url"], width=200)
