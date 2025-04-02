import streamlit as st
from msal import ConfidentialClientApplication
import requests

def init_auth():
    if "access_token" not in st.session_state:
        st.session_state.access_token = None
    if "user_email" not in st.session_state:
        st.session_state.user_email = None

def get_auth_url():
    app = ConfidentialClientApplication(
        st.secrets["MICROSOFT_CLIENT_ID"],
        client_credential=st.secrets["MICROSOFT_CLIENT_SECRET"],
        authority=f"https://login.microsoftonline.com/{st.secrets['MICROSOFT_TENANT_ID']}"
    )
    
    return app.get_authorization_request_url(
        scopes=["https://graph.microsoft.com/User.Read"],
        redirect_uri=st.secrets["MICROSOFT_REDIRECT_URI"],
        state=st.session_state._session_id  # Add state parameter for security
    )

def handle_auth_callback():
    if "code" in st.query_params:
        app = ConfidentialClientApplication(
            st.secrets["MICROSOFT_CLIENT_ID"],
            client_credential=st.secrets["MICROSOFT_CLIENT_SECRET"],
            authority=f"https://login.microsoftonline.com/{st.secrets['MICROSOFT_TENANT_ID']}"
        )
        
        try:
            token_response = app.acquire_token_by_authorization_code(
                st.query_params["code"],
                scopes=["https://graph.microsoft.com/User.Read"],
                redirect_uri=st.secrets["MICROSOFT_REDIRECT_URI"]
            )
            
            if "access_token" in token_response:
                st.session_state.access_token = token_response["access_token"]
                try:
                    user_info = requests.get(
                        "https://graph.microsoft.com/v1.0/me",
                        headers={"Authorization": f"Bearer {st.session_state.access_token}"}
                    ).json()
                    if "error" in user_info:
                        st.error(f"Graph API error: {user_info['error']['message']}")
                        st.error(f"Full response: {user_info}")
                        return
                    st.session_state.user_email = user_info.get("mail") or user_info.get("userPrincipalName")
                except Exception as e:
                    st.error(f"Graph API request failed: {str(e)}")
            else:
                st.error(f"Token error: {token_response.get('error_description', 'Unknown error')}")
                st.error(f"Full response: {token_response}")
        except Exception as e:
            st.error(f"Authentication error: {str(e)}")

def is_authorized():
    return (st.session_state.user_email and 
            st.session_state.user_email == st.secrets["ALLOWED_EMAIL"])
