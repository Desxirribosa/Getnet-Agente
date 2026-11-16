import datetime as dt
import json
from pathlib import Path

import requests
from bs4 import BeautifulSoup

# Se cargan los comercios de prueba desde el json, esto simula la base de datos de Getnet, cuyos datos fueron inventados.
USUARIOS = json.loads(Path("data/users.json").read_text(encoding="utf-8"))

# Diccionario con los códigos de rechazo más comunes y lo que significan
CODIGOS_RECHAZO = {
    "05": "Not authorized by the issuer. Ask for another card.",
    "51": "Insufficient funds. Ask for another card or Pix.",
    "54": "Expired card.",
    "55": "Wrong PIN.",
    "91": "Issuer unavailable / communication timeout. Check connection and retry.",
}


# ==================== HERRAMIENTAS WEB (Agente de conocimiento) ====================

def get_weather(city: str, day: str = "tomorrow") -> dict:
    # Primero se buscan las coordenadas de la ciudad y luego el pronóstico con esas coordenadas (open-meteo no pide API key)
    try:
        geo = requests.get("https://geocoding-api.open-meteo.com/v1/search",
                           params={"name": city, "count": 1}, timeout=10).json()
        if not geo.get("results"):
            return {"error": f"city not found: {city}"}
        lugar = geo["results"][0]

        pronostico = requests.get("https://api.open-meteo.com/v1/forecast", params={
            "latitude": lugar["latitude"], "longitude": lugar["longitude"], "timezone": "auto",
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max"}, timeout=10).json()

        dias = pronostico["daily"]
        i = 1 if day == "tomorrow" else 0  # La posición 0 es hoy y la 1 es mañana
        return {"city": lugar["name"], "date": dias["time"][i],
                "max_c": dias["temperature_2m_max"][i], "min_c": dias["temperature_2m_min"][i],
                "rain_prob": dias["precipitation_probability_max"][i], "source": "https://open-meteo.com"}
    except Exception as e:
        return {"error": str(e)}


def get_exchange_rate(base: str, quote: str = "BRL") -> dict:
    # Frankfurter da el tipo de cambio del Banco Central Europeo, tampoco pide API key
    base = base.upper()
    quote = quote.upper()
    try:
        r = requests.get("https://api.frankfurter.dev/v1/latest",
                         params={"base": base, "symbols": quote}, timeout=10).json()
        return {"base": base, "quote": quote, "rate": r["rates"][quote],
                "date": r["date"], "source": "https://www.frankfurter.app"}
    except Exception as e:
        return {"error": str(e)}


def web_search(query: str) -> dict:
    # Búsqueda sencilla en la versión html de DuckDuckGo, solo se toman los primeros 5 resultados
    try:
        r = requests.post("https://html.duckduckgo.com/html/", data={"q": query},
                          headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        resultados = []
        for a in soup.select(".result__a")[:5]:
            resultados.append({"title": a.get_text(strip=True), "url": a.get("href")})
        if not resultados:
            return {"error": "no results"}
        return {"results": resultados}
    except Exception as e:
        return {"error": str(e)}


# ==================== HERRAMIENTAS DE SOPORTE (Agente de soporte) ====================

def add_business_days(inicio: dt.date, dias: int) -> dt.date:
    # Se avanza día por día y solo se cuentan los días hábiles (lunes a viernes)
    fecha = inicio
    while dias > 0:
        fecha += dt.timedelta(days=1)
        if fecha.weekday() < 5:  # weekday() regresa 0 = lunes ... 4 = viernes
            dias -= 1
    return fecha


def transacciones_con_fecha(usuario, hoy):
    # En el json las transacciones tienen "day_offset" (-1 = ayer, 0 = hoy), aquí se convierte a fecha real
    lista = []
    for t in usuario["transactions"]:
        fecha = hoy + dt.timedelta(days=t["day_offset"])
        lista.append({**t, "date": fecha.isoformat()})
    return lista


def get_settlement_schedule(user_id, sales_date="yesterday", today=None):
    usuario = USUARIOS.get(user_id)
    if not usuario:
        return {"error": "account_not_found"}

    hoy = today or dt.date.today()
    if sales_date == "yesterday":
        dia_venta = hoy - dt.timedelta(days=1)
    else:
        dia_venta = hoy

    depositos = []
    for t in transacciones_con_fecha(usuario, hoy):
        # Solo cuentan las ventas aprobadas del día que se pidió
        if t["date"] != dia_venta.isoformat() or t["status"] != "approved":
            continue

        # Pix cae el mismo día, débito y crédito dependen del plan del comercio (en días hábiles)
        if t["type"] == "pix":
            fecha_deposito = dia_venta
        elif t["type"] == "debit":
            fecha_deposito = add_business_days(dia_venta, usuario["plan"]["debit_days"])
        else:
            fecha_deposito = add_business_days(dia_venta, usuario["plan"]["credit_days"])

        depositos.append({"transaction": t["id"], "type": t["type"], "amount": t["amount"],
                          "deposit_date": fecha_deposito.isoformat()})

    return {"sales_date": dia_venta.isoformat(), "bank": usuario["bank"], "deposits": depositos}


def get_recent_transactions(user_id, status=None, today=None):
    usuario = USUARIOS.get(user_id)
    if not usuario:
        return {"error": "account_not_found"}

    transacciones = transacciones_con_fecha(usuario, today or dt.date.today())
    if status:  # Si se pide un estado en específico (approved / declined) se filtra
        transacciones = [t for t in transacciones if t["status"] == status]

    # A las rechazadas se les agrega qué significa su código para que el agente lo pueda explicar
    for t in transacciones:
        if "code" in t:
            t["code_meaning"] = CODIGOS_RECHAZO.get(t["code"], "unknown")

    return {"transactions": transacciones}


def get_terminal_status(user_id):
    usuario = USUARIOS.get(user_id)
    if not usuario:
        return {"error": "account_not_found"}
    return {"terminals": usuario["terminals"]}
