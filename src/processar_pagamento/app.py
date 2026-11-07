import uuid

from shared.errors import PagamentoRecusadoError


class GatewayTimeoutError(Exception):
    pass


def handler(event: dict, context) -> dict:
    """Gateway de pagamento simulado, o resultado depende do token."""
    # TODO: trocar pelo gateway real depois
    token = event["pagamento"]["token"]
    tentativa = event.get("tentativa", 0)

    # token fake pra testar o retry da step function: falha nas 2 primeiras e passa na 3a
    if token == "tok_teste_timeout" and tentativa < 2:
        raise GatewayTimeoutError(f"gateway não respondeu (tentativa {tentativa})")

    if token not in ("tok_teste_aprovado", "tok_teste_timeout"):
        raise PagamentoRecusadoError("pagamento recusado pela operadora")

    return {
        "transacao_id": f"txn_{uuid.uuid4().hex[:12]}",
        "status_pagamento": "APROVADO",
    }
