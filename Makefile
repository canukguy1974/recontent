    .PHONY: setup run-api run-worker db-upgrade fmt

    setup:
	python -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt

    run-api:
	. .venv/bin/activate && uvicorn services.api.main:app --reload --port 8080

    run-worker:
	. .venv/bin/activate && uvicorn services.worker.main:app --reload --port 8081

    db-upgrade:
	alembic upgrade head
