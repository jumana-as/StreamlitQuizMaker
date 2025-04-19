import pymongo
import streamlit as st
from typing import List, Dict
from datetime import datetime

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

def update_exam_questions(exam_name: str, provider: str, questions: List[Dict]):
    db = get_database()
    # Get current exam data first
    exam = db.exams.find_one({"exam": exam_name, "provider": provider})
    if not exam:
        return False
    
    # Update questions while preserving metadata
    result = db.exams.update_one(
        {"exam": exam_name, "provider": provider},
        {
            "$set": {
                "questions": questions,
                "metadata": exam["metadata"]  # Preserve existing metadata
            }
        }
    )
    # Clear cache to reflect changes
    get_exam.clear()
    return result.modified_count > 0

def update_exam_metadata(exam_name: str, provider: str, session_time: int, total_questions: int, questions_per_session: int):
    db = get_database()
    exam = db.exams.find_one({"exam": exam_name, "provider": provider})
    if not exam:
        return False
    
    # Recalculate missing questions with new total_questions value
    missing_questions = find_missing_questions(exam["questions"], total_questions)
    
    result = db.exams.update_one(
        {"exam": exam_name, "provider": provider},
        {
            "$set": {
                "metadata": {
                    "sessionTime": session_time,
                    "totalQuestions": total_questions,
                    "questionsPerSession": questions_per_session,
                    "uploadedQuestions": len(exam["questions"]),
                    "missingQuestions": missing_questions,
                    "hasMissingQuestions": len(missing_questions) > 0
                }
            }
        }
    )
    get_exam.clear()
    return result.modified_count > 0

def update_single_question(exam_name: str, provider: str, question_number: int, 
                         verified_answer: str, is_marked: bool) -> bool:
    try:
        db = get_database()
        result = db.exams.update_one(
            {
                "exam": exam_name, 
                "provider": provider,
            },
            {
                "$set": {
                    "questions.$[q].verifiedAnswer": verified_answer,
                    "questions.$[q].isMarked": is_marked
                }
            },
            array_filters=[{"q.questionNumber": question_number}]
        )
        # Clear exam cache after update
        get_exam.clear()
        return True
    except Exception as e:
        print(f"Error updating question: {e}")
        return False

@st.cache_data(ttl=600)
def get_note(email: str, exam_name: str, provider: str, question_number: int) -> str:
    try:
        db = get_database()
        note = db.notes.find_one({
            "email": email,
            "exam": exam_name,
            "provider": provider,
            "questionNumber": question_number
        })
        return note["text"] if note else ""
    except Exception as e:
        print(f"Error getting note: {e}")
        return ""

def save_note(email: str, exam_name: str, provider: str, question_number: int, note_text: str) -> bool:
    try:
        db = get_database()
        db.notes.update_one(
            {
                "email": email,
                "exam": exam_name,
                "provider": provider,
                "questionNumber": question_number
            },
            {
                "$set": {
                    "text": note_text,
                    "updated_at": datetime.now()
                }
            },
            upsert=True
        )
        # Clear the specific note from cache
        get_note.clear()
        return True
    except Exception as e:
        print(f"Error saving note: {e}")
        return False

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
        {
            "score": 1, 
            "completed_at": 1, 
            "duration_minutes": 1, 
            "batch_number": 1, 
            "batch_range": 1,
            "answers": 1  # Add answers field to query projection
        }
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
