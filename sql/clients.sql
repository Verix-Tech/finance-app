CREATE TABLE clients (
	client_id varchar NULL,
	"name" varchar NULL,
	phone varchar NULL,
	created_at varchar NULL,
	updated_at varchar NULL,
	subscription_timestamp timestamptz NULL,
	subscribed bool NULL,
	CONSTRAINT clients_unique UNIQUE (client_id)
);