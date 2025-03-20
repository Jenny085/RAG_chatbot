import streamlit as st
import pandas as pd
import requests
import pdfplumber
from io import BytesIO
from dotenv import load_dotenv
import os


load_dotenv()


st.title("Upload File to FastAPI")
uploaded_file = st.file_uploader("Upload a file", type=["pdf", "csv", "xlsx"])

SERVER_URL = os.getenv("BACKEND_URL")



def extract_pdf_data(file: BytesIO):
    all_text = ""
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            all_text += page.extract_text() + "\n"  
    return all_text

if uploaded_file:
    if uploaded_file.name.endswith('.csv'):
        df = pd.read_csv(uploaded_file)
        content = df.to_string()
    elif uploaded_file.name.endswith('.xlsx'):
        df = pd.read_excel(uploaded_file)
        content = df.to_string()
    elif uploaded_file.name.endswith('.pdf'):
        content = extract_pdf_data(uploaded_file)
    else:
        st.error("Unsupported file type.")
        content = None
    response = requests.post(f"{SERVER_URL}/upload/", json={"content": str(content)})

    if response.status_code == 200:
        st.success(f"File uploaded: {uploaded_file.name}")
    else:
        st.error("Failed to upload file")

user_message = st.text_input("Enter your message")

if st.button("Send"):
    if user_message:
        response = requests.post(f"{SERVER_URL}/chat/", json={"user_message": str(user_message)})
        if response.status_code == 200:
            response_text = response.json().get("message", "No response received")
        else:
            response_text = f"Error: {response.status_code} - {response.text}"
        response_placeholder = st.empty()
        response_placeholder.write(response_text, unsafe_allow_html=True)
        



