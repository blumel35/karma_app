from supabase import create_client
import streamlit as st


@st.cache_resource(show_spinner=False)
def get_client():
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["secret_key"]
    return create_client(url, key)
