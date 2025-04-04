import streamlit as st

def init_auth():
    if 'user_email' not in st.session_state:
        st.session_state.user_email = None

def authenticate():
    user = None
    if not st.experimental_user.is_logged_in:
        if st.button("Login with Microsoft"):
            st.login("microsoft")
    else:
        user = st.experimental_user
        st.session_state.user_email = user.email
        if st.sidebar.button("Log out"):
            st.logout()
    return user

def is_authorized():
    return (st.session_state.user_email and 
            st.session_state.user_email == st.secrets["ALLOWED_EMAIL"])
