PYTHON ?= python3
export PYTHONPATH := src

.PHONY: help deck deck-fast card play watch loop heartbeat heartbeat-stop journal test lint serve clean clean-cache

help:
	@echo "Daten"
	@echo "  make deck        Kartendaten aus offenen Quellen bauen (~25 min)"
	@echo "  make deck-fast   dasselbe ohne GDELT (~1 min, ohne Polarisierung)"
	@echo "  make card N=Musk einzelne Karte prüfen"
	@echo ""
	@echo "Spiel"
	@echo "  make play        eine Partie im Terminal"
	@echo "  make watch       Bot gegen Bot, nur zuschauen"
	@echo ""
	@echo "Weiterentwicklung"
	@echo "  make loop        einmal nach Verbesserungen suchen"
	@echo "  make heartbeat   dauerhaft weiterentwickeln, bis du stoppst"
	@echo "  make heartbeat-stop  anhalten"
	@echo "  make journal     was der Herzschlag getan hat"
	@echo ""
	@echo "Entwicklung"
	@echo "  make test        Testsuite, ohne Netz"
	@echo "  make lint        ruff, falls installiert"
	@echo "  make serve       Kartenvorschau auf http://localhost:8000"
	@echo "  make clean-cache API-Cache verwerfen"

deck:
	$(PYTHON) -m powerdeck deck

deck-fast:
	$(PYTHON) -m powerdeck deck --no-gdelt

card:
	$(PYTHON) -m powerdeck deck --only "$(N)" --out /tmp/powerdeck-card.json

play:
	$(PYTHON) -m powerdeck play

watch:
	$(PYTHON) -m powerdeck play --auto

loop:
	$(PYTHON) -m powerdeck loop

heartbeat:
	$(PYTHON) -m powerdeck heartbeat

heartbeat-stop:
	$(PYTHON) -m powerdeck heartbeat --stop

journal:
	$(PYTHON) -m powerdeck heartbeat --journal 40

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
