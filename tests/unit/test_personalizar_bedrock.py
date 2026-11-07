import importlib
import json
from unittest.mock import MagicMock

import pytest

from personalizar_bedrock import app as bedrock_app

RESPOSTA_MODELO = {
    "mensagem_cliente": "Oi Ana! Sua Margherita já vai pro forno, sem cebola.",
    "sugestoes": ["Bruschetta de tomate", "Brownie vegano"],
    "tempo_estimado_min": 35,
    "observacoes_interpretadas": ["sem cebola"],
}


def converse_returning(text):
    return {"output": {"message": {"content": [{"text": text}]}}}


@pytest.fixture
def app(table, monkeypatch):
    importlib.reload(bedrock_app)
    monkeypatch.setattr(bedrock_app, "bedrock", MagicMock())
    return bedrock_app


def test_personaliza_com_resposta_do_modelo(app, table, pedido):
    # vem dentro de ```json de propósito, que é como alguns modelos respondem
    app.bedrock.converse.return_value = converse_returning(f"```json\n{json.dumps(RESPOSTA_MODELO)}\n```")

    result = app.handler(pedido, None)

    assert result == RESPOSTA_MODELO
    kwargs = app.bedrock.converse.call_args.kwargs
    assert kwargs["modelId"] == "modelo-teste"
    assert kwargs["inferenceConfig"]["temperature"] == 0.4
    item = table.get_item(Key={"pedido_id": "pedido-123"})["Item"]
    assert item["mensagem_personalizada"] == RESPOSTA_MODELO["mensagem_cliente"]
    assert item["sugestoes"] == RESPOSTA_MODELO["sugestoes"]


@pytest.mark.parametrize("configura_falha", [
    lambda bedrock: setattr(bedrock.converse, "side_effect", Exception("ThrottlingException")),
    lambda bedrock: setattr(bedrock.converse, "return_value", converse_returning("desculpe, não entendi")),
    lambda bedrock: setattr(bedrock.converse, "return_value", converse_returning('{"sugestoes": []}')),
], ids=["bedrock_fora", "texto_sem_json", "json_incompleto"])
def test_falha_do_bedrock_usa_mensagem_padrao(app, table, pedido, configura_falha):
    configura_falha(app.bedrock)

    result = app.handler(pedido, None)

    assert result == app.DEFAULT_RESPONSE
    item = table.get_item(Key={"pedido_id": "pedido-123"})["Item"]
    assert item["mensagem_personalizada"] == app.DEFAULT_RESPONSE["mensagem_cliente"]
