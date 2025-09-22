.PHONY: setup run-api run-worker run-web stop-api stop-worker stop-web restart-api restart-worker db-upgrade fmt

setup:
	python -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt


run-api:
	bash -c 'set -a; [ -f .env ] && source .env; set +a; . .venv/bin/activate && uvicorn services.api.main:app --reload --port 8080'


run-worker:
	bash -c 'set -a; [ -f .env ] && source .env; set +a; . .venv/bin/activate && uvicorn services.worker.main:app --reload --port 8081'

run-web:
	cd apps/web && npm run dev

stop-api:
	-pkill -f "uvicorn services.api.main:app" || true
	-@lsof -ti:8080 | xargs -r kill -9
	-@fuser -k 8080/tcp || true

stop-worker:
	-pkill -f "uvicorn services.worker.main:app" || true
	-@lsof -ti:8081 | xargs -r kill -9
	-@fuser -k 8081/tcp || true

stop-web:
	-@lsof -ti:3000 | xargs -r kill -9
	-@fuser -k 3000/tcp || true

restart-api: stop-api
	$(MAKE) run-api

restart-worker: stop-worker
	$(MAKE) run-worker

db-upgrade:
	alembic upgrade head
