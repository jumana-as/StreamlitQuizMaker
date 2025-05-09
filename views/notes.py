import streamlit as st
from database import get_all_user_notes

def show_notes():
    st.header("My Notes")
    
    notes = get_all_user_notes(st.session_state.user_email)
    if not notes:
        st.info("No notes found")
        return
    
    # Group notes by exam
    notes_by_exam = {}
    for note in notes:
        key = (note["exam"], note["provider"])
        if key not in notes_by_exam:
            notes_by_exam[key] = []
        notes_by_exam[key].append(note)
    
    # Display notes grouped by exam
    for (exam_name, provider), exam_notes in notes_by_exam.items():
        with st.expander(f"{exam_name} ({provider})", expanded=True):
            for note in sorted(exam_notes, key=lambda x: x["questionNumber"]):
                st.markdown(f"**Question {note['questionNumber']}**")
                st.markdown(note["text"])
                st.divider()
