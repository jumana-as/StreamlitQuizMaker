import streamlit as st
from msal import ConfidentialClientApplication
import requests

def init_auth():
    if "access_token" not in st.session_state:
        st.session_state.access_token = None
    if "user_email" not in st.session_state:
        st.session_state.user_email = None

def get_auth_url():
    msal_app = ConfidentialClientApplication(
        st.secrets["MICROSOFT_CLIENT_ID"],
        client_credential=st.secrets["MICROSOFT_CLIENT_SECRET"],
        authority=f"https://login.microsoftonline.com/{st.secrets['MICROSOFT_TENANT_ID']}"
    )
    
    return msal_app.get_authorization_request_url(
        scopes=["User.Read"],
        redirect_uri=st.secrets["MICROSOFT_REDIRECT_URI"]
    )

def handle_auth_callback():
    if "code" in st.experimental_get_query_params():
        code = st.experimental_get_query_params()["code"][0]
        msal_app = ConfidentialClientApplication(
            st.secrets["MICROSOFT_CLIENT_ID"],
            client_credential=st.secrets["MICROSOFT_CLIENT_SECRET"],
            authority=f"https://login.microsoftonline.com/{st.secrets['MICROSOFT_TENANT_ID']}"
        )
        
        token_response = msal_app.acquire_token_by_authorization_code(
            code,
            scopes=["User.Read"],
            redirect_uri=st.secrets["MICROSOFT_REDIRECT_URI"]
        )
        
        if "access_token" in token_response:
            st.session_state.access_token = token_response["access_token"]
            user_info = requests.get(
                "https://graph.microsoft.com/v1.0/me",
                headers={"Authorization": f"Bearer {st.session_state.access_token}"}
            ).json()
            st.session_state.user_email = user_info.get("mail")

def is_authorized():
    return (st.session_state.user_email and 
            st.session_state.user_email == st.secrets["ALLOWED_EMAIL"])
