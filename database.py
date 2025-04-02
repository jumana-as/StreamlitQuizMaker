import pymongo
import streamlit as st
from typing import List, Dict

@st.cache_resource
def get_database():
    # Initialize connection using connection string from host
    client = pymongo.MongoClient(st.secrets["mongo"]["connection_string"])
    return client.quizdb

def find_missing_questions(questions: List[Dict], total_questions: int) -> List[int]:
    # Sort questions by number
    question_numbers = sorted([q['questionNumber'] for q in questions])
    expected_range = set(range(1, total_questions + 1))
    actual_numbers = set(question_numbers)
    return sorted(list(expected_range - actual_numbers))

def save_exam(exam_data: List[Dict], session_time: int, total_questions: int, 
             uploaded_questions: int, questions_per_session: int):
    db = get_database()
    exam_info = exam_data[0]
    exam_name = exam_info["exam"]
    provider = exam_info["provider"]
    
    # Find missing questions using total_questions
    missing_questions = find_missing_questions(exam_data, total_questions)
    
    db.exams.update_one(
        {"exam": exam_name, "provider": provider},
        {
            "$set": {
                "questions": exam_data,
                "metadata": {
                    "sessionTime": session_time,
                    "totalQuestions": total_questions,
                    "uploadedQuestions": uploaded_questions,
                    "questionsPerSession": questions_per_session,
                    "missingQuestions": missing_questions,
                    "hasMissingQuestions": len(missing_questions) > 0
                }
            }
        },
        upsert=True
    )
    # Clear the cache after saving new data
    get_exam_list.clear()
    get_exam.clear()

@st.cache_data(ttl=600)
def get_exam_list():
    db = get_database()
    return list(db.exams.find({}, {"exam": 1, "provider": 1}))

@st.cache_data(ttl=600)
def get_exam(exam_name: str, provider: str):
    db = get_database()
    result = db.exams.find_one({"exam": exam_name, "provider": provider})
    return result if result else None

@st.cache_data(ttl=600)
def get_user_exam_attempts(email: str, exam_name: str, provider: str):
    db = get_database()
    attempts = db.progress.find(
        {"email": email, "exam": exam_name, "provider": provider},
        {"score": 1, "completed_at": 1, "duration_minutes": 1, "batch_number": 1, "batch_range": 1}
    ).sort("completed_at", -1)
    return list(attempts)

def save_user_progress(email: str, exam_name: str, provider: str, progress_data: Dict):
    db = get_database()
    db.progress.insert_one({  # Changed from update_one to insert_one for multiple attempts
        "email": email,
        "exam": exam_name,
        "provider": provider,
        **progress_data
    })
    # Clear the cache
    get_user_exam_attempts.clear()
