import json
import os
import uuid

import boto3

sfn = boto3.client("stepfunctions")
table = boto3.resource("dynamodb").Table(os.environ["TABLE_NAME"])

CAMPOS_RESPOSTA = (
    "pedido_id", "status", "total", "historico_status",
    "mensagem_personalizada", "sugestoes", "motivo_cancelamento",
)


def response(status: int, body: dict) -> dict:
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json"},
        # default=str porque o total volta do dynamo como Decimal
        "body": json.dumps(body, ensure_ascii=False, default=str),
    }


def handler(event: dict, context) -> dict:
    """POST /pedidos inicia o fluxo e GET /pedidos/{id} consulta o status."""
    if event["routeKey"] == "POST /pedidos":
        try:
            pedido = json.loads(event.get("body") or "")
        except json.JSONDecodeError:
            pedido = None
        if not isinstance(pedido, dict):
            return response(400, {"erro": "o corpo precisa ser um JSON com o pedido"})

        pedido["pedido_id"] = str(uuid.uuid4())
        # execução com o mesmo nome do pedido pra achar fácil no console
        execution = sfn.start_execution(
            stateMachineArn=os.environ["STATE_MACHINE_ARN"],
            name=pedido["pedido_id"],
            input=json.dumps(pedido),
        )
        return response(202, {"pedido_id": pedido["pedido_id"], "executionArn": execution["executionArn"]})

    item = table.get_item(Key={"pedido_id": event["pathParameters"]["id"]}).get("Item")
    if not item:
        return response(404, {"erro": "pedido não encontrado"})
    return response(200, {campo: item[campo] for campo in CAMPOS_RESPOSTA if campo in item})
