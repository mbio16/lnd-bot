-- public.channels definition

-- Drop table

-- DROP TABLE public.channels;

CREATE TABLE public.channels (
	channel_id int8 NOT NULL,
	remote_public_key varchar NULL,
	alias varchar NULL,
	CONSTRAINT channels_pk PRIMARY KEY (channel_id)
);
CREATE INDEX channels_alias_idx ON public.channels USING btree (alias);
CREATE INDEX channels_remote_public_key_idx ON public.channels USING btree (remote_public_key);


-- public.invoices definition

-- Drop table

-- DROP TABLE public.invoices;

CREATE TABLE public.invoices (
	id serial4 NOT NULL,
	memo varchar NULL,
	value int8 NULL,
	value_milisats int8 NULL,
	settled bool NULL,
	creation_date timestamp NULL,
	settle_date timestamp NULL,
	state varchar NULL,
	expiry int8 NULL,
	CONSTRAINT invoices_pk PRIMARY KEY (id)
);
CREATE INDEX invoices_creation_date_idx ON public.invoices USING btree (creation_date DESC);
CREATE INDEX invoices_settle_date_idx ON public.invoices USING btree (settle_date DESC);
CREATE INDEX invoices_settled_idx ON public.invoices USING btree (settled);
CREATE INDEX invoices_state_idx ON public.invoices USING btree (state);
CREATE INDEX invoices_value_idx ON public.invoices USING btree (value);


-- public.log_type definition

-- Drop table

-- DROP TABLE public.log_type;

CREATE TABLE public.log_type (
	id serial4 NOT NULL,
	"type" varchar NOT NULL,
	CONSTRAINT log_type_pk PRIMARY KEY (id)
);


-- public.payments definition

-- Drop table

-- DROP TABLE public.payments;

CREATE TABLE public.payments (
	id serial4 NOT NULL,
	value int8 NULL,
	value_milisat int8 NULL,
	creation_date timestamp NULL,
	fee int8 NULL,
	fee_milisat int8 NULL,
	status varchar NULL,
	CONSTRAINT payments_pk PRIMARY KEY (id)
);
CREATE INDEX payments_creation_date_idx ON public.payments USING btree (creation_date);
CREATE INDEX payments_id_idx ON public.payments USING btree (id);
CREATE INDEX payments_value_idx ON public.payments USING btree (value);


-- public.logs definition

-- Drop table

-- DROP TABLE public.logs;

CREATE TABLE public.logs (
	id serial4 NOT NULL,
	log_type int2 NOT NULL,
	log_timestamp timestamp NOT NULL,
	message varchar NULL,
	CONSTRAINT logs_pk PRIMARY KEY (id),
	CONSTRAINT logs_fk FOREIGN KEY (log_type) REFERENCES public.log_type(id)
);
CREATE INDEX logs_log_timestamp_idx ON public.logs USING btree (log_timestamp DESC);
CREATE INDEX logs_log_type_idx ON public.logs USING btree (log_type);


-- public.routing definition

-- Drop table

-- DROP TABLE public.routing;

CREATE TABLE public.routing (
	unix_timestamp timestamp NOT NULL,
	chan_id_in int8 NOT NULL,
	chan_id_out int8 NOT NULL,
	amount_in_sats int8 NOT NULL,
	amount_out_sats int8 NOT NULL,
	fee_sats int8 NOT NULL,
	fee_milisats int8 NOT NULL,
	amt_in_milisats int8 NOT NULL,
	amount_out_milisats int8 NOT NULL,
	id serial4 NOT NULL,
	CONSTRAINT routing_pk PRIMARY KEY (id),
	CONSTRAINT routing_fk FOREIGN KEY (chan_id_in) REFERENCES public.channels(channel_id),
	CONSTRAINT routing_fk2 FOREIGN KEY (chan_id_out) REFERENCES public.channels(channel_id)
);
CREATE INDEX routing_chan_id_in_idx ON public.routing USING btree (chan_id_in);
CREATE INDEX routing_chan_id_out_idx ON public.routing USING btree (chan_id_out);
CREATE INDEX routing_fee_milisats_idx ON public.routing USING btree (fee_milisats);
CREATE INDEX routing_fee_sats_idx ON public.routing USING btree (fee_sats);
CREATE INDEX routing_id_idx ON public.routing USING btree (id);
CREATE INDEX routing_unix_idx ON public.routing USING btree (unix_timestamp DESC);


-- VIEWS
-- public.log_view source

CREATE OR REPLACE VIEW public.log_view
AS SELECT logs.id,
    logs.log_type,
    log_type.type,
    logs.log_timestamp,
    logs.message
   FROM logs
     JOIN log_type ON logs.log_type = log_type.id;


-- public.routing_completed source

CREATE OR REPLACE VIEW public.routing_completed
AS SELECT routing.unix_timestamp,
    routing.chan_id_in,
    chan1.remote_public_key AS public_key_in,
    chan1.alias AS alias_in,
    routing.chan_id_out,
    chan2.remote_public_key AS public_key_out,
    chan2.alias AS alias_out,
    routing.amount_in_sats,
    routing.amount_out_sats,
    routing.fee_sats,
    routing.fee_milisats,
    routing.amt_in_milisats,
    routing.amount_out_milisats,
    routing.id
   FROM routing
     LEFT JOIN channels chan1 ON routing.chan_id_in = chan1.channel_id
     LEFT JOIN channels chan2 ON routing.chan_id_out = chan2.channel_id;


CREATE TABLE public.channel_backup (
	id serial NOT NULL,
	date_creation timestamp without time zone NULL,
	sha256 varchar NULL,
	"data" json NULL,
	CONSTRAINT channel_bc_pk PRIMARY KEY (id)
);
CREATE INDEX channel_backup_id_idx ON public.channel_backup (id);
CREATE INDEX channel_backup_date_creation_idx ON public.channel_backup (date_creation);
CREATE INDEX channel_backup_sha256_idx ON public.channel_backup (sha256);


--INSERT to DEBUG level

INSERT INTO public.log_type ("type") VALUES
	 ('DEBUG'),
	 ('INFO'),
	 ('WARNING'),
	 ('ERROR');