CREATE TABLE public.transactions (
	transaction_id varchar NULL,
	client_id varchar NOT NULL,
	transaction_revenue float8 NULL,
	payment_method_name varchar NULL,
	payment_location varchar NULL,
	payment_product varchar NULL,
	transaction_timestamp timestamptz NULL
);