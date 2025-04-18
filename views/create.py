import streamlit as st
import json
from database import save_exam

def create_exam():
    st.header("Create New Exam")
    uploaded_file = st.file_uploader("Upload JSON file", type="json")
    if uploaded_file:
        exam_data = json.load(uploaded_file)
        uploaded_questions = len(exam_data)
        st.info(f"Uploaded file contains {uploaded_questions} questions")
        
        session_time = st.number_input("Session Time (minutes)", min_value=1, value=60)
        total_questions = st.number_input("Total Questions", min_value=1, value=uploaded_questions)
        questions_per_session = st.number_input("Questions Per Session", min_value=1, 
                                              max_value=uploaded_questions, value=10)
        
        if st.button("Save Exam"):
            save_exam(exam_data, session_time, total_questions, uploaded_questions, questions_per_session)
            st.success("Exam saved successfully!")
