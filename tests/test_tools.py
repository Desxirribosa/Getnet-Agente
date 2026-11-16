import datetime as dt

from app.tools import add_business_days, get_recent_transactions, get_settlement_schedule, get_terminal_status

SABADO = dt.date(2026, 11, 14)  # Se fija la fecha para que los tests siempre den lo mismo


def test_dias_habiles_brincan_fin_de_semana():
    assert add_business_days(dt.date(2026, 11, 13), 1) == dt.date(2026, 11, 16)  # Viernes -> lunes


def test_fechas_de_deposito():
    out = get_settlement_schedule("cliente1988", "yesterday", today=SABADO)
    fechas = {d["type"]: d["deposit_date"] for d in out["deposits"]}
    # Débito 1 día hábil, crédito 2 días hábiles y Pix el mismo día
    assert fechas == {"debit": "2026-11-16", "credit": "2026-11-17", "pix": "2026-11-13"}


def test_transacciones_rechazadas():
    out = get_recent_transactions("cliente1988", status="declined", today=SABADO)
    assert out["transactions"][0]["code"] == "51"


def test_usuario_que_no_existe():
    assert get_terminal_status("nadie") == {"error": "account_not_found"}
