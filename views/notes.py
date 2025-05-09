import streamlit as st
from database import get_all_user_notes

def show_notes():
    st.header("My Notes")
    
    notes = get_all_user_notes(st.session_state.user_email)
    if not notes:
        st.info("No notes found")
        return
    
    st.caption(f"Total notes: {len(notes)}")
    
    # Group notes by exam
    notes_by_exam = {}
    for note in notes:
        key = (note["exam"], note["provider"])
        if key not in notes_by_exam:
            notes_by_exam[key] = []
        notes_by_exam[key].append(note)
    
    # Add exam filter with None removed from options
    exam_options = [None] + list(notes_by_exam.keys())
    selected_exam = st.selectbox(
        "Select an exam to view notes",
        options=exam_options,
        format_func=lambda x: "Select an exam..." if x is None else f"{x[0]} ({x[1]})"
    )
    
    # Only show notes if an exam is selected
    if selected_exam:
        exam_notes = notes_by_exam[selected_exam]
        st.caption(f"Notes in this exam: {len(exam_notes)}")
        st.divider()
        for note in sorted(exam_notes, key=lambda x: x["questionNumber"]):
            st.markdown(f"**{note['questionNumber']}**")
            st.markdown(note["text"])
            st.divider()
