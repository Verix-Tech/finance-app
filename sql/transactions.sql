CREATE TABLE public.transactions (
	internal_transaction_id varchar NOT NULL,
	transaction_id int4 NOT NULL,
	client_id varchar NOT NULL,
	transaction_revenue float8 NULL,
	payment_method_name varchar NULL,
	payment_location varchar NULL,
	payment_product varchar NULL,
	transaction_timestamp timestamptz NOT NULL
);