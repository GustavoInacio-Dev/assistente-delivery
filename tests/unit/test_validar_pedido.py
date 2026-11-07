import importlib
from decimal import Decimal

import pytest

from shared.errors import PedidoInvalidoError
from validar_pedido import app as validar_app


@pytest.fixture
def app(table):
    # o módulo cria o client no import, então recarrega depois do mock da aws subir
    return importlib.reload(validar_app)


def test_valida_e_grava_pedido(app, table, pedido):
    result = app.handler(pedido, None)

    assert result == {"pedido_id": "pedido-123", "total": 78.9}
    item = table.get_item(Key={"pedido_id": "pedido-123"})["Item"]
    assert item["status"] == "VALIDADO"
    assert item["total"] == Decimal("78.90")
    assert [h["status"] for h in item["historico_status"]] == ["RECEBIDO", "VALIDADO"]


@pytest.mark.parametrize("quebra, erro", [
    (lambda p: p["endereco"].update(cep="80020310"), "CEP"),
    (lambda p: p["cliente"].update(email="ana.exemplo.com"), "e-mail"),
    (lambda p: p["itens"][0].update(quantidade=0), "quantidade"),
    (lambda p: p["itens"][0].update(preco=-1), "preço"),
    (lambda p: p.update(itens=[]), "sem itens"),
], ids=["cep", "email", "quantidade", "preco", "sem_itens"])
def test_recusa_pedido_invalido(app, table, pedido, quebra, erro):
    quebra(pedido)

    with pytest.raises(PedidoInvalidoError, match=erro):
        app.handler(pedido, None)

    # fica gravado como RECEBIDO pra step function marcar como CANCELADO depois
    item = table.get_item(Key={"pedido_id": "pedido-123"})["Item"]
    assert item["status"] == "RECEBIDO"
