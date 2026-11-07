import pytest

from processar_pagamento.app import GatewayTimeoutError, handler
from shared.errors import PagamentoRecusadoError


def test_pagamento_aprovado():
    result = handler({"pagamento": {"token": "tok_teste_aprovado"}}, None)

    assert result["status_pagamento"] == "APROVADO"
    assert result["transacao_id"].startswith("txn_")


def test_pagamento_recusado():
    with pytest.raises(PagamentoRecusadoError):
        handler({"pagamento": {"token": "tok_teste_recusado"}}, None)


def test_timeout_falha_nas_primeiras_tentativas_e_depois_aprova():
    event = {"pagamento": {"token": "tok_teste_timeout"}}

    for tentativa in (0, 1):
        with pytest.raises(GatewayTimeoutError):
            handler({**event, "tentativa": tentativa}, None)

    assert handler({**event, "tentativa": 2}, None)["status_pagamento"] == "APROVADO"
