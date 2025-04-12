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
        show_user_info()
        if st.sidebar.button("Log out"):
            st.logout()
    return user

def is_authorized():
    return (st.session_state.user_email and 
            st.session_state.user_email == st.secrets["ALLOWED_EMAIL"])

def get_initials(name: str) -> str:
    return name[0].upper() if name else '?'

def show_user_info():
    if st.experimental_user.is_logged_in:
        # Create avatar circle with user initials
        initials = get_initials(st.experimental_user.name)
        user_info = f"""
        **Email:** {st.experimental_user.email}
        **Name:** {st.experimental_user.name or 'N/A'}
        """
        
        # Style the avatar circle and position it in the sidebar
        st.sidebar.markdown(
            f"""
            <div style="display: flex; align-items: center; margin-bottom: 1rem;">
                <div title="{user_info}" style="
                    background-color: #3498db;
                    color: white;
                    border-radius: 50%;
                    width: 40px;
                    height: 40px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-weight: bold;
                    margin-right: 10px;
                    cursor: help;
                ">{initials}</div>
                <div style="cursor: help;" title="{user_info}">Logged in ✓</div>
            </div>
            """,
            unsafe_allow_html=True
        )
        st.sidebar.divider()
