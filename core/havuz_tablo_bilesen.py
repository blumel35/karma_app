"""
core/havuz_tablo_bilesen.py

Bölge Havuzu tablosu — Excel tarzı başlık filtreleri (▾ ile değer listesi),
sıralama ve satır onay kutuları olan Streamlit bileşeni (09.10.2026).
components/havuz_tablo/index.html tek dosyadır, derleme gerektirmez.
Filtre/sıralama iframe içinde çalışır (sayfa yeniden çalışmaz); yalnızca
seçim (onay kutuları) ve aktif satır Python'a gider.
"""
import os
import streamlit.components.v1 as components

_YOL = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "components", "havuz_tablo",
)
_bilesen = components.declare_component("havuz_tablo", path=_YOL)


def havuz_tablosu(kolonlar, satirlar, secili0=None, aktif0=None, key="havuz_tablo"):
    """kolonlar: [{'k': anahtar, 'label': başlık, 'w': px, 'sk': True(zaman gibi
    sayısal sıralı sütun)}]. satirlar: [{'id', 'yeni', 't' (sıralama sayısı),
    'h': {anahtar: metin}}]. Döner: {'sec': [id...], 'aktif': id|None, 'n'} ya da None."""
    return _bilesen(
        kolonlar=kolonlar, satirlar=satirlar, secili0=secili0 or [],
        aktif0=aktif0, key=key, default=None,
    )
