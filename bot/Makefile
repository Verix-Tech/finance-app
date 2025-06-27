include .env
export

run:
	watchmedo auto-restart --directory=. --pattern=*.py --recursive -- python main.py

run_debug:
	python main.py

run_test:
	python test_accuracy.py

debug_config:
	python config/config.py