import streamlit as st
from database import get_exam_list, get_user_exam_attempts
from typing import Dict

def show_attempt_details(attempt: Dict):
    with st.expander("View Attempt Details"):
        st.write("Analysis")
        
        answers = sorted(attempt["answers"], key=lambda x: x["questionNumber"])
        
        for q in answers:
            user_answer = q.get("userAnswer", "No answer")
            verified = q.get("verifiedAnswer", "Unknown")
            is_correct = user_answer == verified
            
            st.markdown(
                f"""
                **Q{q['questionNumber']}:** {
                    f"✔️ {user_answer}" if is_correct else 
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
    
    selected_exam = st.selectbox(
        "Filter by Exam",
        options=[(None, None)] + [(e["exam"], e["provider"]) for e in exams],
        format_func=lambda x: "All Exams" if x[0] is None else f"{x[0]} - {x[1]}"
    )
    
    if selected_exam[0] is None:
        all_attempts = []
        for exam in exams:
            attempts = get_user_exam_attempts(st.session_state.user_email, 
                                           exam["exam"], exam["provider"])
            for attempt in attempts:
                attempt["exam_name"] = exam["exam"]
                attempt["provider"] = exam["provider"]
                all_attempts.append(attempt)
    else:
        all_attempts = get_user_exam_attempts(st.session_state.user_email, 
                                            selected_exam[0], selected_exam[1])
        for attempt in all_attempts:
            attempt["exam_name"] = selected_exam[0]
            attempt["provider"] = selected_exam[1]
    
    if all_attempts:
        cols = st.columns([2, 2, 2, 1, 1, 2])
        
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
