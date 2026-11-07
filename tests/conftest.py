import json
import os
import sys
from pathlib import Path

import boto3
import pytest
from moto import mock_aws

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))

# credencial fake pra nenhum teste bater na aws de verdade
os.environ.update(
    AWS_DEFAULT_REGION="us-east-1",
    AWS_ACCESS_KEY_ID="testing",
    AWS_SECRET_ACCESS_KEY="testing",
    TABLE_NAME="Pedidos",
    BEDROCK_MODEL_ID="modelo-teste",
)


@pytest.fixture
def table():
    with mock_aws():
        yield boto3.resource("dynamodb").create_table(
            TableName="Pedidos",
            KeySchema=[{"AttributeName": "pedido_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "pedido_id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )


@pytest.fixture
def pedido():
    data = json.loads((ROOT / "events" / "pedido_aprovado.json").read_text(encoding="utf-8"))
    data["pedido_id"] = "pedido-123"
    return data
