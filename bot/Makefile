include .env
export

run:
	PYTHONPATH=.. watchmedo auto-restart --directory=. --pattern=*.py --recursive -- python main.py

run_debug:
	PYTHONPATH=.. python main.py

run_test:
	python test_accuracy.py

debug_config:
	python config/config.py