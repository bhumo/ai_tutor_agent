from fastapi import FastAPI, Request
from utils.load_gemini_api import set_gemini_api_key
# from utils.generate_queries import generate_gemini_query
# import google.generativeai as genai
# from agents.tutor_agent import tutor_agent
# app = FastAPI()
# set_gemini_api_key()
# @app.post("/query")

# async def handle_query(request: Request):
#     data = await request.json()
#     query = data.get("query")
#     if not query:
#         return {"error": "No query provided."}
#     # response = generate_gemini_query(query)
#     response = tutor_agent(query)
#     print("Response from Gemini API:", response)
#     return {"response": response}

from fastapi import FastAPI, Request
from graph.workflow import TutorWorkflow
import yaml
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
import os

with open("api_keys/gemini_api_key.yaml") as f:
    config = yaml.safe_load(f)

app = FastAPI(title="Mini Tutor Agent")
set_gemini_api_key()
api_key = os.environ["GEMINI_API_KEY"] 
# workflow = TutorWorkflow(config["gemini"]["api_key"])
workflow = TutorWorkflow(api_key)
# Mount the frontend folder
app.mount("/static", StaticFiles(directory="frontend"), name="static")

# Serve the HTML page at root
@app.get("/", response_class=HTMLResponse)
async def serve_home():
    return FileResponse("frontend/index.html")

# API endpoint for chat
@app.post("/chat")
async def chat(request: Request):
    data = await request.json()
    message = data.get("message")
    print("Received message:", message)
    if not message:
        return {"error": "No message provided."}
    response = workflow.process_query(message)
    return {"response": response}