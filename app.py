import streamlit as st
import json
import time
import math
from datetime import datetime, timedelta
from typing import Dict
from auth import init_auth, authenticate, is_authorized
from database import save_exam, get_exam_list, get_exam, save_user_progress, get_user_exam_attempts, update_exam_metadata, update_single_question

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
    mode = st.sidebar.radio("Select Mode", ["Practice", "Create", "Edit", "History"])
    
    if mode == "Create":
        create_exam()
    elif mode == "Edit":
        edit_exam()
    elif mode == "History":
        show_history()
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
            
            # Sort and store selected questions for this attempt
            questions = sorted(exam["questions"][start_idx:end_idx], 
                            key=lambda q: q['questionNumber'])
            st.session_state.exam_data = questions
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
    st.subheader(f"{question['questionNumber']}")
    st.write(question["questionText"])
    
    # Show options
    selected_option = st.radio(
        "Select your answer:",
        options=[f"{opt['optionLetter']}. {opt['optionText']}" for opt in question["options"]],
        key=f"q_{question['questionNumber']}"
    )
    
    # Mark for review
    question["isMarked"] = st.checkbox("Mark for review", 
                                     key=f"mark_{question['questionNumber']}")
    
    # Store user answer - only save the option letter
    question["userAnswer"] = selected_option.split(".")[0].strip()
    
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
            head = comment['commentHead'].replace('\n', ' ').replace('\t', ' ').strip()
            content = comment['commentContent'].replace('\n', ' ').replace('\t', ' ').strip()
            selected = f" [{comment.get('commentSelectedAnswer', '')}]" if comment.get('commentSelectedAnswer') else ""
            st.write(f"{head}{selected}: {content}")
        st.write(f"Suggested Answer: {question['suggestedAnswer']}")
        st.write("Vote Distribution:", question["voteDistribution"])
        st.write(f"Verified Answer: {question['verifiedAnswer']}")

def show_results():
    # Compare option letters directly
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
    # st.header("Edit")
    
    # Create placeholders
    question_nav = st.sidebar.container()
    
    # Main content
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
        
        # Add cache refresh button at top
        st.button("🔄 Refresh Cache", on_click=get_exam.clear)
        
        # Add metadata editing section
        with st.expander("Edit Exam Settings", expanded=True):
            st.subheader("Metadata")
            meta = exam["metadata"]
            
            # Show missing questions info
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

        # Question editing section
        st.subheader("")
        questions = sorted(exam["questions"], key=lambda q: q['questionNumber'])

        # Add side navigation
        with question_nav:
            # st.sidebar.markdown("### ")
            st.sidebar.markdown(
                """
                <style>
                    .question-nav {
                        max-height: 400px;
                        overflow-y: auto;
                        padding: 10px;
                    }
                    .question-link {
                        display: block;
                        padding: 5px;
                        margin: 2px 0;
                        text-decoration: none;
                        color: inherit;
                    }
                    .question-link:hover {
                        background-color: #f0f2f6;
                        border-radius: 4px;
                    }
                    .current {
                        background-color: #e6f3ff;
                        border-radius: 4px;
                    }
                </style>
                <div class="question-nav">
                """,
                unsafe_allow_html=True
            )
            
            for i, q in enumerate(questions):
                icons = []
                if q.get("isMarked", False):
                    icons.append("🚩")
                if not q.get("verifiedAnswer"):
                    icons.append("⚠️")
                    
                icon_str = " ".join(icons)
                current_class = " current" if i == st.session_state.editing_question else ""
                
                st.sidebar.markdown(
                    f"""<div class="question-link{current_class}" onclick="location.href='#{i}'">Q{q['questionNumber']} {icon_str}</div>""", 
                    unsafe_allow_html=True
                )
            
            st.sidebar.markdown("</div>", unsafe_allow_html=True)

        # Display current question
        question = questions[st.session_state.editing_question]
        st.markdown(f'<div id="{st.session_state.editing_question}"></div>', unsafe_allow_html=True)
        with st.container():
            st.markdown(f"### {question['questionNumber']}")
            st.write(question['questionText'])
            
            # Display question options
            st.write("Options:")
            for opt in question["options"]:
                st.write(f"{opt['optionLetter']}. {opt['optionText']}")
            
            cols = st.columns([3, 1, 1])
            with cols[0]:
                new_verified = st.text_input(
                    "Verified Answer", 
                    value=question.get("verifiedAnswer", "")
                )
            
            with cols[1]:
                is_marked = st.checkbox(
                    "Mark for Review",
                    value=question.get("isMarked", False)
                )
            
            with cols[2]:
                if (new_verified != question.get("verifiedAnswer", "") or 
                    is_marked != question.get("isMarked", False)):
                    if st.button("Save"):
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

            # Add details expander
            with st.expander("Show Details"):
                st.write("Comments:")
                for comment in question["comments"]:
                    head = comment['commentHead'].replace('\n', ' ').replace('\t', ' ').strip()
                    content = comment['commentContent'].replace('\n', ' ').replace('\t', ' ').strip()
                    selected = f" [{comment.get('commentSelectedAnswer', '')}]" if comment.get('commentSelectedAnswer') else ""
                    st.write(f"{head}{selected}: {content}")
                st.write(f"Suggested Answer: {question['suggestedAnswer']}")
                st.write("Vote Distribution:", question["voteDistribution"])
                st.write(f"Verified Answer: {question['verifiedAnswer']}")

        # Add navigation buttons
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

def show_attempt_details(attempt: Dict):
    with st.expander("View Attempt Details"):
        st.write("Analysis")
        
        # Sort answers by question number
        answers = sorted(attempt["answers"], key=lambda x: x["questionNumber"])
        
        for q in answers:
            user_answer = q.get("userAnswer", "No answer")
            verified = q.get("verifiedAnswer", "Unknown")
            is_correct = user_answer == verified
            
            # Format the comparison row
            st.markdown(
                f"""
                **Q{q['questionNumber']}:** {
                    f"✓ {user_answer}" if is_correct else 
                    f"❌ <span style='color: red'>{user_answer}</span> (Correct: {verified})"
                }
                """,
                unsafe_allow_html=True
            )

def show_history():
    st.header("Attempt History")
    
    exams = get_exam_list()
    if not exams:
        st.warning("No exams available")
        return
    
    # Add exam filter
    selected_exam = st.selectbox(
        "Filter by Exam",
        options=[(None, None)] + [(e["exam"], e["provider"]) for e in exams],
        format_func=lambda x: "All Exams" if x[0] is None else f"{x[0]} - {x[1]}"
    )
    
    # Get and display attempts
    if selected_exam[0] is None:
        # Show all attempts across all exams
        all_attempts = []
        for exam in exams:
            attempts = get_user_exam_attempts(st.session_state.user_email, 
                                           exam["exam"], exam["provider"])
            for attempt in attempts:
                attempt["exam_name"] = exam["exam"]
                attempt["provider"] = exam["provider"]
                all_attempts.append(attempt)
    else:
        # Show attempts for selected exam
        all_attempts = get_user_exam_attempts(st.session_state.user_email, 
                                            selected_exam[0], selected_exam[1])
        for attempt in all_attempts:
            attempt["exam_name"] = selected_exam[0]
            attempt["provider"] = selected_exam[1]
    
    if all_attempts:
        history_df = {
            "Date": [],
            "Exam": [],
            "Batch": [],
            "Score": [],
            "Duration (minutes)": [],
            "Actions": []
        }
        
        # Create two columns for each attempt
        cols = st.columns([2, 2, 2, 1, 1, 2])
        
        # Headers
        cols[0].write("**Date**")
        cols[1].write("**Exam**")
        cols[2].write("**Batch**")
        cols[3].write("**Score**")
        cols[4].write("**Duration**")
        cols[5].write("**Details**")
        
        for attempt in sorted(all_attempts, key=lambda x: x["completed_at"], reverse=True):
            cols[0].write(attempt["completed_at"].strftime("%Y-%m-%d %H:%M"))
            cols[1].write(f"{attempt['exam_name']} ({attempt['provider']})")
            cols[2].write(f"Batch {attempt.get('batch_number', '?')} ({attempt.get('batch_range', 'unknown')})")
            cols[3].write(f"{attempt['score']:.2f}%")
            cols[4].write(f"{attempt['duration_minutes']:.1f}")
            if cols[5].button("Details", key=f"detail_{attempt['completed_at'].strftime('%Y%m%d%H%M%S')}"):
                show_attempt_details(attempt)

    else:
        st.info("No attempts found")

if __name__ == "__main__":
    main()
