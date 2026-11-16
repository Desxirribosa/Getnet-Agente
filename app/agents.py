import json
from functools import partial

from app import llm, tools
from app.rag import search

# ============================== AGENTE ROUTER ==============================
# Este agente no contesta, solo decide a qué agente mandar el mensaje (knowledge o support)
ROUTER_PROMPT = """You are the Router Agent of Getnet's merchant support assistant.
Decide which specialist agent must handle the merchant's message. Never answer it yourself.

Agents:
- "knowledge": questions answered with information, not the merchant's own account.
  Getnet products, fees, how-tos (Get Clássica, Get Smart, Pix, antecipação, crediário, payment link)
  AND general questions (weather, exchange rates, news).
- "support": needs THIS merchant's own data: their deposits, their transactions or declines,
  their card machine status. Signals: "my machine", "my sales", "yesterday's sales".

Examples:
"What's the difference between Get Clássica and Get Smart?" -> knowledge
"What's the euro exchange rate today?" -> knowledge
"When will the money from yesterday's sales be deposited?" -> support
"My card machine won't connect to the internet" -> support
"Do I need a bank account to receive via Pix?" -> knowledge

Reply ONLY with JSON: {"agent": "knowledge" | "support", "reason": "<max 15 words>"}"""


def route(mensaje):
    try:
        resp = llm.get_client().chat.completions.create(
            model=llm.CHAT_MODEL, temperature=0,
            response_format={"type": "json_object"},
            messages=[{"role": "system", "content": ROUTER_PROMPT},
                      {"role": "user", "content": mensaje}],
        )
        decision = json.loads(resp.choices[0].message.content)
    except Exception as e:
        # Si el modelo falla o no regresa un json válido, se manda a knowledge por default
        decision = {"agent": "knowledge", "reason": "fallback: " + str(e)}

    if decision.get("agent") not in ("knowledge", "support"):
        decision["agent"] = "knowledge"
    return decision


# ============================== CICLO DE HERRAMIENTAS ==============================
# El modelo pide herramientas, se ejecutan aquí y se le regresa el resultado, hasta que ya conteste (máximo 4 vueltas)
def ciclo_herramientas(system, mensaje, esquemas, funciones, max_vueltas=4):
    mensajes = [{"role": "system", "content": system}, {"role": "user", "content": mensaje}]
    llamadas = []

    for _ in range(max_vueltas):
        resp = llm.get_client().chat.completions.create(
            model=llm.CHAT_MODEL, temperature=0.2, messages=mensajes, tools=esquemas)
        msg = resp.choices[0].message

        if not msg.tool_calls:  # Ya no pidió herramientas, entonces esta es la respuesta final
            return msg.content, llamadas

        mensajes.append(msg.model_dump(exclude_none=True))
        for tc in msg.tool_calls:
            args = json.loads(tc.function.arguments or "{}")
            try:
                resultado = funciones[tc.function.name](**args)
            except Exception as e:
                resultado = {"error": str(e)}  # Si una herramienta truena, no debe tronar todo el agente
            llamadas.append({"tool": tc.function.name, "args": args})
            mensajes.append({"role": "tool", "tool_call_id": tc.id,
                             "content": json.dumps(resultado, ensure_ascii=False)})

    return "Sorry, I couldn't complete that request.", llamadas


def schema(nombre, descripcion, propiedades, requeridos=None):
    # Función para no repetir toda la estructura que pide OpenAI en cada herramienta
    return {"type": "function", "function": {
        "name": nombre, "description": descripcion,
        "parameters": {"type": "object", "properties": propiedades, "required": requeridos or []}}}


# ============================== AGENTE DE CONOCIMIENTO ==============================
KNOWLEDGE_PROMPT = """You are the Knowledge Agent of Getnet's merchant support assistant.
- For Getnet questions, answer ONLY with the provided context. Cite sources like [1], [2].
- If the context doesn't contain the answer, say you don't know and suggest the Getnet Brasil app
  or the Central de Relacionamento. Never invent fees, prices or deadlines.
- For general questions (weather, exchange rates, news) use your tools and mention the source and date.
- Answer in the same language as the user, in 60-150 words, with bullets for steps."""

WEB_SCHEMAS = [
    schema("get_weather", "Weather forecast for a city.",
           {"city": {"type": "string"}, "day": {"type": "string", "enum": ["today", "tomorrow"]}}, ["city"]),
    schema("get_exchange_rate", "Latest exchange rate between two currencies (ISO codes).",
           {"base": {"type": "string", "description": "e.g. EUR"},
            "quote": {"type": "string", "description": "e.g. BRL"}}, ["base"]),
    schema("web_search", "General web search for current facts not covered by other tools.",
           {"query": {"type": "string"}}, ["query"]),
]
WEB_FUNCS = {"get_weather": tools.get_weather,
             "get_exchange_rate": tools.get_exchange_rate,
             "web_search": tools.web_search}


def knowledge_agent(mensaje):
    # Primero se buscan los chunks de la base de conocimiento más parecidos a la pregunta (RAG)
    resultados = search(mensaje)
    contexto = ""
    for i, r in enumerate(resultados, 1):
        contexto += "[" + str(i) + "] (" + r["url"] + ")\n" + r["text"] + "\n\n"

    respuesta, llamadas = ciclo_herramientas(KNOWLEDGE_PROMPT, "Context:\n" + contexto + "\nQuestion: " + mensaje,
                                             WEB_SCHEMAS, WEB_FUNCS)

    # Solo se muestran como fuente las que sí se parecían a la pregunta
    fuentes = sorted({r["url"] for r in resultados if r["score"] > 0.3})
    return {"agent": "knowledge", "answer": respuesta, "sources": fuentes, "tool_calls": llamadas}


# ============================== AGENTE DE SOPORTE ==============================
SUPPORT_PROMPT = """You are the Customer Support Agent of Getnet's merchant support assistant.
You are already authenticated as the merchant; tools only return THIS merchant's data.
1. Call the tools you need (as few as possible).
2. Answer strictly from tool results: give concrete dates, amounts (R$), terminal serials, codes.
3. Always end with clear next steps.
If a tool returns account_not_found, apologise and suggest contacting a human agent.
Answer in the same language as the user, in 60-150 words."""

# IMPORTANTE: ninguna herramienta tiene user_id como parámetro, así el modelo no puede pedir datos de otro comercio
SUPPORT_SCHEMAS = [
    schema("get_settlement_schedule", "When the merchant's approved sales of a day will be deposited.",
           {"sales_date": {"type": "string", "enum": ["yesterday", "today"]}}),
    schema("get_recent_transactions", "Merchant's recent transactions, optionally only declined ones.",
           {"status": {"type": "string", "enum": ["approved", "declined"]}}),
    schema("get_terminal_status", "Connectivity status of the merchant's card machines.", {}),
]


def support_agent(mensaje, user_id):
    # Con partial se "amarra" el user_id a cada función desde el servidor, el modelo nunca lo elige
    funciones = {
        "get_settlement_schedule": partial(tools.get_settlement_schedule, user_id),
        "get_recent_transactions": partial(tools.get_recent_transactions, user_id),
        "get_terminal_status": partial(tools.get_terminal_status, user_id),
    }
    respuesta, llamadas = ciclo_herramientas(SUPPORT_PROMPT, mensaje, SUPPORT_SCHEMAS, funciones)
    return {"agent": "support", "answer": respuesta, "sources": [], "tool_calls": llamadas}
