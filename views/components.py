import streamlit as st
from typing import Dict, List

def format_comment_head(head: str) -> str:
    """Format special phrases in comment headers as bold"""
    for phrase in ["Highly Voted", "Most Recent"]:
        if phrase in head:
            head = head.replace(phrase, f"**{phrase}**")
    return head

def format_vote_distribution(votes: List[Dict]) -> str:
    """Format vote distribution with percentages and highlight most voted"""
    if not votes:
        return "No votes"
        
    # Calculate total votes
    total_votes = sum(v["vote_count"] for v in votes)
    
    # Format each vote entry
    formatted_votes = []
    for vote in votes:
        percentage = (vote["vote_count"] / total_votes) * 100
        vote_text = f"{vote['voted_answers']} ({percentage:.0f}%)"
        
        # Add bold and star for most voted
        if vote.get("is_most_voted", False):
            vote_text = f"**{vote_text}** ⭐"
            
        formatted_votes.append(vote_text)
    
    return ", ".join(formatted_votes)

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
    
    # Format and display vote distribution
    vote_dist = format_vote_distribution(question["voteDistribution"])
    st.markdown(f"Vote Distribution: {vote_dist}")
    
    st.write(f"Verified Answer: {question['verifiedAnswer']}")
