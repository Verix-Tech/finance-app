# Create tables on database
create_tables:
	python databaseManager/manage_tables.py create_tables

# Drop tables on database
drop_tables:
	python databaseManager/manage_tables.py drop_tables

# Start API
start_api:
	uvicorn main:app --host 0.0.0.0 --port 8000 --reload
