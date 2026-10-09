"""
core/fsbo_kart_bilesen.py

FSBO kartlarını, her kartın içinde 'Revy'den kopyaladığın numarayı yapıştır'
kutusu olan, Python'a geri değer döndürebilen bir Streamlit bileşeni olarak
gösterir (09.10.2026 — Meltem: "ilan linkinin içine girip kopyaladığım
telefonu ekrana yapıştırmak istiyorum ve bu telefon rehbere otomatik kayıt
olsun").

Derleme gerektirmez: components/fsbo_kart/index.html tek dosyadır.
st.components.v1.html sadece tek yönlüdür; kart içindeki yapıştırma olayını
Python'a taşıyabilmek için declare_component kullanılıyor.
"""
import os
import streamlit.components.v1 as components

_YOL = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "components", "fsbo_kart",
)
_bilesen = components.declare_component("fsbo_kart", path=_YOL)


def fsbo_kartlari(html, anahtar, kayitli=None, sonuc=None, key="fsbo_kartlar"):
    """html: tam kart sayfası (telefon_kutusu=True ile üretilmiş).
    anahtar: liste/filtre değişince değişen kısa metin — aynı kaldıkça iframe
    yeniden yüklenmez (kaydırma konumu korunur).
    kayitli: {ilan_linki: telefon} — zaten Rehberim'de olanlar.
    sonuc: son kayıt denemesinin sonucu {link, ok, mesaj}.
    Döner: {link, tel, n} (yeni bir yapıştırma olduysa) ya da None."""
    return _bilesen(
        html=html, anahtar=anahtar, kayitli=kayitli or {}, sonuc=sonuc,
        key=key, default=None,
    )
