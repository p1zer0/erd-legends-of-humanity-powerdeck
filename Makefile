PYTHON ?= python3
export PYTHONPATH := src

.PHONY: help deck deck-fast card test lint serve clean clean-cache

help:
	@echo "make deck        volles Deck bauen (~25 min, GDELT drosselt)"
	@echo "make deck-fast   Deck ohne GDELT (~1 min, ohne Polarisierung)"
	@echo "make card N=Musk einzelne Karte testen"
	@echo "make test        Testsuite (kein Netz nötig)"
	@echo "make lint        ruff, falls installiert"
	@echo "make serve       Vorschau auf http://localhost:8000"
	@echo "make clean-cache API-Cache verwerfen"

deck:
	$(PYTHON) -m powerdeck

deck-fast:
	$(PYTHON) -m powerdeck --no-gdelt

card:
	$(PYTHON) -m powerdeck --only "$(N)" --out /tmp/powerdeck-card.json

test:
	$(PYTHON) -m unittest discover -s tests

lint:
	@ruff check . || echo "ruff nicht installiert – uebersprungen"

serve:
	@echo "http://localhost:8000"
	@cd public && $(PYTHON) -m http.server 8000

clean-cache:
	rm -rf .cache

clean: clean-cache
	rm -rf build dist src/*.egg-info
	find . -name __pycache__ -type d -exec rm -rf {} +
