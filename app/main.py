import time

from fastapi import FastAPI
from pydantic import BaseModel, Field

from app.agents import knowledge_agent, route, support_agent

app = FastAPI(title="Getnet Multi-Agent Support")


# Lo que se recibe en /chat, se limita el tamaño para que no manden mensajes gigantes evitar gastos en la tokenización
class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    user_id: str = Field(min_length=1, max_length=64)


@app.post("/chat")
def chat(req: ChatRequest):
    inicio = time.time()

    # 1) El router decide qué agente contesta
    decision = route(req.message)

    # 2) Se llama al agente que eligió el router
    try:
        if decision["agent"] == "support":
            resultado = support_agent(req.message, req.user_id)
        else:
            resultado = knowledge_agent(req.message)
    except Exception as e:
        print("ERROR en el agente:", e)
        resultado = {"agent": decision["agent"], "sources": [], "tool_calls": [],
                     "answer": "Sorry, something went wrong. Please try again or call Getnet at 4002 4000."}

    latencia = round((time.time() - inicio) * 1000)  # En milisegundos
    print("Ruta:", decision["agent"], "| Herramientas:", [c["tool"] for c in resultado["tool_calls"]],
          "| Latencia:", latencia, "ms")

    return {"user_id": req.user_id, "route": decision, **resultado, "latency_ms": latencia}


@app.get("/health")
def health():
    return {"status": "ok"}
