# 🎓 AI Tutor Agent with Authentication

**Your personal AI tutor for Math & Physics - Now with secure user authentication!**

**✨ New Features:**
- 🔐 **User Authentication**: Secure email/password login and Google OAuth support
- 👤 **Personalized Experience**: User profiles and conversation tracking
- �️ **Secure Sessions**: JWT token-based authentication
- 📱 **Modern UI**: Clean login interface with responsive design

**✨ Core Features:**
- 🧠 Intelligent agent switching between Math and Physics
- 🧰 Powerful tools (Calculator, symbolic solver, unit converter)
- 🌐 Safe web search for academic resources
- 💬 Human-like explanations and step-by-step guidance
- 📊 Interactive charts and visualizations

**🛠️ Tech Stack:**
- **Backend**: FastAPI, SQLAlchemy, JWT Authentication
- **AI**: Google Gemini Pro, LangChain, LangGraph
- **Tools**: SymPy, Pint, Matplotlib
- **Frontend**: HTML5, Bootstrap, JavaScript
- **Database**: SQLite (development) / PostgreSQL (production)

---

## 🌐 Live Website

**Render Deployment:** [https://ai-tutor-agent-736f.onrender.com](https://ai-tutor-agent-736f.onrender.com)

*Note: Create an account or use the demo login to start learning!*
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

## 🚀 Quick Setup

### Option 1: Automated Setup (Recommended)
```bash
# Clone the repository
git clone https://github.com/yourusername/ai_tutor_agent.git
cd ai_tutor_agent

# Run the setup script
python setup.py

# Install dependencies
pip install -r requirements.txt

# Update .env file with your Gemini API key
# Edit .env file and add your GEMINI_API_KEY

# Start the application
uvicorn main:app --reload
```

### Option 2: Manual Setup
```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Create environment file
cp .env.example .env
# Edit .env and add your API keys

# 3. Start the application
uvicorn main:app --reload
```

### 🔑 Credentials Required
- **Gemini API Key** (Required): create it in Google AI Studio and store it only in `.env`.
- **Secret key** (Required): set a random `SECRET_KEY` of at least 32 characters.
- **Langfuse keys** (Optional): set the public and secret keys to export traces.

### 🌐 Access the Application
- **Main Application**: http://localhost:8000
- **Login Page**: http://localhost:8000/login
- **API Documentation**: http://localhost:8000/docs

---

## 🔐 Authentication Features

### Email/Password Authentication
- Secure user registration and login
- Password hashing with bcrypt
- JWT token-based sessions

### User Management
- User profiles with personalization
- User-owned, persisted tutoring sessions
- Secure logout

---

## 🧠 RAG Architecture

The LangGraph workflow first uses a Pydantic-validated LLM judge to route requests to math, physics, chemistry, biology, computer science, or rejection. Unsupported requests stop immediately. Each supported domain agent searches only its portion of the ten-topic corpus in `rag/data/knowledge.json`, fusing BM25-style lexical and dense concept-vector rankings.

When local evidence exists, the response is grounded and its citations are marked `evidence`. When the supported topic is missing, the base model answers and an allow-list search adds Khan Academy or OpenStax links marked `further_reading`; these fallbacks are logged in `logs/model_fallback.jsonl`. The application never presents further-reading links as evidence.

Gemini responses use Pydantic schemas for both routing and generation. `TutorAnswer` validates the final API contract. Langfuse observations cover semantic routing, each domain agent, retrieval, and generation. Trace scores record router confidence, support decisions, and local-context availability.

```bash
# Deterministic unit, routing, audit, schema, and retrieval p95 checks
python -m pytest -q

# Full-corpus offline hallucination and retrieval gate
python -m evaluation.hallucination

# Credentialed routing, retrieval, and Ragas faithfulness gates
pip install -r requirements-eval.txt
python -m evaluation.run_ragas

# Offline paired baseline/candidate quality and latency gate
python -m evaluation.ab_test
```

The Ragas command makes Gemini calls. Unit tests use fakes and need no network or API key.

See `docs/architecture_review.md` for the system's production-readiness assessment and scaling roadmap.
