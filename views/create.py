import streamlit as st
import json
from database import save_exam
import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import secrets
import requests

def encrypt_image(image_bytes, key):
    nonce = secrets.token_bytes(12)
    aesgcm = AESGCM(key)
    encrypted = aesgcm.encrypt(nonce, image_bytes, None)
    return nonce + encrypted  # prepend nonce for later decryption

def upload_to_onedrive(folder_name, files, access_token):
    # Create folder in OneDrive
    folder_url = f"https://graph.microsoft.com/v1.0/me/drive/root/children"
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    folder_data = {"name": folder_name, "folder": {}, "@microsoft.graph.conflictBehavior": "rename"}
    resp = requests.post(folder_url, headers=headers, json=folder_data)
    resp.raise_for_status()
    folder_id = resp.json()["id"]

    # Upload each file
    for filename, file_bytes in files.items():
        upload_url = f"https://graph.microsoft.com/v1.0/me/drive/items/{folder_id}:/"+filename+":/content"
        upload_resp = requests.put(upload_url, headers={"Authorization": f"Bearer {access_token}"}, data=file_bytes)
        upload_resp.raise_for_status()

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
        
        # --- New Feature: Image Folder Upload ---
        st.subheader("Upload Exam Images Folder")
        image_files = st.file_uploader(
            "Select all images in a folder (Ctrl+A to select all)", 
            type=["png", "jpg", "jpeg", "gif", "bmp"], 
            accept_multiple_files=True
        )
        if image_files:
            folder_name = st.text_input("Enter folder name for OneDrive (must match local folder name)")
            if st.button("Encrypt and Upload Images to OneDrive"):
                # Load AES key from secrets
                key = bytes.fromhex(st.secrets["AES_KEY"])
                encrypted_files = {}
                for img in image_files:
                    img_bytes = img.read()
                    encrypted = encrypt_image(img_bytes, key)
                    encrypted_files[img.name] = encrypted
                # Get access token from Streamlit authentication
                access_token = (st.user.tokens["access"] if st.user.is_logged_in else None)
                if not access_token:
                    st.error("No access token found. Please ensure you are logged in with Microsoft and have granted permission to access OneDrive.")
                elif not folder_name:
                    st.error("Please enter a folder name.")
                else:
                    try:
                        upload_to_onedrive(folder_name, encrypted_files, access_token)
                        st.success("All images encrypted and uploaded to OneDrive successfully!")
                    except Exception as e:
                        st.error(f"Upload failed: {e}")

        if st.button("Save Exam"):
            save_exam(exam_data, session_time, total_questions, uploaded_questions, questions_per_session)
            st.success("Exam saved successfully!")
