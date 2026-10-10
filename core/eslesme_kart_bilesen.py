"""
core/eslesme_kart_bilesen.py

Eşleşme sekmesi için gruplu kart listesi bileşeni (10.10.2026).
components/eslesme_kartlar/index.html tek dosyadır, derleme gerektirmez.
Her grup: bir kaynak kayıt (başlık) + altında uygun adaylar; başlığa
tıklayınca kayıt, uygulamadaki orijinal kart görünümüyle (Shadow DOM içinde,
kendi CSS'iyle) açılır. Python'a veri dönmez.
"""
import os
import streamlit.components.v1 as components

_YOL = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "components", "eslesme_kartlar",
)
_bilesen = components.declare_component("eslesme_kartlar", path=_YOL)


def eslesme_kartlari(gruplar, css, imza, key="eslesme_kartlar"):
    """gruplar: [{'kaynak': {baslik, chips[], link, kart{css,html}},
                  'adaylar': [{oran, guclu, baslik, gerekce, kaynak, link, meta, kart{css,html}}]}]
    css: {'talep': '...', 'pazar': '...'} — orijinal kart stilleri (bir kez gönderilir).
    imza: içerik değiştiğinde değişen kısa metin (bileşenin yeniden çizmesi için)."""
    return _bilesen(gruplar=gruplar, css=css, imza=imza, key=key, default=None)
