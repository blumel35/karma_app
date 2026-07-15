import streamlit as st
import sys as _sys, os as _os
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
from core.ui_helpers import render_navbar, render_page_header


from core.auth import oturum_kontrol

if not oturum_kontrol():
    st.switch_page("pages/giris.py")

render_navbar(
    user_role=st.session_state.get("user_role", "danisan"),
    user_name=st.session_state.get("user_name", ""),
    user_initials=st.session_state.get("user_initials", ""),
)
st.title("Eşleştirme Motoru")
st.markdown("---")
st.info("🚧 Alıcı talepleri ile portföyleri otomatik eşleştirir. Yapım aşamasındadır.")
