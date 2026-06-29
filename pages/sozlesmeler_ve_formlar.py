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
# Sözleşmeler ve Formlar

Bu modül sonraki adımda aktif hale getirilecektir.

- Sözleşme yönetimi
- Form ve belge takipleri
- Onay akışları

Ana sayfadan `Sözleşmeler ve Formlar` kartına tıklayarak bu placeholder sayfaya ulaşabilirsiniz.
""",
    unsafe_allow_html=True,
)
