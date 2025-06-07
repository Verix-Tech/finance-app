CREATE TABLE public.clients (
	client_id varchar NULL,
	"name" varchar NULL,
	phone varchar NULL,
	created_at varchar NULL,
	updated_at varchar NULL,
	subscribed bool NULL,
	subs_start_timestamp timestamptz NULL,
	subs_end_timestamp timestamptz NULL,
	CONSTRAINT clients_unique UNIQUE (client_id)
);