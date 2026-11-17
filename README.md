# Getnet AI — Multi-Agent Support System

An AI support system developed for the Getnet AI Hardcore Engineer technical challenge.

The project uses specialized agents to classify requests, retrieve information, and handle customer inquiries.

## 1. Architecture

The system consists of three main agents:

- **Router Agent:** Identifies user intent and selects the appropriate agent.
- **Knowledge Agent:** Uses RAG and web search to retrieve information.
- **Customer Support Agent:** Retrieves customer and transaction data through dedicated tools.

FastAPI handles incoming requests and connects them to the agent workflow.

## 2. Technologies

- Python
- FastAPI
- OpenAI API
- NumPy
- JSON-based mock data
- Docker
- Pytest

## 3. Project Structure

```text
getnet-ai/
│
├── app/
│   ├── agents/
│   ├── tools/
│   ├── rag/
│   ├── database/
│   └── main.py
│
├── data/
│   ├── docs/
│   ├── index/
│   └── users.json
│
├── tests/
│
├── SPEC.md
├── README.md
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .env.example
└── .gitignore
```

## 4. How It Works

1. The user sends a message through the API.
2. The Router Agent identifies the request type.
3. The appropriate agent is selected.
4. The agent retrieves information using RAG, web search, or customer tools.
5. The LLM generates the response.
6. The API returns the result as JSON.

## 5. Installation

Clone the repository:

```bash
git clone YOUR_REPOSITORY_URL
cd getnet-ai
```

Create a virtual environment:

```bash
python -m venv venv
```

Activate it on Windows:

```bash
venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Create a `.env` file based on `.env.example`.

## 6. Run the Application

Start the API:

```bash
uvicorn app.main:app --reload
```

API documentation:

`http://localhost:8000/docs`

Health check:

`GET http://localhost:8000/health`

## 7. Docker

Build and run the application:

```bash
docker compose up --build
```

## 8. Testing

Run automated tests:

```bash
pytest tests/ -v
```

Testing covers agent routing, RAG retrieval, customer tools, API responses, and error handling.

## 9. Design Considerations

The architecture keeps each agent focused on a specific responsibility, making the system easier to test, maintain, and extend.

Customer data is simulated; no private Getnet production systems are required or accesed.

The initial implementation prioritizes functionality, reliability, and clear separation of responsibilities over unnecessary complexity.

Requieres an OpenAI API Key.

## 10. Future Improvements

- Human escalation.
- Improved retrieval and ranking.
- Additional support tools.
- Better monitoring and logging.
- More advanced agent workflows.