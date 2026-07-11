from pathlib import Path

p = Path(r'pages/2_Talep_Tablosu.py')
text = p.read_text(encoding='utf-8')
replacements = [
    (
        "f'<div style=\"padding:6px 12px;border-radius:0 6px 6px 0;margin-bottom:10px;\'>'",
        "f'<div style=\"padding:5px 12px;border-radius:0 6px 6px 0;margin-bottom:8px;\'>'"
    ),
    (
        "f'<div style=\"font-size:0.95rem;font-weight:800;color:#172B4D;line-height:1.3;\">{ui[\"baslik\"]}</div>'",
        "f'<div style=\"font-size:0.88rem;font-weight:800;color:#172B4D;line-height:1.25;\">{ui[\"baslik\"]}</div>'"
    ),
    (
        "return (\n            f'<span style=\"display:inline-flex;flex-direction:column;\'\n            f'background:{bg};border:1px solid {border};border-radius:8px;\'\n            f'padding:4px 10px;margin-right:6px;margin-bottom:4px;\'\n            f'<span style=\"font-size:9px;font-weight:700;color:#94a3b8;text-transform:uppercase;letter-spacing:0.06em;\">{label}</span>'\n            f'<span style=\"font-size:12px;font-weight:700;color:{color};margin-top:1px;\">{value}</span>'\n            f'</span>'\n        )\n",
        "return (\n            f'<span style=\"display:inline-flex;flex-direction:column;justify-content:center;\'\n            f'background:{bg};border:1px solid {border};border-radius:8px;\'\n            f'padding:5px 10px;margin-right:6px;margin-bottom:6px;min-width:120px;\'\n            f'<span style=\"font-size:9px;font-weight:700;color:#94a3b8;text-transform:uppercase;letter-spacing:0.06em;\">{label}</span>'\n            f'<span style=\"font-size:12px;font-weight:700;color:{color};margin-top:2px;\">{value}</span>'\n            f'</span>'\n        )\n"
    ),
    (
        "chip_html = (\n        _chip(\"Danışman\", isim, color=\"#172B4D\")\n        + _chip(\"İlçe\", ilce_str, color=aks_r[\"text\"], bg=aks_r[\"bg\"], border=aks_r[\"bg\"])\n        + _chip(\"İşlem\", islem, color=\"#991b1b\" if \"atılık\" in islem else \"#166534\",\n                bg=\"#fef2f2\" if \"atılık\" in islem else \"#f0fdf4\",\n                border=\"#fca5a5\" if \"atılık\" in islem else \"#86efac\")\n        + _chip(\"Mülk\", mulk)\n        + _chip(\"Oda / M²\", oda, color=\"#172B4D\")\n        + _chip(\"Bütçe\", butce, color=\"#172B4D\", bg=\"#EEF4FA\", border=\"#D6E4F0\")\n    )\n    if ofis:\n        chip_html += _chip(\"Ofis\", ofis)\n\n    st.markdown(\n        f'<div style=\"display:flex;flex-wrap:wrap;align-items:flex-start;margin-bottom:8px;\'>\n        f'{chip_html}</div>',\n        unsafe_allow_html=True,\n    )\n",
        "row1 = _chip(\"Danışman\", isim, color=\"#172B4D\")\n    if ofis:\n        row1 += _chip(\"Ofis\", ofis)\n    row1 += _chip(\"İlçe\", ilce_str, color=aks_r[\"text\"], bg=aks_r[\"bg\"], border=aks_r[\"bg\"])\n\n    row2 = (\n        _chip(\"İşlem\", islem, color=\"#991b1b\" if \"atılık\" in islem else \"#166534\",\n              bg=\"#fef2f2\" if \"atalık\" in islem else \"#f0fdf4\",\n              border=\"#fca5a5\" if \"atalık\" in islem else \"#86efac\")\n        + _chip(\"Mülk\", mulk)\n        + _chip(\"Oda / M²\", oda, color=\"#172B4D\")\n        + _chip(\"Bütçe\", butce, color=\"#172B4D\", bg=\"#EEF4FA\", border=\"#D6E4F0\")\n    )\n\n    st.markdown(\n        f'<div style=\"display:flex;flex-wrap:wrap;gap:6px 8px;margin-bottom:8px;\">{row1}</div>'\n        f'<div style=\"display:flex;flex-wrap:wrap;gap:6px 8px;margin-bottom:8px;\">{row2}</div>',\n        unsafe_allow_html=True,\n    )\n"
    )
]
for old, new in replacements:
    if old not in text:
        print('MISSING:', repr(old[:120]))
        raise SystemExit(1)
    text = text.replace(old, new)
p.write_text(text, encoding='utf-8')
print('PATCH APPLIED')
