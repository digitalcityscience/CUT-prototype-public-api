
VENV = .venv
PYTHON = $(VENV)/bin/python3
PIP = $(VENV)/bin/pip

create-env:
	python3 -m venv $(VENV)

venv: create-env
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	$(PIP) install -r requirements-dev.txt
	$(VENV)/bin/pre-commit install
	cp .env.example .env

start:
	docker compose up --build

fmt:
	black ./cut_api/ ./tests/
	isort ./cut_api/ ./tests/

lint:
	black --check ./cut_api/ ./tests/ 
	isort --check ./cut_api/ ./tests/
	flake8 ./cut_api/ ./tests/
	mypy ./cut_api/ ./tests/

test:
	$(PYTHON) -m pytest -s -v