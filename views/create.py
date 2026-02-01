import streamlit as st
import json
from database import save_exam
import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import secrets
import requests
import msal

def encrypt_image(image_bytes, key):
    nonce = secrets.token_bytes(12)
    aesgcm = AESGCM(key)
    encrypted = aesgcm.encrypt(nonce, image_bytes, None)
    return nonce + encrypted  # prepend nonce for later decryption

def get_msal_access_token():
    """Get OneDrive access token using MSAL with cached credentials"""
    CLIENT_ID = st.secrets.get("MICROSOFT_CLIENT_ID")
    TENANT_ID = st.secrets.get("MICROSOFT_TENANT_ID", "common")
    SCOPES = ["Files.ReadWrite"]
    
    if not CLIENT_ID:
        raise ValueError("MICROSOFT_CLIENT_ID not configured in secrets")
    
    authority = f"https://login.microsoftonline.com/{TENANT_ID}"
    app = msal.PublicClientApplication(CLIENT_ID, authority=authority)
    
    # Try to use cached token first
    accounts = app.get_accounts()
    if accounts:
        result = app.acquire_token_silent(SCOPES, account=accounts[0])
        if "access_token" in result:
            return result["access_token"]
    
    # If no cached token, user needs to authenticate
    raise Exception(
        "No cached authentication available. Please ensure you've logged in with Microsoft "
        "and the MSAL cache is accessible. If this is your first time, logout and login again."
    )

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
                
                if not folder_name:
                    st.error("Please enter a folder name.")
                else:
                    try:
                        # Get access token using MSAL
                        access_token = get_msal_access_token()
                        upload_to_onedrive(folder_name, encrypted_files, access_token)
                        st.success("All images encrypted and uploaded to OneDrive successfully!")
                    except ValueError as e:
                        st.error(f"Configuration error: {e}")
                    except Exception as e:
                        st.error(f"Upload failed: {e}")

        if st.button("Save Exam"):
            save_exam(exam_data, session_time, total_questions, uploaded_questions, questions_per_session)
            st.success("Exam saved successfully!")
