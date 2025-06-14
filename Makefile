# Create tables on database
create_tables:
	python database_manager/manage_tables.py create_tables

# Drop tables on database
drop_tables:
	python database_manager/manage_tables.py drop_tables

# Create user on database
create_user:
	python database_manager/manage_tables.py create_users

# Start API
start_api: create_tables create_user
	uvicorn main:app --host 0.0.0.0 --port 8000 --reload
