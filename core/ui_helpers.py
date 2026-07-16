import streamlit as st


# ═══════════════════════════════════════════════════════════════════════════════
# YENİ SOL SIDEBAR — st.sidebar kullanır, CSS ile stillendirilir
# ═══════════════════════════════════════════════════════════════════════════════

_NAV_SECTIONS = [
    {
        "key": "ana",
        "label": "",
        "pages": [
            ("pages/ana_sayfa.py", "Ana Sayfa", "🏠", []),
        ],
    },
    {
        "key": "calisma",
        "label": "Çalışma Alanım",
        "pages": [
            ("pages/gd_calisma_alani.py", "GD Çalışma Alanı", "🧭", []),
            ("pages/taleplerim.py", "Taleplerim", "👤", []),
            ("pages/portfoylerím.py", "Portföylerim", "🏡", []),
            ("pages/ajandam.py", "Ajandam", "🗓", []),
        ],
    },
    {
        "key": "havuz",
        "label": "Ortak Havuzlar",
        "pages": [
            ("pages/2_Talep_Tablosu.py", "Talep Havuzu", "🗂", []),
            ("pages/3_Portfoy_Tablosu.py", "Portföy Havuzu", "🏠", []),
            ("pages/arsiv_merkezi.py", "Arşiv Merkezi", "📦", []),
            ("pages/rehber_app.py", "Startkey Rehberi", "🏢", []),
        ],
    },
    {
        "key": "operasyon",
        "label": "Operasyon",
        "pages": [
            ("pages/4_Ofis_Paneli.py", "Ofis Paneli", "📊", []),
            ("pages/operasyon_merkezi.py", "Operasyon Merkezi", "⚙️", []),
            ("pages/sozlesmeler_ve_formlar.py", "Sözleşmeler ve Formlar", "📝", []),
        ],
    },
    {
        "key": "pazar_analiz",
        "label": "Pazar & Analiz",
        "pages": [
            ("pages/pazar_analiz.py", "Pazar Radar", "📡", []),
            ("pages/pazar_raporu.py", "Pazar Raporu", "📊", []),
            ("pages/startkey_portfoy_listesi.py", "Startkey İlanları", "🔎", []),
        ],
    },
    {
        "key": "yonetim_araclari",
        "label": "Yönetici / Eski Ekranlar",
        "pages": [
            ("pages/5_Mail_Islem.py", "Mail İşlem", "📨", []),
            ("pages/kullanici_sec.py", "Kullanıcı Görünümü", "👥", []),
        ],
    },
]

def _detect_active(current_path: str) -> str:
    try:
        path_only = current_path.split("?")[0].split("#")[0].rstrip("/")
    except Exception:
        path_only = ""
    if not path_only:
        return ""
    all_pages = []
    for section in _NAV_SECTIONS:
        for page_path, *_ in section["pages"]:
            all_pages.append(page_path)
    all_pages.sort(key=lambda p: len(p), reverse=True)
    for page_path in all_pages:
        page_name = page_path.split("/")[-1].replace(".py", "")
        if path_only.endswith("/" + page_name) or path_only == page_name:
            return page_path
    return ""


def _can_see(izin: list, role: str) -> bool:
    return not izin or role in izin


def render_navbar(user_role: str = "danisan",
                  user_name: str = "",
                  user_initials: str = ""):
    """
    Sol sidebar render eder (st.sidebar kullanır).
    Sayfa içeriğini doğrudan yazabilirsin — main_col döndürmez artık.

    Kullanım:
        render_navbar(user_role=..., user_name=..., user_initials=...)
        st.write("içerik")   # direkt ana alana yaz
    """
    # ── TEK KAYNAK: st.session_state["kullanici"] dict'inden override et ──────
    _k = st.session_state.get("kullanici", {})
    _original_role = user_role  # debug amaçlı
    if _k:
        user_role = _k.get("rol", user_role)
        user_name = _k.get("ad_soyad") or _k.get("ad") or user_name
        if user_name:
            user_initials = "".join(w[0].upper() for w in user_name.split()[:2] if w)
    
    try:
        current_path = str(st.context.url)
    except Exception:
        current_path = ""

    active_page = _detect_active(current_path)
    initials    = user_initials or (user_name[:2].upper() if user_name else "SK")
    role_label  = {
        "admin":         "Admin",
        "broker":        "Broker",
        "danisan":       "Danışman",
        "ofis":          "Ofis",
        "yonetici":      "Yönetici",
        "gd":            "Gayrimenkul Danışmanı",
        "ofis_asistani": "Ofis Asistanı",
        "medya":         "Medya",
    }.get(user_role, user_role)

    # ── Streamlit sidebar içeriği ─────────────────────────────────────────────
    # Sidebar'ı her render'da expanded tut
    st.markdown(
        '<style>[data-testid="stSidebar"]{display:flex!important;}'
        '[data-testid="collapsedControl"]{display:none!important;}'
        '[data-testid="stSidebarHeader"]{'
        'background:transparent!important;padding:0!important;height:0!important;'
        'min-height:0!important;}'
        '[data-testid="stSidebarCollapseButton"]{display:none!important;}'
        '</style>',
        unsafe_allow_html=True
    )
    with st.sidebar:
        # ── İmpersonate banner ────────────────────────────────────────────────
        if st.session_state.get("_impersonate_active"):
            _imp_k   = st.session_state.get("kullanici", {})
            _imp_ad  = _imp_k.get("ad_soyad") or _imp_k.get("ad", "?")
            st.markdown(
                f'<div style="background:#b91c1c;border-radius:6px;padding:7px 8px;'
                f'margin-bottom:8px;font-size:10px;color:#fff;line-height:1.5;">'
                f'👁 <b>{_imp_ad}</b> olarak<br>görüntülüyorsunuz</div>',
                unsafe_allow_html=True,
            )
            if st.button("↩ Oturumuma dön", key="_imp_geri", use_container_width=True):
                _orig = st.session_state.get("_impersonate_original", {})
                st.session_state["kullanici"]           = _orig
                st.session_state["user_role"]           = _orig.get("rol", "admin")
                _orig_ad = _orig.get("ad_soyad") or _orig.get("ad", "")
                st.session_state["user_name"]           = _orig_ad
                st.session_state["user_initials"]       = "".join(
                    w[0].upper() for w in _orig_ad.split()[:2] if w
                )
                st.session_state["_impersonate_active"] = False
                st.session_state.pop("_impersonate_original", None)
                st.rerun()

        # Brand + Kullanıcı alanı — transparan
        # Logo + avatar + kullanıcı bilgisi tek HTML bloğunda kalır.
        # Beyaz/açık kart zemini kaldırıldı.
        import os as _os
        import base64 as _b64

        _logo_path = _os.path.join(
            _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))),
            "assets", "zeta_logo_sidebar.png"
        )
        _logo_src = ""
        if _os.path.exists(_logo_path):
            with open(_logo_path, "rb") as _lf:
                _logo_src = f"data:image/png;base64,{_b64.b64encode(_lf.read()).decode('utf-8')}"

        _k = st.session_state.get("kullanici", {})
        _foto_bytes = _k.get("foto_bytes")
        _foto_path = _k.get("foto_path", "")
        _foto_url = _k.get("foto_url", "")

        _avatar_src = ""
        if _foto_bytes:
            _avatar_src = f"data:image/jpeg;base64,{_b64.b64encode(_foto_bytes).decode('utf-8')}"
        elif _foto_path and _os.path.exists(_foto_path):
            try:
                with open(_foto_path, "rb") as _f:
                    _avatar_src = f"data:image/jpeg;base64,{_b64.b64encode(_f.read()).decode('utf-8')}"
            except Exception:
                _avatar_src = ""
        elif _foto_url and _foto_url.startswith("http"):
            _avatar_src = _foto_url  # http URL doğrudan <img src> olarak kullanılabilir

        _avatar_html = (
            f'<img src="{_avatar_src}" style="width:52px;height:52px;border-radius:50%;'
            'object-fit:cover;object-position:center top;border:1px solid rgba(255,255,255,0.35);'
            'box-shadow:none;flex-shrink:0;">'
            if _avatar_src else
            f'<div style="width:52px;height:52px;border-radius:50%;background:#185FA5;'
            'display:flex;align-items:center;justify-content:center;font-size:15px;'
            f'font-weight:700;color:#fff;flex-shrink:0;">{initials}</div>'
        )

        st.markdown(
            f'<div style="padding:12px 8px 10px 8px;margin-bottom:2px;">'
            f'<div style="background:transparent;border-radius:0;padding:8px 4px;box-shadow:none;">'
            + (f'<div style="display:flex;justify-content:center;margin-bottom:12px;">'
               f'<img src="{_logo_src}" style="width:100%;max-width:118px;display:block;background:transparent;box-shadow:none;">'
               f'</div>' if _logo_src else '')
            + '<div style="height:0.5px;background:rgba(255,255,255,0.12);margin:0 0 12px 0;"></div>'
            + '<div style="display:flex;align-items:center;gap:10px;">'
            + _avatar_html
            + '<div>'
            + f'<div style="font-size:13px;font-weight:700;color:#ffffff;line-height:1.3;">{user_name or "Kullanıcı"}</div>'
            + f'<div style="font-size:10px;color:rgba(255,255,255,0.58);">{role_label}</div>'
            + '</div></div>'
            + '</div></div>',
            unsafe_allow_html=True,
        )

        if st.button("👤 Profilim", key="nav_profil_btn", use_container_width=True):
            st.switch_page("pages/profil.py")

        st.markdown(
            '<div style="height:0.5px;background:rgba(255,255,255,0.1);margin:8px 0 4px 0;"></div>',
            unsafe_allow_html=True)

        # Nav sections
        for s_idx, section in enumerate(_NAV_SECTIONS):
            visible = [
                (p, lbl, icon)
                for p, lbl, icon, izin in section["pages"]
                if _can_see(izin, user_role)
            ]
            if not visible:
                continue

            if s_idx > 0 and section["label"]:
                st.markdown(
                    '<div style="height:0.5px;background:rgba(255,255,255,0.07);'
                    'margin:6px 0;"></div>',
                    unsafe_allow_html=True
                )

            if section["label"]:
                st.markdown(
                    f'<div style="font-size:9px;font-weight:600;'
                    f'color:rgba(255,255,255,0.3);letter-spacing:0.12em;'
                    f'text-transform:uppercase;padding:8px 4px 3px;">'
                    f'{section["label"]}</div>',
                    unsafe_allow_html=True
                )

            for path, label, icon in visible:
                item_key = path.replace("pages/", "").replace(".py", "").replace("/", "_")
                is_active = (path == active_page)
                btn_label = f"▸  {icon}  {label}" if is_active else f"{icon}  {label}"
                if is_active:
                    st.markdown('<div class="sidebar-active-btn">', unsafe_allow_html=True)
                if st.button(btn_label, key=f"nav_{item_key}", use_container_width=True):
                    st.switch_page(path)
                if is_active:
                    st.markdown('</div>', unsafe_allow_html=True)

        # ── DEBUG CAPTION (kapalı — açmak için SHOW_DEBUG = True yap) ────────
        SHOW_DEBUG = False

        if SHOW_DEBUG:
            _dk = st.session_state.get("kullanici", {})
            _foto_dbg = _dk.get("foto_path") or "—"
            _foto_found = "✅" if (_dk.get("foto_path") and __import__("os").path.exists(_dk.get("foto_path", ""))) else "❌"

            # ROL STATE UYUMSUZLUĞU KONTROLÜ
            _sesli_rol = user_role
            _dict_rol = _dk.get("rol", "")
            _role_mismatch = _sesli_rol != _dict_rol

            st.markdown(
                f'<div style="font-size:9px;color:rgba(255,255,255,0.25);'
                f'padding:8px 4px 4px;line-height:1.6;word-break:break-all;">'
                f'🔑 {_dk.get("user_key","—")}<br>'
                f'🏷 kullanici.rol={_dict_rol}<br>'
                f'🏷 user_role={_sesli_rol}<br>'
                f'🏢 {_dk.get("ofis_id","—")}<br>'
                f'📷 foto {_foto_found}</div>',
                unsafe_allow_html=True,
            )

            if _role_mismatch:
                st.markdown(
                    f'<div style="font-size:10px;color:#ff4444;font-weight:600;'
                    f'padding:6px 4px;background:rgba(255,68,68,0.15);border-radius:4px;">'
                    f'⚠️ ROL STATE UYUMSUZ</div>',
                    unsafe_allow_html=True
                )

    # ── Global CSS — sidebar stilini override et ──────────────────────────────
    st.markdown("""
<style>
/* Streamlit sidebar arka planı */
[data-testid="stSidebar"] {
    background: #1E3A5F !important;
    min-width: 200px !important;
    max-width: 200px !important;
    display: flex !important;
    visibility: visible !important;
    opacity: 1 !important;
}
[data-testid="stSidebar"][aria-expanded="false"] {
    min-width: 200px !important;
    max-width: 200px !important;
    transform: none !important;
}
[data-testid="stSidebar"] > div:first-child {
    background: #1E3A5F !important;
    padding: 0 8px !important;
}
[data-testid="collapsedControl"] {
    display: none !important;
}
[data-testid="stHeader"] {
    display: none !important;
}
[data-testid="stAppViewContainer"] > .main > .block-container {
    padding-top: 1rem !important;
    max-width: 100% !important;
}

/* Sidebar buton stilleri — en yüksek specificity */
#root [data-testid="stSidebar"] button,
#root [data-testid="stSidebar"] [data-testid="stButton"] > button {
    background: transparent !important;
    background-color: transparent !important;
    border: none !important;
    border-left: 2px solid transparent !important;
    border-radius: 6px !important;
    color: rgba(255,255,255,0.75) !important;
    font-size: 12px !important;
    font-weight: 400 !important;
    text-align: left !important;
    padding: 6px 8px !important;
    width: 100% !important;
    min-height: 32px !important;
    box-shadow: none !important;
    justify-content: flex-start !important;
}
#root [data-testid="stSidebar"] button > div,
#root [data-testid="stSidebar"] button p,
#root [data-testid="stSidebar"] [data-testid="stButton"] > button p,
#root [data-testid="stSidebar"] [data-testid="stButton"] > button > div {
    color: rgba(255,255,255,0.75) !important;
    font-size: 12px !important;
    font-weight: 400 !important;
    text-align: left !important;
}
#root [data-testid="stSidebar"] button:hover,
#root [data-testid="stSidebar"] [data-testid="stButton"] > button:hover {
    background: rgba(255,255,255,0.08) !important;
    color: rgba(255,255,255,0.95) !important;
}
#root [data-testid="stSidebar"] button:hover p,
#root [data-testid="stSidebar"] [data-testid="stButton"] > button:hover p,
#root [data-testid="stSidebar"] [data-testid="stButton"] > button:hover > div {
    color: rgba(255,255,255,0.95) !important;
}

/* Aktif sayfa butonu */
#root [data-testid="stSidebar"] .sidebar-active-btn > button,
#root [data-testid="stSidebar"] .sidebar-active-btn button {
    background: rgba(255,255,255,0.12) !important;
    border-left: 2px solid #5BA3D9 !important;
    color: #ffffff !important;
    font-weight: 600 !important;
}
#root [data-testid="stSidebar"] .sidebar-active-btn > button p,
#root [data-testid="stSidebar"] .sidebar-active-btn button p,
#root [data-testid="stSidebar"] .sidebar-active-btn > button > div {
    color: #ffffff !important;
    font-weight: 600 !important;
}

/* Sidebar scrollbar */
[data-testid="stSidebar"] ::-webkit-scrollbar { width: 3px; }
[data-testid="stSidebar"] ::-webkit-scrollbar-thumb {
    background: rgba(255,255,255,0.1); border-radius: 2px;
}
</style>
""", unsafe_allow_html=True)


def render_page_header(title: str, subtitle: str = ""):
    """Sayfa başlığı."""
    sub_html = f'<div style="font-size:12px;color:#64748B;margin-top:2px;">{subtitle}</div>' if subtitle else ""
    st.markdown(
        f'<div style="padding:0 0 12px;border-bottom:0.5px solid #e2e8f0;margin-bottom:16px;">'
        f'<div style="font-size:20px;font-weight:600;color:#1E293B;letter-spacing:-0.03em;">'
        f'{title}</div>{sub_html}</div>',
        unsafe_allow_html=True,
    )
