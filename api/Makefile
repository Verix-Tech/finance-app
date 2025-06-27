-include .env
export

# Create tables on database
create_tables:
	python database_manager/manage_tables.py create_tables

# Drop tables on database
drop_tables:
	python database_manager/manage_tables.py drop_tables

# Create user on database
create_user:
	python database_manager/manage_tables.py create_users

# Create payment methods on database
create_payment_methods:
	python database_manager/manage_tables.py create_payment_methods

# Create payment categories on database
create_payment_categories:
	python database_manager/manage_tables.py create_payment_categories

# Debugging
workers_debug:
	python workers/main.py

utils_debug:
	python utils/utils.py

# Start Celery worker
start_celery:
	watchmedo auto-restart --directory=./ --pattern=*.py --recursive -- celery -A workers.main.app worker --concurrency=1 --loglevel=INFO --include=tests.test_tasks

# Test Redis and Celery connection
test_celery_redis_connection:
	python tests/test_redis_connection.py

# Start API
start_api: create_tables create_user create_payment_methods create_payment_categories
	uvicorn main:app --host 0.0.0.0 --port 8000 --reload

