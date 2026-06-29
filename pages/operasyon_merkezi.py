import streamlit as st
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.ui_helpers import render_navbar

render_navbar(
    user_role=st.session_state.get("user_role", "danisan"),
    user_name=st.session_state.get("user_name", ""),
    user_initials=st.session_state.get("user_initials", ""),
)

st.markdown("""
# Operasyon Merkezi

Bu modül sonraki adımda aktif hale getirilecektir.

- Operasyon hattı kontrolü
- Görev akışı
- Ofis içi işlem takibi

Geri dönmek için sol menü veya ana sayfadaki `Operasyon Merkezi` kartını kullanabilirsiniz.
""",
    unsafe_allow_html=True,
)
