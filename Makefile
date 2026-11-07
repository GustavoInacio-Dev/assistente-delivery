STACK ?= assistente-delivery
EVENT ?= events/pedido_aprovado.json
API_URL = $(shell aws cloudformation describe-stacks --stack-name $(STACK) \
	--query "Stacks[0].Outputs[?OutputKey=='ApiUrl'].OutputValue" --output text)

.PHONY: test build deploy invoke delete

test:
	pytest --cov=src --cov-report=term-missing

build:
	sam validate --lint
	sam build

deploy: build
	sam deploy

# uso: make invoke EVENT=events/pedido_timeout.json
invoke:
	curl -s -X POST "$(API_URL)/pedidos" -H "Content-Type: application/json" -d @$(EVENT)

delete:
	sam delete --stack-name $(STACK)
