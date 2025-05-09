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
    
    # Add exam filter
    exam_options = [(None, None)] + list(notes_by_exam.keys())
    selected_exam = st.selectbox(
        "Filter by Exam",
        options=exam_options,
        format_func=lambda x: "All Exams" if x[0] is None else f"{x[0]} ({x[1]})"
    )
    
    st.divider()
    
    # Display filtered notes
    if selected_exam[0] is None:
        # Show all notes
        for (exam_name, provider), exam_notes in notes_by_exam.items():
            st.subheader(f"{exam_name} ({provider})")
            for note in sorted(exam_notes, key=lambda x: x["questionNumber"]):
                st.markdown(f"**Question {note['questionNumber']}**")
                st.markdown(note["text"])
                st.divider()
    else:
        # Show notes for selected exam
        exam_notes = notes_by_exam[selected_exam]
        for note in sorted(exam_notes, key=lambda x: x["questionNumber"]):
            st.markdown(note["text"])
            st.divider()
