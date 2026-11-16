# SPEC — Getnet Multi-Agent Support System :D

## 1. Overview

Develop an AI support system that classifies user requests and routes them to specialized agents.

The system will handle:
- Getnet product and service questions.
- General questions using external tools.
- Customer-specific inquiries.

## 2. Technology Stack

| Component | Technology |
|---|---|
| Language | Python 3.15.2 |
| API | FastAPI |
| LLM | OpenAI |
| Embeddings | OpenAI Embeddings |
| Vector Search | NumPy |
| Customer Data | JSON |
| Web Search | DuckDuckGo |
| Containerization | Docker |

## 3. System Architecture

The system will have three main components:

### Router Agent
- Identifies user intent.
- Selects the appropriate agent.
- Handles invalid classifications.

### Knowledge Agent
- Uses RAG to retrieve Getnet documentation.
- Uses web search for general questions.
- Generates answers based on retrieved information.

### Customer Support Agent
- Retrieves customer and transaction information.
- Uses dedicated tools to check payment and terminal status.

## 4. Functional Requirements

- Provide a `POST /chat` endpoint accepting `message` and `user_id`.
- Return structured JSON responses.
- Support RAG and web search.
- Implement at least two customer support tools.
- Keep customer data separate from public documentation.
- Support multiple languages.
- Provide a `GET /health` endpoint.
- Run through Docker Compose.

## 5. Security and Reliability

- Validate incoming requests.
- Prevent unauthorized customer data access.
- Store API keys in environment variables.
- Handle LLM and tool failures.
- Avoid unsupported answers.
- Log request routes, tool usage, and execution time.

## 6. API Contract

**Request:**

```json
{
  "message": "string",
  "user_id": "string"
}
```

**Response:**

```json
{
  "route": "support",
  "agent": "customer_support",
  "answer": "Response text",
  "sources": [],
  "tool_calls": [],
  "latency_ms": 0
}
```

## 7. Acceptance Criteria

The solution must:

- Correctly classify and route requests.
- Retrieve relevant Getnet documentation.
- Use web search for general questions.
- Retrieve customer transactions and payment information.
- Enforce customer data isolation.
- Return valid JSON responses.
- Handle errors without crashing.
- Run successfully using Docker Compose.

## 8. Development Approach

Development will follow Spec-Driven Development (SDD).

The priority is a functional core solution, clear component responsibilities, and reproducible execution. Additional features will be considered after the main requirements are completed.