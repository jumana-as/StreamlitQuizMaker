import streamlit as st
from typing import Dict

def format_comment_head(head: str) -> str:
    """Format special phrases in comment headers as bold"""
    for phrase in ["Highly Voted", "Most Recent"]:
        if phrase in head:
            head = head.replace(phrase, f"**{phrase}**")
    return head

def show_question_comments(question: Dict):
    """Shared function to display question comments consistently"""
    st.write("Comments:")
    for comment in question["comments"]:
        head = comment['commentHead'].replace('\n', ' ').replace('\t', ' ').strip()
        head = format_comment_head(head)
        content = comment['commentContent'].replace('\n', ' ').replace('\t', ' ').strip()
        selected = f" [{comment.get('commentSelectedAnswer', '')}]" if comment.get('commentSelectedAnswer') else ""
        st.markdown(f"{head}{selected}: {content}")
    st.write(f"Suggested Answer: {question['suggestedAnswer']}")
    st.write("Vote Distribution:", question["voteDistribution"])
    st.write(f"Verified Answer: {question['verifiedAnswer']}")
