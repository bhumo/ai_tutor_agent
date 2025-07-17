# 🎓 Tutor Agent

# 🚀 AI Tutor Agent: Your AI-Powered Learning Companion 🧠

**Your personal AI tutor for Math & Physics!**

**✨ Features:** Intelligent agent switching, powerful tools, web search, and a user-friendly chat interface.

**🛠️ Tech Stack:** Gemini Pro, LangChain, LangGraph, FastAPI, SymPy, Pint, DuckDuckGo, Matplotlib, HTML/CSS/JS

---

Tutor Agent is an intelligent AI tutor designed to help students master **math** and **physics** problems with step-by-step guidance. Powered by **Google's Gemini Pro**, this agent integrates a suite of smart tools and offers a clean, intuitive chat interface for a truly helpful learning experience.

Whether you need to solve complex equations, convert units, plot functions, or even find practice papers, this agent is equipped to assist you.

---

## Live Website

Render Deployment: 
https://ai-tutor-agent-736f.onrender.com

Note: Previously the website was hosted on railways 

## ✨ Key Features & Capabilities

- 🧠 **Smart Agent Switching:** Intelligently routes your questions to the appropriate Math or Physics solver.
- 🧰 **Uses Tools** – Calculator, symbolic solver, unit converter, and more.
- 🌐 **Safe Web Search:** Accesses academic resources and filters out irrelevant or unsafe content.
- 💬 **Explains Like a Real Tutor** – Breaks down problems, explains the why behind answers, and gives similar practice problems.
- ✨ **Modern Chat UI:**  Features a clean design with avatars, Markdown support, and a typing indicator for a smooth user experience.

---

## 🛠️ Technical Deep Dive

| Layer       | Tools Used                             |
|-------------|-----------------------------------------|
| LLM         | Gemini Pro via `langchain_google_genai` |
| Orchestration | LangChain + LangGraph                  |
| API         | FastAPI                                 |
| Frontend    | HTML, Bootstrap, JavaScript             |
| Tools       | SymPy, Pint, DuckDuckGo, Matplotlib     |

---

## 🚀 Local Setup

### 1. Install dependencies
```bash
pip install -r requirements.txt
```
### 2. Setting up the Gemini API Key
```bash
# Way 1
In the file main.py set the environment variable os.environ["GEMINI_API_KEY"] before line 31.
# Way 2
Alternatively, update the api_key in api_keys\gemini_api_key.yaml and set api_key = config["gemini"]["api_key"] in main.py at line 31.
```
### 3. To run the backend server 
In ai_tutor_agent folder (that is my root directory) run the following command
```bash
 uvicorn main:app --reload
```

Now go to the web browser and you can see the frontend at (http://localhost:8000/ )
