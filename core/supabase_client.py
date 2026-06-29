from supabase import create_client
import streamlit as st

def get_client():
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["secret_key"]
    return create_client(url, key)