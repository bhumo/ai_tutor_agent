# 🎓 Tutor Agent

**Tutor Agent** is your personal AI tutor — built to help students learn and solve **math** and **physics** problems step-by-step. It's powered by **Gemini Pro**, enhanced with smart tools, and comes with a clean, chat-style web interface that actually feels helpful (not robotic).

Whether you want to solve an equation, convert units, plot a function, or even find SAT mock papers — this agent has your back. 💡

---

## Live Website

The website is deployed using the railway : https://web-production-32aed.up.railway.app/

## 🧠 What it Can Do

- 🔁 **Smart Agent Switching** – Knows when to send your question to the math brain 🧮 or the physics brain 🔬.
- 🧰 **Uses Tools** – Calculator, symbolic solver, unit converter, and more.
- 🌐 **Safe Web Search** – Finds academic content (like SAT papers) and filters out junk and unsafe links.
- 💬 **Explains Like a Real Tutor** – Breaks down problems, explains the why behind answers, and gives similar practice problems.
- ✨ **Modern Chat UI** – Enter key + send button, avatars, Markdown support, and even a typing spinner!

---

## 🔧 Tech Stack

| Layer       | Tools Used                             |
|-------------|-----------------------------------------|
| LLM         | Gemini Pro via `langchain_google_genai` |
| Orchestration | LangChain + LangGraph                  |
| API         | FastAPI                                 |
| Frontend    | HTML, Bootstrap, JavaScript             |
| Tools       | SymPy, Pint, DuckDuckGo, Matplotlib     |

---

## 🖥️ Usage (Project Setup locally)

### 1. Install dependencies
```bash
pip install -r requirements.txt
```
### 2. Setting up the Gemini API Key
```bash
# Way 1
In the file main.py set the enviorement os.environ["GEMINI_API_KEY"] before line 31 as the api_key
# Way 2
Second method is to update the api_key in api_keys\gemini_api_key.yaml and in main.py at line 31 set api_key = config["gemini"]["api_key"]
```
### 3. To run the backend server 
In ai_tutor_agent folder (that is my root directory) run the following command
```bash
 uvicorn main:app --reload
```

Now go to the web browser and you can see the frontend at (http://localhost:8000/ )


