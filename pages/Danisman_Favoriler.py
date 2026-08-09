"""
pages/Danisman_Favoriler.py

Favori Listem ekranı. Eski Danisman_Pano.py içindeki "Takip Listem"
sekmesinin ayrı bir sayfaya çıkarılmış hali — isim "Favori Listem" olarak
sabitlendi (mockup'ta da bu isimle netleşti).

Kart tasarımı diğer panolarla BİREBİR AYNI (pano_html_olustur) — sadece
beslenen liste, tüm kayıtlar yerine favorilenmiş kayıtlarla sınırlı.

2. TUR (regresyon giderme, 08.08.2026): Önceki halde hem ayrı, bordered
bir filtre kutusu (kendi scoped CSS'iyle) hem de sekme yerine alt alta
"Favori Taleplerim" / "Favori Portföylerim" başlıkları vardı — Talep/
Portföy panolarıyla aynı görsel dile geçirildi: tek ana başlık ("Favori
Listem"), Talepler/Portföyler SEKMESİ, çerçevesiz minimalist toolbar,
TEK ortak CSS kaynağı (_inject_filtre_pill_css, artık burada tekrar
tanımlanmıyor).
"""

import streamlit as st
import streamlit.components.v1 as components

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.auth import oturum_kontrol
from core.pano_export import pano_html_olustur
from core.danisman_ortak import (
    talepleri_cek, portfoyleri_cek, islem_tipi_filtrele,
    favorileri_cek, su_anki_danisman, supabase_anon_secrets,
    render_topbar, hide_sidebar_css, _inject_filtre_pill_css,
)

if not oturum_kontrol():
    st.switch_page("pages/Danisman_Giris.py")

hide_sidebar_css()
render_topbar("Favori Listem", ikon="⭐", geri_hedefi="pages/Danisman_Secim.py")

su_kullanici = su_anki_danisman()
favori_kayitlari = favorileri_cek(su_kullanici)

if not favori_kayitlari:
    st.info("Henüz favori eklemedin — panodaki kartların üzerindeki ☆ yıldıza tıklayarak ekleyebilirsin.")
    st.stop()

favori_talep_idler = {f["kayit_id"] for f in favori_kayitlari if f["kaynak_tablo"] == "alici_talepleri"}
favori_portfoy_idler = {f["kayit_id"] for f in favori_kayitlari if f["kaynak_tablo"] == "portfoyler"}
favori_set = {(f["kaynak_tablo"], f["kayit_id"]) for f in favori_kayitlari}
supabase_url, supabase_anon = supabase_anon_secrets()

tum_favori_talepler = [v for v in talepleri_cek() if v["id"] in favori_talep_idler]
tum_favori_portfoyler = [v for v in portfoyleri_cek() if v["id"] in favori_portfoy_idler]

sekme_talep, sekme_portfoy = st.tabs([
    f"Talepler ({len(tum_favori_talepler)})",
    f"Portföyler ({len(tum_favori_portfoyler)})",
])


def _favori_sekme_icerik(havuz, kayit_tipi, key_prefix, baslik_iframe):
    """Her iki sekme de aynı çerçevesiz toolbar + filtre mantığını
    paylaşır — kod tekrarını önlemek için tek yerde.
    DÜZELTME (09.08.2026): "İlan Kaynağı" (Tümü/Zeta/Startkey) filtresi
    kaldırıldı — favori listesinde bu ayrımın pratik bir faydası yoktu.
    Artık Uzmanlık Bölgelerim'deki AYNI basit desen: tek filtre grubu
    (İşlem Tipi) + Yenile, aynı satırda."""
    _inject_filtre_pill_css()

    # DÜZELTME (3. tur — dikey alan sıkılaştırma): Talep/Portföy/Zeta
    # panolarındaki aynı sıkılaştırma deseni burada da uygulanıyor —
    # filtre alanının kapladığı dikey boşluk minimuma iniyor.
    st.markdown(f"""
    <style>
    div[class*="st-key-df_filtre_toolbar_{key_prefix}"] {{
        margin-top: -8px !important;
        margin-bottom: -8px !important;
    }}
    div[class*="st-key-df_filtre_toolbar_{key_prefix}"] div[data-testid="stHorizontalBlock"] {{
        gap: 0.5rem !important;
    }}
    div[class*="st-key-df_yenile_{key_prefix}"] button {{
        width: 38px !important; min-width: 38px !important; padding: 0 !important;
        min-height: 38px !important; height: 38px !important;
        font-size: 15px !important; border-radius: 8px !important;
        border-color: #e3e1da !important; background: #ffffff !important; color: #5b6478 !important;
    }}

    /* Mobil: tek filtre grubu olduğu için 2 sütun zaten tek satıra
       sığar — Uzmanlık Bölgelerim'deki AYNI desen. */
    @media (max-width: 480px) {{
        div[class*="st-key-df_filtre_toolbar_{key_prefix}"] div[data-testid="stHorizontalBlock"] {{
            display: grid !important;
            grid-template-columns: 1fr auto !important;
            align-items: center !important;
        }}
        div[class*="st-key-df_filtre_toolbar_{key_prefix}"] div[data-testid="stColumn"] {{
            width: auto !important; min-width: 0 !important;
        }}
    }}
    </style>
    """, unsafe_allow_html=True)

    with st.container(key=f"df_filtre_toolbar_{key_prefix}"):
        fcol1, fcol2 = st.columns([4, 1])
        with fcol1:
            islem_secim = st.radio(
                "İşlem Tipi", ["Tümü", "Satılık", "Kiralık"],
                horizontal=True, key=f"df_islem_{key_prefix}",
                label_visibility="collapsed",
            )
        with fcol2:
            if st.button("↻", key=f"df_yenile_{key_prefix}", help="Yenile"):
                favorileri_cek.clear()
                st.rerun()

    kayitlar = islem_tipi_filtrele(havuz, islem_secim)

    if not kayitlar:
        st.info("Bu filtrede favori listende kayıt yok.")
        return

    html_buf = pano_html_olustur(
        kayitlar, baslik_iframe, kayit_tipi=kayit_tipi,
        favori_destekli=True, favori_set=favori_set,
        supabase_url=supabase_url, supabase_anon_key=supabase_anon,
        mevcut_kullanici=su_kullanici,
    )
    components.html(html_buf.getvalue().decode("utf-8"), height=1200, scrolling=True)


with sekme_talep:
    _favori_sekme_icerik(tum_favori_talepler, "talep", "favori_talep", "Favori Taleplerim")

with sekme_portfoy:
    _favori_sekme_icerik(tum_favori_portfoyler, "portfoy", "favori_portfoy", "Favori Portföylerim")
