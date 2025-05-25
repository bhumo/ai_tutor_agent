from fastapi import FastAPI, Request
from utils.load_gemini_api import set_gemini_api_key
from utils.generate_queries import generate_gemini_query
import google.generativeai as genai

app = FastAPI()
set_gemini_api_key()
@app.post("/query")
async def handle_query(request: Request):
    data = await request.json()
    query = data.get("query")
    if not query:
        return {"error": "No query provided."}
    response = generate_gemini_query(query)
    print("Response from Gemini API:", response)
    return {"response": response}