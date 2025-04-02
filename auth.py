import streamlit as st

def init_auth():
    if 'user_email' not in st.session_state:
        st.session_state.user_email = None

def authenticate():
    # Configure OAuth provider
    oauth = {
        "client_id": st.secrets["MICROSOFT_CLIENT_ID"],
        "client_secret": st.secrets["MICROSOFT_CLIENT_SECRET"],
        "authorize_url": f"https://login.microsoftonline.com/{st.secrets['MICROSOFT_TENANT_ID']}/oauth2/v2.0/authorize",
        "token_url": f"https://login.microsoftonline.com/{st.secrets['MICROSOFT_TENANT_ID']}/oauth2/v2.0/token",
        "redirect_uri": st.secrets["MICROSOFT_REDIRECT_URI"],
        "client_type": "confidential"
    }
    
    user = st.login_button(
        "Login with Microsoft",
        key="microsoft_login",
        type="azure",
        oauth=oauth
    )
    if user:
        st.session_state.user_email = user.email
    return user

def is_authorized():
    return (st.session_state.user_email and 
            st.session_state.user_email == st.secrets["ALLOWED_EMAIL"])
