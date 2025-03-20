from fastapi import FastAPI
import streamlit as st
from openai import OpenAI
import tiktoken
from dotenv import load_dotenv
from supabase import create_client, Client
from pydantic import BaseModel

import os

load_dotenv()


SUPABASE_URL = os.getenv("SUPABASE_URL")  
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
api_key = os.getenv("OPENAI_API_KEY")

class UploadRequest(BaseModel):
    content: str

class ChatRequest(BaseModel):
    user_message: str



supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
client = OpenAI(api_key=api_key)
app = FastAPI()



def num_tokens_from_string(string):
    encoding = tiktoken.get_encoding("cl100k_base")
    num_tokens = len(encoding.encode(string))
    return num_tokens

def chunk_text(text, max_tokens=200):
    words = text.split()
    chunks = []
    current_chunk = []

    for word in words:
        temp_chunk = current_chunk + [word]
        temp_text = " ".join(temp_chunk)
        new_token_count = num_tokens_from_string(temp_text)
        
        if new_token_count > max_tokens:
            chunks.append(" ".join(current_chunk))
            current_chunk = [word]
        else:
            current_chunk.append(word)

    if current_chunk:
        chunks.append(" ".join(current_chunk))
    
    return chunks

@app.post("/upload/")
async def upload_content(request: UploadRequest):
    content = request.content.upper()
    try:
        chunks = chunk_text(content, max_tokens=500)
        for chunk in chunks:
            print("chunk",chunk)
            response = client.embeddings.create(
                input=chunk,
                model="text-embedding-ada-002"
            )
            embedding = response.data[0].embedding            
            print(embedding)

            data = {
                "text": content,
                "embedding": embedding
            }
            
            response = supabase.table("documents").insert(data).execute()
        
        return {"message": "Content uploaded successfully", "response": response.data}
    
    except Exception as e:
        print(e)
        return {"error": str(e)}


@app.post("/chat/")
async def chat(request: ChatRequest):
    user_message = request.user_message.upper()

    try:
        response = client.embeddings.create(
            input=user_message,
            model="text-embedding-ada-002"
        )
        user_embedding = response.data[0].embedding

        query = supabase.rpc(
            'match_documents',
            {
                'query_embedding': user_embedding,
                'match_threshold': 0.7,
                'match_count': 2
            }
        ).execute()

        similar_contents = [item['content'] for item in query.data]

        if similar_contents:
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[{
                    "role": "user", 
                    "content": f"Based on the following content:\n{similar_contents}\n\nUser: {user_message}\n\nAI:"
                }]
            )
            
            return {
                "message": response.choices[0].message.content,
                "status": "success"
            }
        else:
            return {
                "message": "No relevant content found",
                "status": "error"
            }
            
    except Exception as e:
        return {
            "message": str(e),
            "status": "error"
        }
