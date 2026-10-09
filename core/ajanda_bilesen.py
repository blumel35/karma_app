"""
core/ajanda_bilesen.py

Ajandam takvimi (hafta / ay / gün) — Python'a tıklama bildiren Streamlit
bileşeni (09.10.2026). components/ajanda_takvim/index.html tek dosyadır,
derleme gerektirmez. Hafta/ay gezinmesi iframe içinde yapılır (sayfa yeniden
çalışmaz); yalnızca "olay ekle" ve "olaya dokun" Python'a gider.
"""
import os
import streamlit.components.v1 as components

_YOL = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "components", "ajanda_takvim",
)
_bilesen = components.declare_component("ajanda_takvim", path=_YOL)


def ajanda_takvimi(olaylar, bugun, simdi, gorunum0="hafta", tarih0=None, git=None,
                   key="ajanda_takvim"):
    """olaylar: core.ajanda.takvim_olaylari() çıktısı. bugun: 'YYYY-MM-DD',
    simdi: 'YYYY-MM-DDTHH:MM' (Türkiye saati). git: {'t': tarih, 'n': sayı} —
    n değişince takvim o tarihe gider. Döner: {k, id|t, v, d, n} ya da None."""
    return _bilesen(
        olaylar=olaylar, bugun=bugun, simdi=simdi, gorunum0=gorunum0,
        tarih0=tarih0 or bugun, git=git, key=key, default=None,
    )
