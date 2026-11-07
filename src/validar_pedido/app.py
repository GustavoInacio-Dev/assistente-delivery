import json
import os
import re
from datetime import datetime, timezone
from decimal import Decimal

import boto3

from shared.errors import PedidoInvalidoError

CEP_RE = re.compile(r"^\d{5}-\d{3}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

table = boto3.resource("dynamodb").Table(os.environ["TABLE_NAME"])


def validate(pedido: dict) -> None:
    cliente = pedido.get("cliente") or {}
    endereco = pedido.get("endereco") or {}

    if not cliente.get("nome"):
        raise PedidoInvalidoError("nome do cliente é obrigatório")
    if not EMAIL_RE.match(cliente.get("email") or ""):
        raise PedidoInvalidoError("e-mail inválido")
    if not pedido.get("itens"):
        raise PedidoInvalidoError("pedido sem itens")
    for item in pedido["itens"]:
        if not item.get("quantidade", 0) > 0:
            raise PedidoInvalidoError(f"quantidade inválida no item {item.get('sku')}")
        if not item.get("preco", 0) > 0:
            raise PedidoInvalidoError(f"preço inválido no item {item.get('sku')}")
    if not all(endereco.get(campo) for campo in ("rua", "numero", "cidade")):
        raise PedidoInvalidoError("endereço incompleto")
    if not CEP_RE.match(endereco.get("cep") or ""):
        raise PedidoInvalidoError("CEP deve estar no formato 00000-000")
    if not (pedido.get("pagamento") or {}).get("token"):
        raise PedidoInvalidoError("pagamento sem token")


def handler(event: dict, context) -> dict:
    """Grava o pedido como RECEBIDO, valida e marca como VALIDADO."""
    pedido_id = event["pedido_id"]
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")

    # dynamo não aceita float, então converte tudo pra Decimal antes de gravar
    dados = json.loads(json.dumps(event), parse_float=Decimal)
    table.put_item(Item={
        "pedido_id": pedido_id,
        "status": "RECEBIDO",
        "cliente": dados.get("cliente"),
        "itens": dados.get("itens"),
        "endereco": dados.get("endereco"),
        "historico_status": [{"status": "RECEBIDO", "em": now}],
        "criado_em": now,
        "atualizado_em": now,
    })

    validate(event)

    total = sum(Decimal(str(i["preco"])) * i["quantidade"] for i in event["itens"])
    total = total.quantize(Decimal("0.01"))

    table.update_item(
        Key={"pedido_id": pedido_id},
        UpdateExpression="SET #s = :s, #t = :t, atualizado_em = :now, "
                         "historico_status = list_append(historico_status, :h)",
        # status e total são palavras reservadas no dynamo
        ExpressionAttributeNames={"#s": "status", "#t": "total"},
        ExpressionAttributeValues={
            ":s": "VALIDADO",
            ":t": total,
            ":now": now,
            ":h": [{"status": "VALIDADO", "em": now}],
        },
    )

    # Decimal não serializa na saída da lambda
    return {"pedido_id": pedido_id, "total": float(total)}
