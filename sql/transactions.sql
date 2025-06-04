CREATE TABLE transactions (
	transaction_timestamp timestamptz NULL,
	client_id varchar NOT NULL,
	transaction_id varchar NULL,
	transaction_revenue float8 NULL,
	payment_method_id varchar NULL,
	payment_name varchar NULL
);