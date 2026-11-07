import json
import logging
import os
from datetime import datetime, timezone

import boto3

logger = logging.getLogger()

bedrock = boto3.client("bedrock-runtime")
table = boto3.resource("dynamodb").Table(os.environ["TABLE_NAME"])

SYSTEM_PROMPT = (
    "Você é um assistente simpático de um app de delivery brasileiro. "
    "Escreva em português do Brasil, com tom leve e próximo, chamando o cliente pelo nome. "
    "Responda SOMENTE com um JSON válido, sem nenhum texto fora dele, neste formato: "
    '{"mensagem_cliente": "até 3 frases", "sugestoes": ["até 2 itens que combinam com o pedido"], '
    '"tempo_estimado_min": 35, "observacoes_interpretadas": ["pedidos especiais do cliente"]}. '
    "As sugestões precisam respeitar as preferências do cliente."
)

DEFAULT_RESPONSE = {
    "mensagem_cliente": "Recebemos seu pedido e ele já está sendo preparado. Obrigado pela preferência!",
    "sugestoes": [],
    "tempo_estimado_min": 40,
    "observacoes_interpretadas": [],
}


def handler(event: dict, context) -> dict:
    """Gera a mensagem personalizada do pedido com o Bedrock."""
    pedido = {
        "nome": event["cliente"]["nome"],
        "itens": [f'{i["quantidade"]}x {i["nome"]}' for i in event["itens"]],
        "preferencias": event["cliente"].get("preferencias", []),
        "observacoes": event.get("observacoes", ""),
        "status": "PAGO",
    }

    try:
        response = bedrock.converse(
            modelId=os.environ["BEDROCK_MODEL_ID"],
            system=[{"text": SYSTEM_PROMPT}],
            messages=[{"role": "user", "content": [{"text": json.dumps(pedido, ensure_ascii=False)}]}],
            inferenceConfig={"maxTokens": 400, "temperature": 0.4},
        )
        text = response["output"]["message"]["content"][0]["text"]
        # tem modelo que devolve o json dentro de ```json, então pega só o objeto
        result = json.loads(text[text.find("{"):text.rfind("}") + 1])
        if not isinstance(result.get("mensagem_cliente"), str) or not isinstance(result.get("sugestoes"), list):
            raise ValueError(f"json fora do formato esperado: {text}")
    except Exception:
        # se o bedrock cair, segue com msg padrão, o pedido não pode travar por isso
        logger.exception("falha ao personalizar pedido %s, usando mensagem padrão", event["pedido_id"])
        result = DEFAULT_RESPONSE

    table.update_item(
        Key={"pedido_id": event["pedido_id"]},
        UpdateExpression="SET mensagem_personalizada = :m, sugestoes = :s, atualizado_em = :now",
        ExpressionAttributeValues={
            ":m": result["mensagem_cliente"],
            ":s": result["sugestoes"],
            ":now": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        },
    )
    return result
