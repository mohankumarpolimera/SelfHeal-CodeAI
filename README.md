# 🤖 SelfHeal-CodeAI  

**SelfHeal-CodeAI** is an **Agentic AI system** built with **LangGraph, Groq LLM, and MCP (Model Context Protocol)** that can **generate, validate, debug, and self-heal code automatically**.  

It mimics how a human developer works:  
- Generate code from a request  
- Validate execution in a sandbox  
- Detect errors  
- Search docs/StackOverflow  
- Fix issues iteratively (self-heal loop)  
- Learn from history via memory  

🔥 Designed as a **portfolio project** to stand out for recruiters in **Sep 2025**.  

---

## ✨ Features  

- 🧠 **Multi-Agent System** (LangGraph)  
  - Code Generator Agent → Generates Python code using Groq LLM  
  - Validator Agent → Runs sandbox/tester for correctness  
  - Error Analyzer Agent → Fetches docs & StackOverflow solutions  
  - Fixer Agent → Iteratively heals errors with context  
  - Memory Agent → Stores past fixes in ChromaDB (MCP service)  
  - Learner Agent → Learns patterns for dynamic self-healing  

- 🔒 **Sandboxed Execution** – runs code safely in isolated subprocess.  
- 🧪 **Automated Testing** – validates programs using `pytest/unittest`.  
- 📚 **MCP Servers** – extendable tools for docs, StackOverflow, ChromaDB.  
- 🌐 **Frontend UI** – simple interface to try prompts like:  

**Example** - create a calculator program in python

and watch it generate → validate → fix → finalize.  

---

## 📂 Folder Structure
mermaid
```
selfheal-code-ai/
│── agents/
│ ├── code_generator.py # Groq LLM agent for code generation
│ ├── validator.py # Agent that calls MCP sandbox/tester
│ ├── error_analyzer.py # Agent that calls MCP-docs/stackoverflow
│ ├── fixer.py # Healing agent (Groq LLM + context)
│ ├── memory.py # Agent that calls MCP-Chroma
│ ├── learner.py # Learner agent (improves with history)
│
│── mcp_servers/
│ ├── sandbox_server.py # Runs user code in isolated subprocess/container
│ ├── tester_server.py # Runs pytest/unittest
│ ├── docs_server.py # Fetches library docs (PyPI/official docs API)
│ ├── stackoverflow_server.py# Fetches Q&A via API
│ ├── chroma_server.py # Wraps ChromaDB as MCP endpoint
│
│── graph/
│ ├── state.py # CodeState class
│ ├── selfheal_graph.py # LangGraph workflow (nodes + edges)
│
│── utils/
│ ├── sandbox_runner.py # Helper for code sandboxing
│ ├── test_runner.py # Helper for running tests
│ ├── mcp_client.py # Generic MCP client wrapper
│
│── frontend/
│ ├── index.html # Web UI
│ ├── script.js # Frontend logic
│ ├── style.css # Styling
│
│── app.py # FastAPI app (boot + serve frontend + MCP)
│── requirements.txt # Dependencies
│── README.md # Documentation
```
---

## ⚙️ Tech Stack  

- **LLM**: [Groq API](https://groq.com/)  
- **Agent Framework**: [LangGraph](https://python.langchain.com/docs/langgraph)  
- **Multi-Agent Execution**: LangChain + MCP  
- **FastAPI** – Backend REST API + MCP bootstrap  
- **Frontend** – Simple HTML/JS interface  
- **ChromaDB** – Long-term memory  
- **Pytest/Unittest** – Code validation  
- **StackOverflow & Docs APIs** – Contextual error fixing  

---

## 🚀 Getting Started  

### 1. Clone repo
```bash
git clone https://github.com/mohankumarpolimera/selfheal-code-ai.git
cd selfheal-code-ai
```
### 2. Create virtual environment
```bash
python -m venv venv
source venv/bin/activate   # Linux/Mac
venv\Scripts\activate      # Windows
```
### 3. Install dependencies
```bash
pip install -r requirements.txt
```
### 4. Add .env
# .env
GROQ_API_KEY=your_groq_api_key

### 5. Run the system
```bash
python app.py
```
### 6. Open in browser

👉 Visit http://127.0.0.1:8000

**🧩 Example Usage**

### Prompt:

### create a calculator program in python

mermaid
```
Workflow:

Code Generator → produces calculator code

Validator → runs in sandbox

Error Analyzer → finds missing imports (if any)

Fixer → heals automatically

Memory → stores solution

Learner → updates for future requests

✅ Output: final working calculator program.
```
