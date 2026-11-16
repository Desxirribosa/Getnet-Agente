from types import SimpleNamespace

from app import agents, llm


class ClienteFalso:
    # Simula el cliente de OpenAI y siempre regresa el mismo texto, así no se gasta API en los tests
    def __init__(self, contenido):
        msg = SimpleNamespace(content=contenido, tool_calls=None)
        resp = SimpleNamespace(choices=[SimpleNamespace(message=msg)])
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=lambda **kw: resp))


def test_router_lee_el_json(monkeypatch):
    monkeypatch.setattr(llm, "get_client", lambda: ClienteFalso('{"agent": "support", "reason": "own data"}'))
    assert agents.route("When will yesterday's sales be deposited?")["agent"] == "support"


def test_router_si_falla_manda_a_knowledge(monkeypatch):
    monkeypatch.setattr(llm, "get_client", lambda: ClienteFalso("esto no es json"))
    assert agents.route("hello")["agent"] == "knowledge"


def test_herramientas_de_soporte_no_piden_user_id():
    for s in agents.SUPPORT_SCHEMAS:
        assert "user_id" not in s["function"]["parameters"]["properties"]
