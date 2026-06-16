-- public.actor definition

-- Drop table

-- DROP TABLE actor;

CREATE TABLE actor (
	actor_id serial4 NOT NULL,
	first_name varchar(45) NOT NULL,
	last_name varchar(45) NOT NULL,
	last_update timestamp DEFAULT now() NOT NULL,
	CONSTRAINT actor_pkey PRIMARY KEY (actor_id)
);
CREATE INDEX idx_actor_last_name ON public.actor USING btree (last_name);

-- Table Triggers

create trigger last_updated before
update
    on
    public.actor for each row execute function last_updated();


-- public.category definition

-- Drop table

-- DROP TABLE category;

CREATE TABLE category (
	category_id serial4 NOT NULL,
	"name" varchar(25) NOT NULL,
	last_update timestamp DEFAULT now() NOT NULL,
	CONSTRAINT category_pkey PRIMARY KEY (category_id)
);

-- Table Triggers

create trigger last_updated before
update
    on
    public.category for each row execute function last_updated();


-- public.country definition

-- Drop table

-- DROP TABLE country;

CREATE TABLE country (
	country_id serial4 NOT NULL,
	country varchar(50) NOT NULL,
	last_update timestamp DEFAULT now() NOT NULL,
	CONSTRAINT country_pkey PRIMARY KEY (country_id)
);

-- Table Triggers

create trigger last_updated before
update
    on
    public.country for each row execute function last_updated();


-- public."language" definition

-- Drop table

-- DROP TABLE "language";

CREATE TABLE "language" (
	language_id serial4 NOT NULL,
	"name" bpchar(20) NOT NULL,
	last_update timestamp DEFAULT now() NOT NULL,
	CONSTRAINT language_pkey PRIMARY KEY (language_id)
);

-- Table Triggers

create trigger last_updated before
update
    on
    public.language for each row execute function last_updated();


-- public.city definition

-- Drop table

-- DROP TABLE city;

CREATE TABLE city (
	city_id serial4 NOT NULL,
	city varchar(50) NOT NULL,
	country_id int2 NOT NULL,
	last_update timestamp DEFAULT now() NOT NULL,
	CONSTRAINT city_pkey PRIMARY KEY (city_id),
	CONSTRAINT fk_city FOREIGN KEY (country_id) REFERENCES country(country_id)
);
CREATE INDEX idx_fk_country_id ON public.city USING btree (country_id);

-- Table Triggers

create trigger last_updated before
update
    on
    public.city for each row execute function last_updated();


-- public.film definition

-- Drop table

-- DROP TABLE film;

CREATE TABLE film (
	film_id serial4 NOT NULL,
	title varchar(255) NOT NULL,
	description text NULL,
	release_year public."year" NULL,
	language_id int2 NOT NULL,
	rental_duration int2 DEFAULT 3 NOT NULL,
	rental_rate numeric(4, 2) DEFAULT 4.99 NOT NULL,
	length int2 NULL,
	replacement_cost numeric(5, 2) DEFAULT 19.99 NOT NULL,
	rating public.mpaa_rating DEFAULT 'G'::mpaa_rating NULL,
	last_update timestamp DEFAULT now() NOT NULL,
	special_features _text NULL,
	fulltext tsvector NOT NULL,
	CONSTRAINT film_pkey PRIMARY KEY (film_id),
	CONSTRAINT film_language_id_fkey FOREIGN KEY (language_id) REFERENCES "language"(language_id) ON DELETE RESTRICT ON UPDATE CASCADE
);
CREATE INDEX film_fulltext_idx ON public.film USING gist (fulltext);
CREATE INDEX idx_fk_language_id ON public.film USING btree (language_id);
CREATE INDEX idx_title ON public.film USING btree (title);

-- Table Triggers

create trigger film_fulltext_trigger before
insert
    or
update
    on
    public.film for each row execute function tsvector_update_trigger('fulltext', 'pg_catalog.english', 'title', 'description');
create trigger last_updated before
update
    on
    public.film for each row execute function last_updated();


-- public.film_actor definition

-- Drop table

-- DROP TABLE film_actor;

CREATE TABLE film_actor (
	actor_id int2 NOT NULL,
	film_id int2 NOT NULL,
	last_update timestamp DEFAULT now() NOT NULL,
	CONSTRAINT film_actor_pkey PRIMARY KEY (actor_id, film_id),
	CONSTRAINT film_actor_actor_id_fkey FOREIGN KEY (actor_id) REFERENCES actor(actor_id) ON DELETE RESTRICT ON UPDATE CASCADE,
	CONSTRAINT film_actor_film_id_fkey FOREIGN KEY (film_id) REFERENCES film(film_id) ON DELETE RESTRICT ON UPDATE CASCADE
);
CREATE INDEX idx_fk_film_id ON public.film_actor USING btree (film_id);

-- Table Triggers

create trigger last_updated before
update
    on
    public.film_actor for each row execute function last_updated();


-- public.film_category definition

-- Drop table

-- DROP TABLE film_category;

CREATE TABLE film_category (
	film_id int2 NOT NULL,
	category_id int2 NOT NULL,
	last_update timestamp DEFAULT now() NOT NULL,
	CONSTRAINT film_category_pkey PRIMARY KEY (film_id, category_id),
	CONSTRAINT film_category_category_id_fkey FOREIGN KEY (category_id) REFERENCES category(category_id) ON DELETE RESTRICT ON UPDATE CASCADE,
	CONSTRAINT film_category_film_id_fkey FOREIGN KEY (film_id) REFERENCES film(film_id) ON DELETE RESTRICT ON UPDATE CASCADE
);

-- Table Triggers

create trigger last_updated before
update
    on
    public.film_category for each row execute function last_updated();


-- public.inventory definition

-- Drop table

-- DROP TABLE inventory;

CREATE TABLE inventory (
	inventory_id serial4 NOT NULL,
	film_id int2 NOT NULL,
	store_id int2 NOT NULL,
	last_update timestamp DEFAULT now() NOT NULL,
	CONSTRAINT inventory_pkey PRIMARY KEY (inventory_id),
	CONSTRAINT inventory_film_id_fkey FOREIGN KEY (film_id) REFERENCES film(film_id) ON DELETE RESTRICT ON UPDATE CASCADE
);
CREATE INDEX idx_store_id_film_id ON public.inventory USING btree (store_id, film_id);

-- Table Triggers

create trigger last_updated before
update
    on
    public.inventory for each row execute function last_updated();


-- public.address definition

-- Drop table

-- DROP TABLE address;

CREATE TABLE address (
	address_id serial4 NOT NULL,
	address varchar(50) NOT NULL,
	address2 varchar(50) NULL,
	district varchar(20) NOT NULL,
	city_id int2 NOT NULL,
	postal_code varchar(10) NULL,
	phone varchar(20) NOT NULL,
	last_update timestamp DEFAULT now() NOT NULL,
	CONSTRAINT address_pkey PRIMARY KEY (address_id),
	CONSTRAINT fk_address_city FOREIGN KEY (city_id) REFERENCES city(city_id)
);
CREATE INDEX idx_fk_city_id ON public.address USING btree (city_id);

-- Table Triggers

create trigger last_updated before
update
    on
    public.address for each row execute function last_updated();


-- public.customer definition

-- Drop table

-- DROP TABLE customer;

CREATE TABLE customer (
	customer_id serial4 NOT NULL,
	store_id int2 NOT NULL,
	first_name varchar(45) NOT NULL,
	last_name varchar(45) NOT NULL,
	email varchar(50) NULL,
	address_id int2 NOT NULL,
	activebool bool DEFAULT true NOT NULL,
	create_date date DEFAULT 'now'::text::date NOT NULL,
	last_update timestamp DEFAULT now() NULL,
	active int4 NULL,
	CONSTRAINT customer_pkey PRIMARY KEY (customer_id),
	CONSTRAINT customer_address_id_fkey FOREIGN KEY (address_id) REFERENCES address(address_id) ON DELETE RESTRICT ON UPDATE CASCADE
);
CREATE INDEX idx_fk_address_id ON public.customer USING btree (address_id);
CREATE INDEX idx_fk_store_id ON public.customer USING btree (store_id);
CREATE INDEX idx_last_name ON public.customer USING btree (last_name);

-- Table Triggers

create trigger last_updated before
update
    on
    public.customer for each row execute function last_updated();


-- public.staff definition

-- Drop table

-- DROP TABLE staff;

CREATE TABLE staff (
	staff_id serial4 NOT NULL,
	first_name varchar(45) NOT NULL,
	last_name varchar(45) NOT NULL,
	address_id int2 NOT NULL,
	email varchar(50) NULL,
	store_id int2 NOT NULL,
	active bool DEFAULT true NOT NULL,
	username varchar(16) NOT NULL,
	"password" varchar(40) NULL,
	last_update timestamp DEFAULT now() NOT NULL,
	picture bytea NULL,
	CONSTRAINT staff_pkey PRIMARY KEY (staff_id),
	CONSTRAINT staff_address_id_fkey FOREIGN KEY (address_id) REFERENCES address(address_id) ON DELETE RESTRICT ON UPDATE CASCADE
);

-- Table Triggers

create trigger last_updated before
update
    on
    public.staff for each row execute function last_updated();


-- public.store definition

-- Drop table

-- DROP TABLE store;

CREATE TABLE store (
	store_id serial4 NOT NULL,
	manager_staff_id int2 NOT NULL,
	address_id int2 NOT NULL,
	last_update timestamp DEFAULT now() NOT NULL,
	CONSTRAINT store_pkey PRIMARY KEY (store_id),
	CONSTRAINT store_address_id_fkey FOREIGN KEY (address_id) REFERENCES address(address_id) ON DELETE RESTRICT ON UPDATE CASCADE,
	CONSTRAINT store_manager_staff_id_fkey FOREIGN KEY (manager_staff_id) REFERENCES staff(staff_id) ON DELETE RESTRICT ON UPDATE CASCADE
);
CREATE UNIQUE INDEX idx_unq_manager_staff_id ON public.store USING btree (manager_staff_id);

-- Table Triggers

create trigger last_updated before
update
    on
    public.store for each row execute function last_updated();


-- public.rental definition

-- Drop table

-- DROP TABLE rental;

CREATE TABLE rental (
	rental_id serial4 NOT NULL,
	rental_date timestamp NOT NULL,
	inventory_id int4 NOT NULL,
	customer_id int2 NOT NULL,
	return_date timestamp NULL,
	staff_id int2 NOT NULL,
	last_update timestamp DEFAULT now() NOT NULL,
	CONSTRAINT rental_pkey PRIMARY KEY (rental_id),
	CONSTRAINT rental_customer_id_fkey FOREIGN KEY (customer_id) REFERENCES customer(customer_id) ON DELETE RESTRICT ON UPDATE CASCADE,
	CONSTRAINT rental_inventory_id_fkey FOREIGN KEY (inventory_id) REFERENCES inventory(inventory_id) ON DELETE RESTRICT ON UPDATE CASCADE,
	CONSTRAINT rental_staff_id_key FOREIGN KEY (staff_id) REFERENCES staff(staff_id)
);
CREATE INDEX idx_fk_inventory_id ON public.rental USING btree (inventory_id);
CREATE UNIQUE INDEX idx_unq_rental_rental_date_inventory_id_customer_id ON public.rental USING btree (rental_date, inventory_id, customer_id);

-- Table Triggers

create trigger last_updated before
update
    on
    public.rental for each row execute function last_updated();


-- public.payment definition

-- Drop table

-- DROP TABLE payment;

CREATE TABLE payment (
	payment_id serial4 NOT NULL,
	customer_id int2 NOT NULL,
	staff_id int2 NOT NULL,
	rental_id int4 NOT NULL,
	amount numeric(5, 2) NOT NULL,
	payment_date timestamp NOT NULL,
	CONSTRAINT payment_pkey PRIMARY KEY (payment_id),
	CONSTRAINT payment_customer_id_fkey FOREIGN KEY (customer_id) REFERENCES customer(customer_id) ON DELETE RESTRICT ON UPDATE CASCADE,
	CONSTRAINT payment_rental_id_fkey FOREIGN KEY (rental_id) REFERENCES rental(rental_id) ON DELETE SET NULL ON UPDATE CASCADE,
	CONSTRAINT payment_staff_id_fkey FOREIGN KEY (staff_id) REFERENCES staff(staff_id) ON DELETE RESTRICT ON UPDATE CASCADE
);
CREATE INDEX idx_fk_customer_id ON public.payment USING btree (customer_id);
CREATE INDEX idx_fk_rental_id ON public.payment USING btree (rental_id);
CREATE INDEX idx_fk_staff_id ON public.payment USING btree (staff_id);