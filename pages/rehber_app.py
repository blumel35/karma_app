import base64
import re
from io import BytesIO
from pathlib import Path
from datetime import datetime
from urllib.parse import quote

import pandas as pd
import streamlit as st

from core.ui_helpers import render_navbar

# Veri Supabase'den çekiliyor — Excel path'lere gerek yok

render_navbar(
    user_role=st.session_state.get("user_role", "danisan"),
    user_name=st.session_state.get("user_name", ""),
    user_initials=st.session_state.get("user_initials", ""),
)
HERO_GORSEL_PATH = "assets/network_hero.png"

# "il" değeri Türkiye dışında bir ülke olan satırlarda "Mh." eki anlamsız
# olduğu için bu iller için farklı bir mahalle etiketi formatı kullanılır.
YABANCI_ULKELER = {
    "United Kingdom", "Birleşik Krallık",
    "Greece", "Yunanistan",
    "K.K.T.C.", "KKTC",
}

# Eşleştirme sorunları çözülene kadar ofis kartlarında logo yerine
# ofis adı yazısı gösterilsin. Logo eşleştirmesi tamamlanınca True yapılabilir.
LOGO_GOSTER = True


AKS_SIRASI = [
    "İzmir Merkez",
    "Kuzey Aksı",
    "Güney Aksı",
    "Yarımada / Batı Aksı",
    "Doğu / Dış Aks",
    "İzmir Dışı",
]

KPI_IKONLAR = {
    "ofis": """
    <svg viewBox="0 0 24 24" width="20" height="20" xmlns="http://www.w3.org/2000/svg">
        <rect x="4" y="3" width="16" height="18" rx="2" fill="none" stroke="{renk}" stroke-width="1.8" />
        <line x1="9" y1="7" x2="9" y2="7.2" stroke="{renk}" stroke-width="2" stroke-linecap="round" />
        <line x1="15" y1="7" x2="15" y2="7.2" stroke="{renk}" stroke-width="2" stroke-linecap="round" />
        <line x1="9" y1="11" x2="9" y2="11.2" stroke="{renk}" stroke-width="2" stroke-linecap="round" />
        <line x1="15" y1="11" x2="15" y2="11.2" stroke="{renk}" stroke-width="2" stroke-linecap="round" />
        <rect x="10" y="15" width="4" height="6" fill="{renk}" />
    </svg>
    """,
    "danisman": """
    <svg viewBox="0 0 24 24" width="20" height="20" xmlns="http://www.w3.org/2000/svg">
        <circle cx="9" cy="8" r="3" fill="none" stroke="{renk}" stroke-width="1.8" />
        <path d="M3 20 C3 16 6 14 9 14 C12 14 15 16 15 20" fill="none" stroke="{renk}" stroke-width="1.8" stroke-linecap="round" />
        <circle cx="17" cy="7" r="2.4" fill="none" stroke="{renk}" stroke-width="1.8" />
        <path d="M14 19 C14 16 16 14.5 18.5 14.5 C21 14.5 21.5 16 21.5 18" fill="none" stroke="{renk}" stroke-width="1.8" stroke-linecap="round" />
    </svg>
    """,
    "broker": """
    <svg viewBox="0 0 24 24" width="20" height="20" xmlns="http://www.w3.org/2000/svg">
        <circle cx="8" cy="9" r="4" fill="none" stroke="{renk}" stroke-width="1.8" />
        <line x1="11" y1="12" x2="20" y2="21" stroke="{renk}" stroke-width="1.8" stroke-linecap="round" />
        <line x1="15" y1="16" x2="17.5" y2="18.5" stroke="{renk}" stroke-width="1.8" stroke-linecap="round" />
        <line x1="18" y1="13" x2="20.5" y2="15.5" stroke="{renk}" stroke-width="1.8" stroke-linecap="round" />
    </svg>
    """,
    "bolge": """
    <svg viewBox="0 0 24 24" width="20" height="20" xmlns="http://www.w3.org/2000/svg">
        <circle cx="6" cy="6" r="2.2" fill="{renk}" />
        <circle cx="18" cy="6" r="2.2" fill="{renk}" />
        <circle cx="12" cy="14" r="2.2" fill="{renk}" />
        <circle cx="5" cy="19" r="2.2" fill="{renk}" />
        <circle cx="19" cy="19" r="2.2" fill="{renk}" />
        <line x1="6" y1="6" x2="12" y2="14" stroke="{renk}" stroke-width="1.4" />
        <line x1="18" y1="6" x2="12" y2="14" stroke="{renk}" stroke-width="1.4" />
        <line x1="5" y1="19" x2="12" y2="14" stroke="{renk}" stroke-width="1.4" />
        <line x1="19" y1="19" x2="12" y2="14" stroke="{renk}" stroke-width="1.4" />
    </svg>
    """,
    "pin": """
    <svg viewBox="0 0 24 24" width="14" height="14" xmlns="http://www.w3.org/2000/svg">
        <path d="M12 2 C16 2 19 5 19 9 C19 14 12 22 12 22 C12 22 5 14 5 9 C5 5 8 2 12 2 Z" fill="{renk}" />
        <circle cx="12" cy="9" r="2.6" fill="#ffffff" />
    </svg>
    """,
}


@st.cache_data(ttl=3600)
def load_data():
    """Supabase'den ofis ve danışman verilerini tam sayfalı çek."""
    import os

    def _select_all_active(supa, table_name, order_cols=None, page_size=1000):
        """
        Supabase tek istekte varsayılan olarak sınırlı sayıda satır döndürebilir.
        Rehber danışman sayısı 1000'i geçtiği için tüm sayfaları range() ile çeker.
        """
        rows = []
        start = 0
        order_cols = order_cols or []

        while True:
            query = supa.table(table_name).select("*").eq("aktif", True)

            # Sayfalama stabil olsun diye sıralama ekliyoruz.
            for col in order_cols:
                query = query.order(col)

            res = query.range(start, start + page_size - 1).execute()
            batch = res.data or []
            rows.extend(batch)

            if len(batch) < page_size:
                break

            start += page_size

        return rows

    try:
        from supabase import create_client

        url = (os.environ.get("SUPABASE_URL")
               or st.secrets.get("SUPABASE_URL", "")
               or st.secrets.get("supabase", {}).get("url", ""))

        key = (os.environ.get("SUPABASE_SERVICE_KEY")
               or os.environ.get("SUPABASE_KEY")
               or st.secrets.get("SUPABASE_SERVICE_KEY", "")
               or st.secrets.get("SUPABASE_KEY", "")
               or st.secrets.get("supabase", {}).get("service_key", "")
               or st.secrets.get("supabase", {}).get("secret_key", "")
               or st.secrets.get("supabase", {}).get("publishable_key", ""))

        supa = create_client(url, key)

        ofis_data = _select_all_active(
            supa,
            "rehber_ofisler",
            order_cols=["ofis_adi"],
            page_size=1000,
        )

        danisman_data = _select_all_active(
            supa,
            "rehber_danismanlar",
            order_cols=["ofis_adi", "isim"],
            page_size=1000,
        )

        ofis = pd.DataFrame(ofis_data).fillna("")
        danisman = pd.DataFrame(danisman_data).fillna("")

        # Kolon adlarını rehber_app.py ile uyumlu hale getir
        ofis = ofis.rename(columns={"ofis_adi": "ofis"})
        danisman = danisman.rename(columns={"ofis_adi": "ofis"})

    except Exception as e:
        st.error(f"Supabase bağlantı hatası: {e}")
        ofis = pd.DataFrame(columns=["ofis", "telefon", "mail", "il", "ilce",
                                     "mahalle", "adres", "ofis_link", "bolge_tipi",
                                     "bolge_aksi", "logo_url", "logo_dosya"])
        danisman = pd.DataFrame(columns=["ofis", "isim", "unvan", "telefon",
                                         "mail", "foto_url", "profil_link"])

    # Boş veri ihtimalinde groupby/merge patlamasın.
    if "ofis" not in ofis.columns:
        ofis["ofis"] = ""
    if "ofis" not in danisman.columns:
        danisman["ofis"] = ""

    # Danışman sayısını ofis tablosuna gerçek danışman tablosundan ekle.
    sayilar = danisman.groupby("ofis").size().reset_index(name="danisman_sayisi")
    ofis = ofis.drop(columns=["danisman_sayisi"], errors="ignore")
    ofis = ofis.merge(sayilar, on="ofis", how="left")
    ofis["danisman_sayisi"] = ofis["danisman_sayisi"].fillna(0).astype(int)

    # Danışman satırlarına ofis bölge bilgilerini ekle.
    gerekli_kolonlar = ["ofis", "il", "ilce", "mahalle", "bolge_aksi"]
    for col in gerekli_kolonlar:
        if col not in ofis.columns:
            ofis[col] = ""
    danisman = danisman.merge(
        ofis[gerekli_kolonlar],
        on="ofis",
        how="left",
        suffixes=("", "_ofis")
    ).fillna("")

    return danisman, ofis


def wa_numarasi(telefon):
    rakamlar = re.sub(r"\D", "", telefon or "")
    if not rakamlar:
        return ""
    if rakamlar.startswith("0"):
        rakamlar = "90" + rakamlar[1:]
    elif not rakamlar.startswith("90"):
        rakamlar = "90" + rakamlar
    return rakamlar


@st.cache_data
def logo_b64(yol):
    """Yerel dosya veya CDN URL'den logo verisi döndürür."""
    if not yol:
        return None
    # CDN URL ise direkt kullan (data URI yerine src olarak)
    if yol.startswith("http"):
        return yol  # URL döndür, base64 değil
    try:
        return base64.b64encode(Path(yol).read_bytes()).decode("utf-8")
    except (FileNotFoundError, OSError):
        return None


if st.button("🔄 Rehber verisini yenile"):
    load_data.clear()
    st.rerun()

danisman_df, ofis_df = load_data()

if "secili_aks" not in st.session_state:
    st.session_state["secili_aks"] = "İzmir Merkez"

if "secili_ofis" not in st.session_state:
    st.session_state["secili_ofis"] = ""

if "secili_ofisler" not in st.session_state:
    st.session_state["secili_ofisler"] = []

if "secili_danismanlar" not in st.session_state:
    st.session_state["secili_danismanlar"] = []

if "secim_modu" not in st.session_state:
    st.session_state["secim_modu"] = False

if "aks" in st.query_params or "ofis" in st.query_params:
    if "aks" in st.query_params:
        secilen_aks = st.query_params["aks"]
        if secilen_aks in AKS_SIRASI or secilen_aks == "Tümü":
            st.session_state["secili_aks"] = secilen_aks

    if "ofis" in st.query_params:
        secilen_ofis = st.query_params["ofis"]
        if secilen_ofis in set(ofis_df["ofis"]):
            st.session_state["secili_ofis"] = secilen_ofis
        else:
            st.session_state["secili_ofis"] = ""
    else:
        st.session_state["secili_ofis"] = ""

    st.query_params.clear()
    st.rerun()


st.markdown("""
<style>
.main .block-container {
    padding-top: 0.8rem;
    padding-left: 2.4rem;
    padding-right: 2.4rem;
    max-width: 100%;
}
.hero-card {
    position: relative;
    border-radius: 16px;
    overflow: hidden;
    height: 230px;
    margin-bottom: 16px;
    background-size: cover;
    background-position: center 20%;
    background-color: #e8edf3;
}
.hero-overlay {
    position: absolute;
    inset: 0;
    background: linear-gradient(90deg, rgba(246,245,241,0.97) 0%, rgba(246,245,241,0.85) 38%, rgba(246,245,241,0.05) 75%);
}
.hero-text {
    position: relative;
    z-index: 1;
    max-width: 60%;
    padding: 28px 0 28px 32px;
}
.hero-label {
    font-size: 12px;
    font-weight: 800;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: #D6202B;
}
.title {
    font-size: 32px;
    font-weight: 950;
    color: #0b1f4d;
    margin-top: 6px;
}
.subtitle {
    color: #667085;
    font-size: 14px;
    margin-top: 8px;
}
.metric-soft {
    display: flex;
    align-items: center;
    gap: 12px;
    border: 1px solid #e8edf3;
    border-radius: 16px;
    background: #fff;
    box-shadow: 0 4px 14px rgba(20,30,50,0.04);
    padding: 12px 16px;
}
.metric-icon {
    width: 38px;
    height: 38px;
    border-radius: 11px;
    background: #EEF2FB;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
}
.metric-label {
    font-size: 12px;
    color: #8a93a6;
}
.metric-value {
    font-size: 20px;
    font-weight: 900;
    color: #0b1f4d;
}
.person-row {
    border-top: 1px solid #edf1f6;
    padding: 12px 0;
    min-height: 82px;
}
.person-photo {
    width: 58px;
    height: 58px;
    object-fit: cover;
    border-radius: 50%;
    float: left;
    margin-right: 12px;
}
.person-name {
    font-size: 14px;
    font-weight: 850;
    color: #13233a;
}
.person-info {
    font-size: 12px;
    color: #475467;
    word-break: break-word;
}
.clearfix::after {
    content: "";
    clear: both;
    display: table;
}
.aks-tab {
    border: 1px solid #e8edf3;
    border-radius: 999px;
    padding: 8px 10px;
    min-height: 44px;
    text-align: center;
    transition: background .15s ease, transform .1s ease, box-shadow .15s ease;
    cursor: pointer;
}
.aks-tab:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(20,30,50,0.08);
}
.aks-tab-title {
    font-size: 12.5px;
    font-weight: 950;
    line-height: 1.2;
}
.aks-tab-sub {
    margin-top: 2px;
    font-size: 10px;
    font-weight: 750;
    opacity: .9;
}
.aks-header-title {
    font-size: 20px;
    font-weight: 950;
    color: #0b1f4d;
}
.aks-header-sub {
    margin-top: 2px;
    font-size: 12px;
    color: #667085;
    font-weight: 700;
}
.ilce-header {
    display: flex;
    align-items: center;
    gap: 6px;
    margin-top: 16px;
    margin-bottom: 8px;
}
.ilce-header-title {
    font-size: 15px;
    font-weight: 950;
    color: #0b1f4d;
}
.ilce-header-count {
    font-size: 12px;
    font-weight: 700;
    color: #98a2b3;
}
.bolum-header {
    margin-top: 20px;
    padding-bottom: 6px;
    border-bottom: 2px solid #0b1f4d;
    font-size: 13px;
    font-weight: 800;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #0b1f4d;
}
.office-card-v2 {
    background: #f1f3f6;
    border-radius: 10px;
    padding: 10px 12px;
    min-height: 72px;
    margin-bottom: 6px;
    transition: background .15s ease, transform .1s ease;
    cursor: pointer;
}
.office-card-v2:hover {
    background: #e6e9ee;
    transform: translateY(-1px);
}
.office-name-v2 {
    font-size: 15px;
    font-weight: 950;
    color: #0b1f4d;
}
.office-logo-v2 {
    height: 68px;
    max-width: 100%;
    object-fit: contain;
    object-position: left center;
    display: block;
    margin-bottom: 6px;
}
.office-mahalle-v2 {
    margin-top: 2px;
    font-size: 11px;
    font-weight: 500;
    letter-spacing: 0.02em;
    color: #98a2b3;
}
.office-count-v2 {
    display: inline-block;
    margin-top: 5px;
    padding: 1px 8px;
    border: 1px solid #d4d9e0;
    border-radius: 999px;
    font-size: 11px;
    font-weight: 700;
    color: #667085;
}
.office-telefon-v2 {
    margin-top: 4px;
    font-size: 11px;
    font-weight: 500;
    color: #98a2b3;
}
.secim-badge {
    display: inline-block;
    padding: 3px 12px;
    border-radius: 999px;
    background: #fef3e2;
    color: #b54708;
    font-size: 12px;
    font-weight: 700;
}
</style>
""", unsafe_allow_html=True)


def toggle_list_value(key, value, selected):
    liste = st.session_state.get(key, [])
    if selected and value not in liste:
        liste.append(value)
    if not selected and value in liste:
        liste.remove(value)
    st.session_state[key] = liste


@st.dialog("Toplu İletişim", width="large")
def toplu_iletisim_modal(secili_ofisler, mod):
    kisiler = danisman_df[danisman_df["ofis"].isin(secili_ofisler)].copy()

    st.caption(f"{len(secili_ofisler)} ofis · {len(kisiler)} danışman")

    st.markdown("---")

    # Danışman seçimi
    secili_toplu = []
    for ofis_adi in secili_ofisler:
        ofis_kisiler = kisiler[kisiler["ofis"] == ofis_adi]
        if ofis_kisiler.empty:
            continue
        st.markdown(f"**{ofis_adi}** ({len(ofis_kisiler)} danışman)")
        for _, row in ofis_kisiler.iterrows():
            key = f"toplu_{ofis_adi}_{row['isim']}"
            if st.checkbox(row["isim"], key=key, value=True):
                secili_toplu.append(row)

    if not secili_toplu:
        st.caption("Hiç danışman seçilmedi.")
        return

    st.markdown("---")
    st.markdown(f"**{len(secili_toplu)} danışman seçili**")

    import pandas as pd
    secili_df = pd.DataFrame(secili_toplu)

    if mod == "mail":
        mail_adresleri = [m for m in secili_df["mail"].tolist() if m]
        if mail_adresleri:
            mailto_str = "mailto:" + ",".join(mail_adresleri)
            yandex_link = f"https://mail.yandex.com/compose?mailto={quote(mailto_str)}"
            st.link_button("📧 Yandex Mail'de Aç", yandex_link, use_container_width=True)
        else:
            st.caption("Seçili danışmanların e-posta adresi bulunamadı.")

    else:
        numaralar = [
            wa_numarasi(r["telefon"])
            for _, r in secili_df.iterrows()
            if wa_numarasi(r["telefon"])
        ]

        if numaralar:
            wa_links_html = " ".join(
                f'<a href="https://wa.me/{n}" target="_blank" '
                f'style="display:inline-block;margin:3px;padding:5px 12px;'
                f'background:#25D366;color:white;border-radius:8px;'
                f'font-size:12px;text-decoration:none;">💬 {r["isim"]}</a>'
                for n, (_, r) in zip(numaralar, secili_df.iterrows())
            )
            st.markdown(wa_links_html, unsafe_allow_html=True)

            tum_numaralar = "\n".join(numaralar)
            st.code(tum_numaralar, language=None)
            st.caption("↑ Numaraları seçip kopyalayabilir veya WhatsApp Business'ta Yayın Listesi oluşturabilirsin.")


@st.dialog("Ofis Detayı", width="large")
def ofis_modal(ofis_adi):
    ofis_row = ofis_df[ofis_df["ofis"] == ofis_adi].iloc[0]
    kisiler = danisman_df[danisman_df["ofis"] == ofis_adi].copy()
    mahalle = ofis_row["mahalle"] if ofis_row["mahalle"] else "-"

    st.markdown(f"## {ofis_row['ofis']} Ofis")
    st.caption(f"{ofis_row['bolge_aksi']} · {ofis_row['ilce']} / {mahalle}")

    c1, c2 = st.columns(2)
    c1.write(f"**Telefon:** {ofis_row['telefon']}")
    c1.write(f"**E-posta:** {ofis_row['mail']}")
    c2.write(f"**Danışman:** {len(kisiler)}")
    c2.write(f"**Adres:** {ofis_row['adres']}")

    st.divider()

    f1, f2 = st.columns([2, 1])
    with f1:
        q = st.text_input("Danışman ara")
    with f2:
        sadece_broker = st.checkbox("Broker / Sahip")

    if sadece_broker:
        kisiler = kisiler[
            kisiler["unvan"].str.lower().str.contains("broker", na=False)
            | kisiler["unvan"].str.lower().str.contains("owner", na=False)
            | kisiler["unvan"].str.lower().str.contains("sahip", na=False)
        ]

    if q:
        q = q.lower()
        kisiler = kisiler[
            kisiler["isim"].str.lower().str.contains(q, na=False)
            | kisiler["mail"].str.lower().str.contains(q, na=False)
            | kisiler["telefon"].str.lower().str.contains(q, na=False)
        ]

    baslik_col, secim_col = st.columns([3, 1])
    with baslik_col:
        st.markdown(f"### Danışmanlar · {len(kisiler)}")

    # Checkbox'lar henüz bu turda render edilmedi; önceki turdan kalan
    # seçim durumunu session_state'ten okuyarak butonları listenin
    # üstünde gösterebiliriz.
    secili_modal_danisman = [
        row["isim"] for _, row in kisiler.iterrows()
        if st.session_state.get(f"danisman_sec_{ofis_adi}_{row['isim']}", False)
    ]

    if secili_modal_danisman:
        with secim_col:
            st.markdown(
                f'<div style="text-align:right; margin-top:18px;">'
                f'<span class="secim-badge">{len(secili_modal_danisman)} seçili</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

        secili_kisiler = kisiler[kisiler["isim"].isin(secili_modal_danisman)]

        mail_adresleri = [m for m in secili_kisiler["mail"] if m]
        wa_kisiler = [
            (row["isim"], wa_numarasi(row["telefon"]))
            for _, row in secili_kisiler.iterrows()
            if wa_numarasi(row["telefon"])
        ]

        aksiyon_butonlari = []

        if mail_adresleri:
            mailto_str = "mailto:" + ",".join(mail_adresleri)
            yandex_mail_link = f"https://mail.yandex.com/compose?mailto={quote(mailto_str)}"
            aksiyon_butonlari.append(("📧 Mail Gönder", yandex_mail_link))

        for isim, numara in wa_kisiler:
            aksiyon_butonlari.append((f"💬 {isim}", f"https://wa.me/{numara}"))

        if aksiyon_butonlari:
            for i in range(0, len(aksiyon_butonlari), 4):
                satir = aksiyon_butonlari[i:i + 4]
                aksiyon_cols = st.columns(len(satir))
                for col, (etiket, link) in zip(aksiyon_cols, satir):
                    with col:
                        st.link_button(etiket, link, use_container_width=True)

        if wa_kisiler:
            tum_numaralar = "\n".join(n for _, n in wa_kisiler)
            st.code(tum_numaralar, language=None)
            st.caption("↑ Numaraları kopyalayıp WhatsApp Business'ta Yayın Listesi oluşturabilirsin.")
        else:
            st.caption("Seçili danışmanlar için e-posta veya telefon bulunamadı.")

        st.divider()

    for _, row in kisiler.iterrows():
        check_key = f"danisman_sec_{ofis_adi}_{row['isim']}"
        st.checkbox(
            row["isim"],
            key=check_key
        )

        img = row["foto_url"] if row["foto_url"] else ""

        st.markdown(f"""
        <div class="person-row clearfix">
            <img class="person-photo" src="{img}">
            <div class="person-name">{row["isim"]}</div>
            <div class="person-info">{row["unvan"]}</div>
            <div class="person-info">☎ {row["telefon"]}</div>
            <div class="person-info">✉ {row["mail"]}</div>
            <div class="person-info"><a href="{row["profil_link"]}" target="_blank">Profili Aç</a></div>
        </div>
        """, unsafe_allow_html=True)


_hero_yolu = Path(HERO_GORSEL_PATH)

if not _hero_yolu.exists():
    _aday_dosyalar = sorted(Path("assets").glob("*.png")) if Path("assets").exists() else []
    if _aday_dosyalar:
        _hero_yolu = _aday_dosyalar[0]

_baslik_html = (
    '<div class="hero-overlay"></div>'
    '<div class="hero-text">'
    '<div class="hero-label">Network Ağı</div>'
    '<div class="title">Startkey Rehberi</div>'
    '<div class="subtitle">Aks seç, ilçeleri gör, ofisleri işaretle, gerektiğinde danışmanlara ulaş.</div>'
    '</div>'
)

if _hero_yolu.exists():
    _hero_b64 = base64.b64encode(_hero_yolu.read_bytes()).decode("utf-8")
    st.markdown(
        f'<div class="hero-card" style="background-image:url(\'data:image/png;base64,{_hero_b64}\');">'
        f'{_baslik_html}'
        f'</div>',
        unsafe_allow_html=True,
    )
else:
    st.markdown(f'<div class="hero-card">{_baslik_html}</div>', unsafe_allow_html=True)
    st.caption(f"Hero görseli bulunamadı: {Path(HERO_GORSEL_PATH).resolve()}")

broker_sayisi = danisman_df["unvan"].str.contains(
    "broker|owner|sahip", case=False, na=False
).sum()

m1, m2, m3, m4 = st.columns(4)
for col, (label, value, ikon_anahtari) in zip(
    [m1, m2, m3, m4],
    [
        ("Toplam Ofis", len(ofis_df), "ofis"),
        ("Toplam Danışman", len(danisman_df), "danisman"),
        ("Broker / Sahip", broker_sayisi, "broker"),
        ("Bölge / Aks", ofis_df["bolge_aksi"].nunique(), "bolge"),
    ]
):
    with col:
        ikon = KPI_IKONLAR[ikon_anahtari].format(renk="#3068A8").replace("\n", "")
        st.markdown(
            f'<div class="metric-soft">'
            f'<div class="metric-icon">{ikon}</div>'
            f'<div>'
            f'<div class="metric-value">{value}</div>'
            f'<div class="metric-label">{label}</div>'
            f'</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

@st.cache_data
def rehber_excel_hazirla(ofis_df: pd.DataFrame, danisman_df: pd.DataFrame) -> bytes:
    """Tüm Startkey ofislerini ve danışmanlarını iki sekmeli bir Excel dosyası olarak hazırlar."""
    ofis_export = ofis_df.drop(columns=["logo_url", "logo_dosya"], errors="ignore").copy()
    danisman_export = danisman_df.drop(columns=["foto_url"], errors="ignore").copy()

    kolon_adlari_ofis = {
        "ofis": "Ofis Adı", "telefon": "Telefon", "mail": "Mail", "il": "İl",
        "ilce": "İlçe", "mahalle": "Mahalle", "adres": "Adres",
        "ofis_link": "Ofis Linki", "bolge_tipi": "Bölge Tipi",
        "bolge_aksi": "Bölge / Aks", "danisman_sayisi": "Danışman Sayısı",
    }
    kolon_adlari_dan = {
        "ofis": "Ofis Adı", "isim": "İsim", "unvan": "Unvan", "telefon": "Telefon",
        "mail": "Mail", "profil_link": "Profil Linki", "il": "İl", "ilce": "İlçe",
        "mahalle": "Mahalle", "bolge_aksi": "Bölge / Aks",
    }
    ofis_export = ofis_export.rename(columns=kolon_adlari_ofis)
    danisman_export = danisman_export.rename(columns=kolon_adlari_dan)

    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        ofis_export.to_excel(writer, index=False, sheet_name="Ofisler")
        danisman_export.to_excel(writer, index=False, sheet_name="Danışmanlar")
    buf.seek(0)
    return buf.getvalue()

dl_bosluk, dl_yenile, dl_buton = st.columns([4.2, 1.4, 1.4])
with dl_yenile:
    if st.button("🔄 Rehberi Yenile", use_container_width=True,
                 help="Supabase'den taze veri çeker (normalde 1 saat önbelleğe alınır)"):
        load_data.clear()
        st.toast("Rehber yenilendi ✓")
        st.rerun()
with dl_buton:
    st.download_button(
        "📥 Rehberi Excel'e Aktar",
        data=rehber_excel_hazirla(ofis_df, danisman_df),
        file_name=f"startkey_rehber_{datetime.now().strftime('%Y%m%d')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )

aks_ozet = (
    ofis_df.groupby("bolge_aksi")
    .agg(
        ofis_sayisi=("ofis", "count"),
        danisman_sayisi=("danisman_sayisi", "sum"),
    )
    .reset_index()
)

aks_ozet["sira"] = aks_ozet["bolge_aksi"].apply(
    lambda x: AKS_SIRASI.index(x) if x in AKS_SIRASI else 99
)
aks_ozet = aks_ozet.sort_values("sira")

tab_listesi = [("Tümü", len(ofis_df), int(ofis_df["danisman_sayisi"].sum()))]
tab_listesi += [
    (row["bolge_aksi"], int(row["ofis_sayisi"]), int(row["danisman_sayisi"]))
    for _, row in aks_ozet.iterrows()
]

tab_cols = st.columns(len(tab_listesi))

for col, (aks, ofis_sayisi, danisman_sayisi) in zip(tab_cols, tab_listesi):
    aktif = st.session_state["secili_aks"] == aks

    if aktif:
        bg = "#3068A8"
        baslik_renk = "#ffffff"
        alt_renk = "#ffffff"
        golge = "box-shadow:0 4px 12px rgba(48,104,168,0.30);"
    else:
        bg = "#ffffff"
        baslik_renk = "#0b1f4d"
        alt_renk = "#8a93a6"
        golge = ""

    with col:
        st.markdown(f"""
        <a href="?aks={quote(aks)}" target="_self" style="text-decoration:none; display:block;">
            <div class="aks-tab" style="background:{bg}; {golge}">
                <div class="aks-tab-title" style="color:{baslik_renk};">{aks}</div>
                <div class="aks-tab-sub" style="color:{alt_renk};">{ofis_sayisi} ofis · {danisman_sayisi} danışman</div>
            </div>
        </a>
        """, unsafe_allow_html=True)

secili_aks = st.session_state["secili_aks"]

if secili_aks:
    st.divider()

    if secili_aks == "Tümü":
        aks_df = ofis_df.copy()
    else:
        aks_df = ofis_df[ofis_df["bolge_aksi"] == secili_aks].copy()

    aks_df = aks_df.sort_values(["ilce", "mahalle", "ofis"])

    toplam_ofis = len(aks_df)
    toplam_danisman = int(aks_df["danisman_sayisi"].sum())

    if secili_aks == "Tümü":
        baslik_metni = "Tüm Bölgeler"
    elif secili_aks == "İzmir Dışı":
        baslik_metni = "İzmir Dışı"
    else:
        temiz_ad = re.sub(r"\s*Aks(ı)?$", "", secili_aks)
        baslik_metni = f"{temiz_ad} Aksı"

    ust_sol, ust_sag = st.columns([3, 2])

    with ust_sol:
        st.markdown(
            f'<div class="aks-header-title">{baslik_metni}</div>'
            f'<div class="aks-header-sub">{toplam_ofis} Ofis, {toplam_danisman} Danışman listeleniyor</div>',
            unsafe_allow_html=True,
        )

    with ust_sag:
        t1, t2, t3 = st.columns([2, 1, 1])
        with t1:
            st.session_state["secim_modu"] = st.toggle(
                "Seçim Modu",
                value=st.session_state["secim_modu"],
            )
        secili_var = (
            st.session_state["secim_modu"]
            and len(st.session_state["secili_ofisler"]) > 0
        )
        with t2:
            posta_tikla = st.button("Mail", use_container_width=True, disabled=not secili_var)
        with t3:
            wa_tikla = st.button("WhatsApp", use_container_width=True, disabled=not secili_var)

    secili_ofis_sayisi = len(st.session_state["secili_ofisler"])

    if st.session_state["secim_modu"] and secili_ofis_sayisi > 0:
        b1, b2 = st.columns([5, 1])
        with b1:
            st.caption(f"{secili_ofis_sayisi} ofis seçildi.")
        with b2:
            if st.button("Seçimleri Temizle", use_container_width=True):
                st.session_state["secili_ofisler"] = []
                st.rerun()

    if secili_var and (posta_tikla or wa_tikla):
        mod = "mail" if posta_tikla else "wa"
        toplu_iletisim_modal(st.session_state["secili_ofisler"], mod)

    def grup_basligi_goster(baslik, grup_df):
        ofis_sayisi = len(grup_df)
        danisman_sayisi = int(grup_df["danisman_sayisi"].sum())

        pin = KPI_IKONLAR["pin"].format(renk="#D6202B").replace("\n", "")

        st.markdown(
            f'<div class="ilce-header">'
            f'{pin}'
            f'<div class="ilce-header-title">{baslik}</div>'
            f'<div class="ilce-header-count">({ofis_sayisi} Ofis • {danisman_sayisi} Danışman)</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    def ofis_kartlari_goster(grup_df, ilce_bilgisi_goster=False):
        for i in range(0, len(grup_df), 4):
            cols = st.columns(4)

            for col, (_, row) in zip(cols, grup_df.iloc[i:i+4].iterrows()):
                ofis_adi = row["ofis"]
                yabanci = row["il"].strip() in YABANCI_ULKELER

                if yabanci:
                    if ilce_bilgisi_goster:
                        mahalle = f"{row['ilce']} · {row['mahalle']}" if row["mahalle"] else row["ilce"]
                    else:
                        mahalle = f"{row['mahalle']}, {row['il']}" if row["mahalle"] else row["il"]
                else:
                    temel = f"{row['mahalle']} Mh." if row["mahalle"] else "-"
                    mahalle = f"{row['ilce']} · {temel}" if ilce_bilgisi_goster else temel

                selected = ofis_adi in st.session_state["secili_ofisler"]

                with col:
                    if st.session_state["secim_modu"]:
                        sec = st.checkbox(
                            "Seç",
                            value=selected,
                            key=f"ofis_select_{ofis_adi}"
                        )
                        toggle_list_value("secili_ofisler", ofis_adi, sec)

                    logo_kaynak = (row.get("logo_url", "") or row.get("logo_dosya", "")) if LOGO_GOSTER else ""
                    logo_data = logo_b64(logo_kaynak) if logo_kaynak else None

                    if logo_data:
                        if logo_data.startswith("http"):
                            # CDN URL — direkt src
                            ust_html = f'<img class="office-logo-v2" src="{logo_data}" />' 
                        else:
                            uzanti = Path(logo_kaynak).suffix.lstrip(".").lower() or "png"
                            ust_html = f'<img class="office-logo-v2" src="data:image/{uzanti};base64,{logo_data}" />'
                    else:
                        ust_html = f'<div class="office-name-v2" translate="no">{ofis_adi}</div>'

                    kart_html = (
                        f'<a href="?aks={quote(secili_aks)}&ofis={quote(ofis_adi)}" target="_self" style="text-decoration:none; display:block;">'
                        f'<div class="office-card-v2">'
                        f'{ust_html}'
                        f'<div class="office-mahalle-v2" translate="no">{mahalle}</div>'
                        f'<div class="office-count-v2">{int(row["danisman_sayisi"])} danışman</div>'
                        f'<div class="office-telefon-v2" translate="no">☎ {row["telefon"]}</div>'
                        f'</div>'
                        f'</a>'
                    )

                    st.markdown(kart_html, unsafe_allow_html=True)

    if secili_aks == "İzmir Dışı":
        bolumler = (
            ("Türkiye", aks_df[~aks_df["il"].str.strip().isin(YABANCI_ULKELER)]),
            ("Yurt Dışı", aks_df[aks_df["il"].str.strip().isin(YABANCI_ULKELER)]),
        )

        for bolum_adi, bolum_df in bolumler:
            if bolum_df.empty:
                continue

            st.markdown(f'<div class="bolum-header">{bolum_adi}</div>', unsafe_allow_html=True)

            for il, grup_df in bolum_df.groupby("il", sort=True):
                grup_basligi_goster(il, grup_df)
                ofis_kartlari_goster(grup_df, ilce_bilgisi_goster=True)
    else:
        for ilce, ilce_df in aks_df.groupby("ilce", sort=True):
            grup_basligi_goster(ilce, ilce_df)
            ofis_kartlari_goster(ilce_df)

if st.session_state["secili_ofis"]:
    ofis_modal(st.session_state["secili_ofis"])