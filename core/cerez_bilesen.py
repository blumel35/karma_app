"""
core/cerez_bilesen.py

"Beni hatırla" çerezini tarayıcıda ONAYLI okuyan/yazan/silen küçük Streamlit bileşeni
(11.10.2026). Neden: streamlit-cookies-controller (a) "henüz cevap vermedi" ile
"çerez yok"u ayıramıyordu, (b) yazma/silme komutlarının tarayıcıya ulaştığına dair onay
vermiyordu — kod sabit süre (time.sleep) bekleyip umuyordu. Yavaş cihazda/ağda iframe
yüklenmeden sayfa değişiyor, çerez hiç yazılmıyor ya da yenilenen token kaydedilmiyordu.

Dönüş: işlem tamamlanana kadar None, sonra {'nonce', 'op', 'ok', 'value'}.
components/oturum_cerezi/index.html tek dosyadır, derleme gerektirmez.
"""
import os
import streamlit.components.v1 as components

_YOL = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "components", "oturum_cerezi",
)
_bilesen = components.declare_component("oturum_cerezi", path=_YOL)


def cerez_islem(op, ad, deger, sure_sn, nonce, key):
    """op: 'read' | 'write' | 'remove'. Aynı nonce ile tekrar çağırmak işlemi tekrarlamaz."""
    return _bilesen(op=op, ad=ad, deger=deger or "", sure=int(sure_sn), nonce=nonce, key=key, default=None)
