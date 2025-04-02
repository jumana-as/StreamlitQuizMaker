import streamlit as st
import json
import time
import math
from datetime import datetime, timedelta
from auth import init_auth, authenticate, is_authorized
from database import save_exam, get_exam_list, get_exam, save_user_progress, get_user_exam_attempts, update_exam_questions

st.set_page_config(page_title="Quiz Maker", layout="wide")

def init_session_state():
    if "current_question" not in st.session_state:
        st.session_state.current_question = 0
    if "exam_data" not in st.session_state:
        st.session_state.exam_data = None
    if "start_time" not in st.session_state:
        st.session_state.start_time = None

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

    st.title("Quiz Maker")
    
    mode = st.sidebar.radio("Mode", ["Practice Exam", "Create Exam", "Edit Exam"])
    
    if mode == "Create Exam":
        create_exam()
    elif mode == "Edit Exam":
        edit_exam()
    else:
        practice_exam()

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

def practice_exam():
    st.header("Practice Exam")
    
    exams = get_exam_list()
    if not exams:
        st.warning("No exams available")
        return
        
    selected_exam = st.selectbox(
        "Select Exam",
        options=[(e["exam"], e["provider"]) for e in exams],
        format_func=lambda x: f"{x[0]} - {x[1]}"
    )

    # Show attempt history
    if selected_exam:
        show_attempt_history(selected_exam[0], selected_exam[1])
        exam = get_exam(selected_exam[0], selected_exam[1])
        
        # Show missing questions warning if any
        if exam["metadata"].get("hasMissingQuestions", False):
            missing = exam["metadata"]["missingQuestions"]
            st.warning(f"⚠️ This exam has {len(missing)} missing questions: {missing}")
        
        # Calculate number of batches
        total_questions = exam["metadata"]["uploadedQuestions"]
        questions_per_session = exam["metadata"]["questionsPerSession"]
        num_batches = math.ceil(total_questions / questions_per_session)
        
        # Let user select batch
        batch_options = [f"Questions {i*questions_per_session + 1} - {min((i+1)*questions_per_session, total_questions)}" 
                        for i in range(num_batches)]
        selected_batch = st.radio("Select question batch:", batch_options)
        
        if st.button("Start New Attempt"):
            # Calculate batch index and slice questions
            batch_idx = batch_options.index(selected_batch)
            start_idx = batch_idx * questions_per_session
            end_idx = min((batch_idx + 1) * questions_per_session, total_questions)
            
            # Store selected questions and batch info for this attempt
            st.session_state.exam_data = exam["questions"][start_idx:end_idx]
            st.session_state.exam_metadata = exam["metadata"]
            st.session_state.batch_info = {
                "number": batch_idx + 1,
                "range": selected_batch
            }
            st.session_state.start_time = datetime.now()
            st.session_state.current_question = 0

    if st.session_state.exam_data:
        show_quiz()

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

    # Show question
    st.subheader(f"Question {question['questionNumber']}")
    st.write(question["questionText"])
    
    # Show options
    selected_option = st.radio(
        "Select your answer:",
        options=[opt["optionText"] for opt in question["options"]],
        key=f"q_{question['questionNumber']}"
    )
    
    # Mark for review
    question["isMarked"] = st.checkbox("Mark for review", 
                                     key=f"mark_{question['questionNumber']}")
    
    # Store user answer
    question["userAnswer"] = selected_option
    
    # Navigation buttons
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

    # Expandable details
    with st.expander("Show Details"):
        st.write("Comments:")
        for comment in question["comments"]:
            st.write(f"{comment['commentHead']}: {comment['commentContent']}")
        st.write(f"Suggested Answer: {question['suggestedAnswer']}")
        st.write("Vote Distribution:", question["voteDistribution"])
        st.write(f"Verified Answer: {question['verifiedAnswer']}")

def show_results():
    correct_answers = sum(
        1 for q in st.session_state.exam_data 
        if q["userAnswer"] == q["verifiedAnswer"]
    )
    total_questions = len(st.session_state.exam_data)
    score = (correct_answers / total_questions) * 100
    
    # Calculate duration
    end_time = datetime.now()
    duration = end_time - st.session_state.start_time
    duration_minutes = duration.total_seconds() / 60
    
    st.success(f"Final Score: {score:.2f}%")
    st.info(f"Time taken: {duration_minutes:.1f} minutes")
    
    # Save progress with duration and batch info
    save_user_progress(
        st.session_state.user_email,
        st.session_state.exam_data[0]["exam"],
        st.session_state.exam_data[0]["provider"],
        {
            "score": score,
            "completed_at": end_time,
            "duration_minutes": duration_minutes,
            "answers": st.session_state.exam_data,
            "batch_number": st.session_state.batch_info["number"],
            "batch_range": st.session_state.batch_info["range"]
        }
    )

def edit_exam():
    st.header("Edit Exam")
    
    exams = get_exam_list()
    if not exams:
        st.warning("No exams available")
        return
        
    selected_exam = st.selectbox(
        "Select Exam to Edit",
        options=[(e["exam"], e["provider"]) for e in exams],
        format_func=lambda x: f"{x[0]} - {x[1]}"
    )

    if selected_exam:
        exam = get_exam(selected_exam[0], selected_exam[1])
        questions = exam["questions"]
        modified = False

        st.info(f"Editing {len(questions)} questions")
        
        for i, question in enumerate(questions):
            with st.expander(f"Question {question['questionNumber']}: {question['questionText'][:100]}..."):
                # Display question options
                st.write("Options:")
                for opt in question["options"]:
                    st.write(f"- {opt['optionText']}")
                
                # Edit verified answer
                current_verified = question["verifiedAnswer"]
                new_verified = st.text_input(
                    "Verified Answer", 
                    value=current_verified,
                    key=f"verified_{i}"
                )
                if new_verified != current_verified:
                    question["verifiedAnswer"] = new_verified
                    modified = True
                
                # Toggle isMarked
                is_marked = st.checkbox(
                    "Mark Question for Review",
                    value=question.get("isMarked", False),
                    key=f"mark_{i}"
                )
                if is_marked != question.get("isMarked", False):
                    question["isMarked"] = is_marked
                    modified = True

        if modified and st.button("Save Changes"):
            if update_exam_questions(selected_exam[0], selected_exam[1], questions):
                st.success("Changes saved successfully!")
            else:
                st.error("Failed to save changes")

if __name__ == "__main__":
    main()
