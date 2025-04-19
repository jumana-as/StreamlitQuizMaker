import streamlit as st
import math
from datetime import datetime, timedelta
from database import get_exam_list, get_exam, save_user_progress, get_user_exam_attempts
from .components import show_question_comments

def show_attempt_history(exam_name: str, provider: str):
    attempts = get_user_exam_attempts(st.session_state.user_email, exam_name, provider)
    
    if attempts:
        st.subheader("Previous Attempts")
        history_df = {
            "Date": [],
            "Batch": [],
            "Score": [],
            "Duration (minutes)": []
        }
        
        for attempt in attempts:
            history_df["Date"].append(attempt["completed_at"].strftime("%Y-%m-%d %H:%M"))
            history_df["Batch"].append(f"Batch {attempt.get('batch_number', '?')} ({attempt.get('batch_range', 'unknown')})")
            history_df["Score"].append(f"{attempt['score']:.2f}%")
            history_df["Duration (minutes)"].append(f"{attempt['duration_minutes']:.1f}")
        
        st.dataframe(history_df)
    else:
        st.info("No previous attempts for this exam")

def show_quiz():
    question = st.session_state.exam_data[st.session_state.current_question]
    
    # Show timer
    elapsed_time = datetime.now() - st.session_state.start_time
    remaining_time = timedelta(minutes=st.session_state.exam_metadata["sessionTime"]) - elapsed_time
    st.sidebar.metric("Time Remaining", str(remaining_time).split(".")[0])
    
    if remaining_time.total_seconds() <= 0:
        st.error("Time's up!")
        return

    st.subheader(f"{question['questionNumber']}")
    st.write(question["questionText"])
    
    selected_option = st.radio(
        "Select your answer:",
        options=[f"{opt['optionLetter']}. {opt['optionText']}" for opt in question["options"]],
        key=f"q_{question['questionNumber']}"
    )
    
    question["isMarked"] = st.checkbox("Mark for review", 
                                     key=f"mark_{question['questionNumber']}")
    
    question["userAnswer"] = selected_option.split(".")[0].strip()
    
    cols = st.columns(2)
    with cols[0]:
        if st.session_state.current_question > 0:
            if st.button("Previous"):
                st.session_state.current_question -= 1
                st.rerun()
                
    with cols[1]:
        if st.session_state.current_question < len(st.session_state.exam_data) - 1:
            if st.button("Next"):
                st.session_state.current_question += 1
                st.rerun()
        else:
            if st.button("Submit"):
                show_results()

    with st.expander("Show Details"):
        show_question_comments(question)

def show_results():
    attempt_answers = []
    for q in st.session_state.exam_data:
        user_answer = q["userAnswer"].upper()
        verified_answer = q["verifiedAnswer"].upper()
        attempt_answers.append({
            "questionNumber": q["questionNumber"],
            "verifiedAnswer": verified_answer,
            "userAnswer": user_answer,
            "correct": user_answer == verified_answer
        })

    correct_answers = sum(1 for a in attempt_answers if a["correct"])
    total_questions = len(attempt_answers)
    score = (correct_answers / total_questions) * 100
    
    end_time = datetime.now()
    duration = end_time - st.session_state.start_time
    duration_minutes = duration.total_seconds() / 60
    
    st.success(f"Final Score: {score:.2f}%")
    st.info(f"Time taken: {duration_minutes:.1f} minutes")
    
    save_user_progress(
        st.session_state.user_email,
        st.session_state.exam_data[0]["exam"],
        st.session_state.exam_data[0]["provider"],
        {
            "score": score,
            "completed_at": end_time,
            "duration_minutes": duration_minutes,
            "answers": attempt_answers,
            "batch_number": st.session_state.batch_info["number"],
            "batch_range": st.session_state.batch_info["range"]
        }
    )

def practice_exam():
    exams = get_exam_list()
    if not exams:
        st.warning("No exams available")
        return
        
    selected_exam = st.selectbox(
        "Select Exam",
        options=[None] + [(e["exam"], e["provider"]) for e in exams],
        format_func=lambda x: "Select an exam..." if x is None else f"{x[0]} - {x[1]}"
    )

    if selected_exam:
        show_attempt_history(selected_exam[0], selected_exam[1])
        exam = get_exam(selected_exam[0], selected_exam[1])
        
        if exam["metadata"].get("hasMissingQuestions", False):
            missing = exam["metadata"]["missingQuestions"]
            st.warning(f"⚠️ This exam has {len(missing)} missing questions: {missing}")
        
        # Add practice mode selector
        practice_mode = st.radio("Practice Mode", ["Batch", "Marked Questions"])
        
        if practice_mode == "Batch":
            total_questions = exam["metadata"]["uploadedQuestions"]
            questions_per_session = exam["metadata"]["questionsPerSession"]
            num_batches = math.ceil(total_questions / questions_per_session)
            
            batch_options = [f"Questions {i*questions_per_session + 1} - {min((i+1)*questions_per_session, total_questions)}" 
                            for i in range(num_batches)]
            selected_batch = st.radio("Select question batch:", batch_options)
            
            if st.button("Start New Attempt"):
                batch_idx = batch_options.index(selected_batch)
                start_idx = batch_idx * questions_per_session
                end_idx = min((batch_idx + 1) * questions_per_session, total_questions)
                
                questions = sorted(exam["questions"][start_idx:end_idx], 
                                key=lambda q: q['questionNumber'])
                st.session_state.batch_info = {
                    "number": batch_idx + 1,
                    "range": selected_batch
                }
                start_practice(questions, exam["metadata"])
        else:
            # Handle marked questions mode
            marked_questions = [q for q in exam["questions"] if q.get("isMarked", False)]
            if not marked_questions:
                st.warning("No marked questions found in this exam")
                return
                
            st.info(f"Found {len(marked_questions)} marked questions")
            if st.button("Start New Attempt"):
                st.session_state.batch_info = {
                    "number": 0,
                    "range": "Marked Questions"
                }
                start_practice(marked_questions, exam["metadata"])

    if st.session_state.exam_data:
        show_quiz()

def start_practice(questions: list, metadata: dict):
    """Helper function to start a new practice attempt"""
    st.session_state.exam_data = questions
    st.session_state.exam_metadata = metadata
    st.session_state.start_time = datetime.now()
    st.session_state.current_question = 0
