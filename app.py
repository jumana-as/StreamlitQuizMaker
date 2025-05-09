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
    
    # Add custom CSS for compact buttons
    st.sidebar.markdown("""
        <style>
            div[data-testid="column"] {
                padding: 0 !important;
                margin: 0 2px !important;
            }
            div[data-testid="stHorizontalBlock"] {
                gap: 0.2rem !important;
            }
            .stButton button {
                padding: 2px 8px !important;
            }
            .stButton button div[data-testid="stMarkdownContainer"] {
                font-size: 14px !important;
            }
        </style>
    """, unsafe_allow_html=True)
    
    # Create compact horizontal mode buttons
    st.sidebar.markdown("### Mode")
    mode_cols = st.sidebar.columns([1, 1, 1, 1, 1])
    modes = ["Practice", "Create", "Edit", "History", "Notes"]
    
    for i, mode in enumerate(modes):
        if mode_cols[i].button(
            mode,
            type="primary" if st.session_state.mode == mode else "secondary",
            use_container_width=True
        ):
            st.session_state.mode = mode
            st.rerun()
    
    st.sidebar.divider()
    
    if st.session_state.mode == "Create":
        create_exam()
    elif st.session_state.mode == "Edit":
        edit_exam()
    elif st.session_state.mode == "History":
        show_history()
    elif st.session_state.mode == "Notes":
        show_notes()
    else:
        practice_exam()

if __name__ == "__main__":
    main()
