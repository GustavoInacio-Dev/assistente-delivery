import importlib
import json
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from api import app as api_app


@pytest.fixture
def app(table, monkeypatch):
    importlib.reload(api_app)
    monkeypatch.setattr(api_app, "sfn", MagicMock())
    api_app.sfn.start_execution.return_value = {"executionArn": "arn:execucao-teste"}
    return api_app


def test_post_inicia_execucao(app, pedido):
    del pedido["pedido_id"]

    result = app.handler({"routeKey": "POST /pedidos", "body": json.dumps(pedido)}, None)

    assert result["statusCode"] == 202
    body = json.loads(result["body"])
    assert body["executionArn"] == "arn:execucao-teste"
    kwargs = app.sfn.start_execution.call_args.kwargs
    assert kwargs["name"] == body["pedido_id"]
    assert json.loads(kwargs["input"])["pedido_id"] == body["pedido_id"]


@pytest.mark.parametrize("body", [None, "não é json", "[1, 2]"])
def test_post_com_corpo_invalido(app, body):
    result = app.handler({"routeKey": "POST /pedidos", "body": body}, None)

    assert result["statusCode"] == 400
    app.sfn.start_execution.assert_not_called()


def test_get_retorna_status(app, table):
    table.put_item(Item={"pedido_id": "pedido-123", "status": "PAGO", "total": Decimal("78.90"), "cliente": {}})

    result = app.handler({"routeKey": "GET /pedidos/{id}", "pathParameters": {"id": "pedido-123"}}, None)

    assert result["statusCode"] == 200
    assert json.loads(result["body"]) == {"pedido_id": "pedido-123", "status": "PAGO", "total": "78.90"}


def test_get_pedido_inexistente(app):
    result = app.handler({"routeKey": "GET /pedidos/{id}", "pathParameters": {"id": "nao-existe"}}, None)

    assert result["statusCode"] == 404
