import streamlit as st
from database import (get_exam_list, get_exam, update_exam_metadata, 
                     update_single_question, save_note, get_note)
from .components import show_question_comments

def edit_exam():
    question_nav = st.sidebar.container()
    
    exams = get_exam_list()
    if not exams:
        st.warning("No exams available")
        return
    
    # Calculate and show verification progress
    selected_exam = st.selectbox(
        "Select Exam to Edit",
        options=[None] + [(e["exam"], e["provider"]) for e in exams],
        format_func=lambda x: "Select an exam..." if x is None else f"{x[0]} - {x[1]}"
    )

    if selected_exam:
        exam = get_exam(selected_exam[0], selected_exam[1])
        
        # Add verification progress stats
        total_questions = len(exam["questions"])
        verified_questions = sum(1 for q in exam["questions"] if q.get("verifiedAnswer"))
        marked_questions = sum(1 for q in exam["questions"] if q.get("isMarked", False))
        progress_percentage = (verified_questions / total_questions) * 100

        # Display metrics in three columns
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Verified ✅", f"{verified_questions}/{total_questions}")
        with col2:
            st.metric("Progress", f"{progress_percentage:.1f}%")
        with col3:
            st.metric("Marked 🚩", f"{marked_questions}")
        
        st.progress(progress_percentage / 100)
        st.divider()
        
        st.button("🔄 Refresh Cache", on_click=get_exam.clear)
        
        with st.expander("Edit Exam Settings", expanded=False):
            st.subheader("Metadata")
            meta = exam["metadata"]
            
            if meta.get("hasMissingQuestions", False):
                st.info(f"Missing Questions: {', '.join(map(str, meta['missingQuestions']))}")
            else:
                st.success("No missing questions")
            
            new_session_time = st.number_input("Session Time (minutes)", 
                                             min_value=1, 
                                             value=meta["sessionTime"])
            new_total_questions = st.number_input("Total Questions", 
                                                min_value=1, 
                                                value=meta["totalQuestions"])
            new_questions_per_session = st.number_input("Questions Per Session",
                                                      min_value=1,
                                                      max_value=meta["uploadedQuestions"],
                                                      value=meta["questionsPerSession"])
            
            metadata_modified = (
                new_session_time != meta["sessionTime"] or
                new_total_questions != meta["totalQuestions"] or
                new_questions_per_session != meta["questionsPerSession"]
            )
            
            if metadata_modified and st.button("Save Settings"):
                if update_exam_metadata(selected_exam[0], selected_exam[1],
                                      new_session_time, new_total_questions,
                                      new_questions_per_session):
                    st.success("Settings updated successfully!")
                    st.rerun()
                else:
                    st.error("Failed to update settings")

        st.subheader("")
        questions = sorted(exam["questions"], key=lambda q: q['questionNumber'])

        with question_nav:
            st.sidebar.markdown("""
                <style>
                    .question-nav { max-height: 400px; overflow-y: auto; padding: 10px; }
                    .nav-button { width: 100%; text-align: left; background: none; margin: 2px 0; }
                    .current { background-color: #e6f3ff !important; }
                </style>
            """, unsafe_allow_html=True)
            
            for i, q in enumerate(questions):
                icons = []
                if q.get("isMarked", False):
                    icons.append("🚩")
                if not q.get("verifiedAnswer"):
                    icons.append("⚠️")
                    
                icon_str = " ".join(icons)
                button_key = f"nav_{i}"
                
                button_label = f"{q['questionNumber']} {icon_str}"
                if i == st.session_state.editing_question:
                    button_label = f"**{button_label}**"
                
                if st.sidebar.button(button_label, key=button_key, use_container_width=False):
                    st.session_state.editing_question = i
                    st.rerun()

        question = questions[st.session_state.editing_question]
        st.markdown(f'<div id="{st.session_state.editing_question}"></div>', unsafe_allow_html=True)
        with st.container():
            st.markdown(f"### {question['questionNumber']}")
            st.write(question['questionText'])
            
            st.write("Options:")
            for opt in question["options"]:
                st.write(f"{opt['optionLetter']}. {opt['optionText']}")
            
            # Layout for inputs: (Verified Answer + Notes) | Mark for Review
            cols = st.columns([4, 1])
            with cols[0]:
                new_verified = st.text_input(
                    "Verified Answer", 
                    value=question.get("verifiedAnswer", ""),
                    key=f"verified_{question['questionNumber']}"
                )
            
            with cols[1]:
                is_marked = st.checkbox(
                    "Mark for Review",
                    value=question.get("isMarked", False),
                    key=f"edit_mark_{question['questionNumber']}"
                )
            
            with cols[0]:
                current_note = get_note(
                    st.session_state.user_email,
                    selected_exam[0],
                    selected_exam[1],
                    question["questionNumber"]
                )
                
                note_text = st.text_area(
                    "Notes",
                    value=current_note,
                    key=f"note_{question['questionNumber']}"
                )
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Save Answer"):
                        if update_single_question(
                            selected_exam[0],
                            selected_exam[1],
                            question["questionNumber"],
                            new_verified,
                            is_marked
                        ):
                            st.success("✓")
                        else:
                            st.error("Failed to save")
                
                with col2:
                    if st.button("Save Note"):
                        if save_note(
                            st.session_state.user_email,
                            selected_exam[0],
                            selected_exam[1],
                            question["questionNumber"],
                            note_text
                        ):
                            st.success("Note saved!")
                        else:
                            st.error("Failed to save note")
            
            with st.expander("Show Details"):
                show_question_comments(question)

        cols = st.columns(2)
        with cols[0]:
            if st.session_state.editing_question > 0:
                if st.button("← Previous"):
                    st.session_state.editing_question -= 1
                    st.rerun()
        with cols[1]:
            if st.session_state.editing_question < len(questions) - 1:
                if st.button("Next →"):
                    st.session_state.editing_question += 1
                    st.rerun()
