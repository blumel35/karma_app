import streamlit as st


def get_panel_links(panel):
    if panel == "d":
        return [
            ("pages/ana_sayfa.py", "Ana Sayfa"),
            ("pages/2_Talep_Tablosu.py", "Alıcı Talepleri"),
            ("pages/3_Portfoy_Tablosu.py", "Portföyler"),
            ("pages/5_Zeta_Radar.py", "Zeta Radar"),
            ("pages/fsbo.py", "FSBO"),
            ("pages/eslestirme_motoru.py", "Eşleştirme"),
            ("pages/musteri_yonetimi.py", "Müşteri"),
            ("pages/10_Sunum_Merkezi.py", "Sunum Merkezi"),
            ("pages/4_AI_Asistan.py", "Yapay Zeka"),
        ]
    elif panel == "o":
        return [
            ("pages/ana_sayfa.py", "Ana Sayfa"),
            ("pages/4_Ofis_Paneli.py", "Zeta Ofis Paneli"),
            ("pages/operasyon_paneli.py", "Operasyon"),
        ]
    else:
        return [
            ("pages/ana_sayfa.py", "Ana Sayfa"),
            ("pages/5_Mail_Islem.py", "Mail İşlem"),
            ("pages/6_Veri_Temizle.py", "Veri Temizle"),
            ("pages/ilan_senkron.py", "Ilan Sync"),
            ("pages/proje_hafizasi_app_v2.py", "Proje"),
        ]


def render_page_title_selector(title, current_page_path=None, panel="d"):
    links = get_panel_links(panel)
    if current_page_path is None:
        current_path = ""
        try:
            current_path = str(st.context.url)
        except Exception:
            current_path = ""
        current_page_path = next((path for path, label in links if path in current_path), None)
    available_paths = [path for path, label in links]
    if current_page_path not in available_paths:
        current_page_path = links[0][0]
    active_index = next((idx for idx, (path, label) in enumerate(links) if path == current_page_path), 0)
    page_key = f"page_title_selector_{panel}"
    cols = st.columns([0.22, 0.04, 0.74])
    with cols[0]:
        st.markdown(f'<div class="page-title-heading">{title}</div>', unsafe_allow_html=True)
    with cols[1]:
        if hasattr(st, "popover"):
            with st.popover("▾"):
                for idx, (path, label) in enumerate(links):
                    if st.button(label, key=f"{page_key}_btn_{idx}", use_container_width=True):
                        st.switch_page(path)
        else:
            with st.container():
                selected_page = st.selectbox(
                    "", options=links, format_func=lambda x: x[1],
                    index=active_index, key=page_key, label_visibility="collapsed",
                )
            if selected_page[0] != current_page_path:
                st.switch_page(selected_page[0])
    with cols[2]:
        st.write("")


def render_navbar_legacy():
    """Eski üst navbar — henüz güncellenmemiş sayfalar için."""
    pass


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
            ("pages/taleplerim.py", "Taleplerim", "👤", []),
            ("pages/portfoylerím.py", "Portföylerim", "🏡", []),
            ("pages/Sunum_Merkezi_V2_Demo.py", "Sunum Merkezi", "✨", []),
            ("pages/ajandam.py", "Ajandam", "🗓", []),
        ],
    },
    {
        "key": "havuz",
        "label": "Ortak Havuzlar",
        "pages": [
            ("pages/2_Talep_Tablosu.py", "Talep Merkezi", "🗂", []),
            ("pages/3_Portfoy_Tablosu.py", "Portföy Merkezi", "🏠", []),
            ("pages/2_Talep_Arsiv.py", "Arşiv Merkezi", "📦", []),
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
        ],
    },
    {
        "key": "yonetim_araclari",
        "label": "Yönetici / Eski Ekranlar",
        "pages": [
            ("pages/5_Mail_Islem.py", "Mail İşlem", "📨", []),
            ("pages/proje_hafizasi_app_v2.py", "Proje Hafızası", "📌", []),
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
        '[data-testid="collapsedControl"]{display:none!important;}</style>',
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

        # Brand
        import os as _os
        _logo_path = _os.path.join(
            _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))),
            "assets", "zeta_logo_sidebar.png"
        )
        if _os.path.exists(_logo_path):
            st.markdown(
                '<div style="padding:10px 8px 8px 8px;'
                'border-bottom:0.5px solid rgba(255,255,255,0.08);'
                'margin-bottom:6px;">',
                unsafe_allow_html=True
            )
            st.image(_logo_path, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.markdown("""
<div style="padding:14px 4px 12px;border-bottom:0.5px solid rgba(255,255,255,0.08);
            display:flex;align-items:center;gap:9px;margin-bottom:6px;">
  <div style="width:30px;min-width:30px;height:30px;background:rgba(255,255,255,0.12);
              border:0.5px solid rgba(255,255,255,0.2);border-radius:7px;
              display:flex;align-items:center;justify-content:center;
              font-size:13px;font-weight:600;color:#fff;">Z</div>
  <div>
    <div style="font-size:9px;color:rgba(255,255,255,0.38);letter-spacing:0.12em;
                text-transform:uppercase;">Startkey</div>
    <div style="font-size:14px;font-weight:600;color:#fff;letter-spacing:-0.03em;">
                Zeta Panel</div>
  </div>
</div>""", unsafe_allow_html=True)

        # ── Kullanıcı kartı — brand'ın hemen altı ───────────────────────────
        _k = st.session_state.get("kullanici", {})
        _foto_bytes = _k.get("foto_bytes")
        _foto_path  = _k.get("foto_path", "")
        _foto_url   = _k.get("foto_url", "")

        def _render_circle_avatar(raw_bytes, size=56):
            """bytes → yuvarlak PIL image → st.image"""
            import io as _io
            from PIL import Image as _PImg, ImageDraw as _PDraw
            try:
                _img = _PImg.open(_io.BytesIO(raw_bytes)).convert("RGBA")
                # Boy fotoğraf: üst kare al
                _w, _h = _img.size
                if _h > _w * 1.1:
                    _img = _img.crop((0, 0, _w, _w))
                # Kareye çevir (ortadan)
                _w2, _h2 = _img.size
                if _w2 != _h2:
                    _mn = min(_w2, _h2)
                    _img = _img.crop(
                        ((_w2 - _mn) // 2, 0, (_w2 - _mn) // 2 + _mn, _mn)
                    )
                _img = _img.resize((size * 2, size * 2), _PImg.LANCZOS)
                _mask = _PImg.new("L", (size * 2, size * 2), 0)
                _PDraw.Draw(_mask).ellipse((0, 0, size * 2, size * 2), fill=255)
                _img.putalpha(_mask)
                _img = _img.resize((size, size), _PImg.LANCZOS)
                st.image(_img, width=size)
                return True
            except Exception:
                return False

        _col_av, _col_info = st.columns([1, 2.4])
        with _col_av:
            _rendered = False

            # Öncelik 1: foto_bytes (Supabase'den indirilen)
            if _foto_bytes and not _rendered:
                _rendered = _render_circle_avatar(_foto_bytes)

            # Öncelik 2: foto_path (local Excel klasörü)
            if _foto_path and not _rendered:
                import os as _os
                if _os.path.exists(_foto_path):
                    try:
                        with open(_foto_path, "rb") as _f:
                            _raw = _f.read()
                        _rendered = _render_circle_avatar(_raw)
                    except Exception:
                        pass

            # Öncelik 3: foto_url (Supabase Storage URL)
            if _foto_url and _foto_url.startswith("http") and not _rendered:
                st.markdown(
                    f'<img src="{_foto_url}" width="56" '
                    'style="border-radius:50%;object-fit:cover;'
                    'border:2px solid rgba(255,255,255,0.25);">',
                    unsafe_allow_html=True)
                _rendered = True

            # Fallback: initials dairesi
            if not _rendered:
                st.markdown(
                    f'<div style="width:56px;height:56px;border-radius:50%;'
                    'background:#185FA5;display:flex;align-items:center;'
                    f'justify-content:center;font-size:16px;font-weight:700;color:#fff;">{initials}</div>',
                    unsafe_allow_html=True)
        with _col_info:
            st.markdown(
                f'<div style="font-size:12px;font-weight:600;color:rgba(255,255,255,0.92);' +
                f'padding-top:2px;line-height:1.3;">{user_name or "Kullanıcı"}</div>' +
                f'<div style="font-size:9px;color:rgba(255,255,255,0.4);margin-bottom:4px;">{role_label}</div>',
                unsafe_allow_html=True)
            if st.button("👤 Profilim", key="nav_profil_btn", use_container_width=False):
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

        # ── DEBUG CAPTION (geçici) ───────────────────────────────────────────
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
