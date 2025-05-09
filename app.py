import streamlit as st
from auth import init_auth, authenticate, is_authorized
from views.practice import practice_exam
from views.edit import edit_exam
from views.history import show_history
from views.create import create_exam
from views.notes import show_notes

st.set_page_config(page_title="", layout="wide")

def init_session_state():
    if "current_question" not in st.session_state:
        st.session_state.current_question = 0
    if "exam_data" not in st.session_state:
        st.session_state.exam_data = None
    if "start_time" not in st.session_state:
        st.session_state.start_time = None
    if "editing_question" not in st.session_state:
        st.session_state.editing_question = 0

def main():
    init_auth()
    init_session_state()

    # Define available modes
    modes = ["Practice", "Create", "Edit", "History", "Notes"]

    user = authenticate()
    if not user:
        st.error("Please login with Microsoft Account")
        return

    if not is_authorized():
        st.error("Unauthorized access")
        return
    
    st.title("")
    
    # Initialize mode in session state if not exists
    if "mode" not in st.session_state:
        st.session_state.mode = "Practice"
    
    # Add custom CSS for horizontal radio buttons
    st.sidebar.markdown("""
        <style>
            div[data-testid="stHorizontalBlock"] {
                gap: 0 !important;
            }
            div[data-testid="stMarkdown"] div.row-widget.stRadio > div {
                flex-direction: row;
                gap: 0.5rem;
            }
            div[data-testid="stMarkdown"] div.row-widget.stRadio > div[role="radiogroup"] > label {
                padding: 0.2rem 0.5rem;
                min-width: fit-content;
                font-size: 14px;
            }
        </style>
    """, unsafe_allow_html=True)
    
    # Remove direct assignment to session_state and use radio value directly
    mode = st.sidebar.radio(
        "",  # Empty label since we have the header above
        modes,
        horizontal=True,
        label_visibility="collapsed",
        index=modes.index(st.session_state.mode)
    )
    
    st.sidebar.divider()
    
    # Use mode value directly instead of session_state
    if mode == "Create":
        create_exam()
        st.session_state.mode = mode  # Update session state after rendering
    elif mode == "Edit":
        edit_exam()
        st.session_state.mode = mode
    elif mode == "History":
        show_history()
        st.session_state.mode = mode
    elif mode == "Notes":
        show_notes()
        st.session_state.mode = mode
    else:
        practice_exam()
        st.session_state.mode = mode

if __name__ == "__main__":
    main()
