-- ============================================
-- Chinook Digital Media Store - Ground Truth DDL
-- 11 tables, 11 PKs (10 atomic + 1 composite), 11 FKs
-- ============================================

CREATE TABLE artist (
    artist_id INTEGER NOT NULL,
    name VARCHAR(120),
    CONSTRAINT artist_pkey PRIMARY KEY (artist_id)
);

CREATE TABLE album (
    album_id INTEGER NOT NULL,
    title VARCHAR(160) NOT NULL,
    artist_id INTEGER NOT NULL,
    CONSTRAINT album_pkey PRIMARY KEY (album_id),
    CONSTRAINT album_fk_artist FOREIGN KEY (artist_id) REFERENCES artist(artist_id)
);

CREATE TABLE media_type (
    media_type_id INTEGER NOT NULL,
    name VARCHAR(120),
    CONSTRAINT media_type_pkey PRIMARY KEY (media_type_id)
);

CREATE TABLE genre (
    genre_id INTEGER NOT NULL,
    name VARCHAR(120),
    CONSTRAINT genre_pkey PRIMARY KEY (genre_id)
);

CREATE TABLE track (
    track_id INTEGER NOT NULL,
    name VARCHAR(200) NOT NULL,
    album_id INTEGER,
    media_type_id INTEGER NOT NULL,
    genre_id INTEGER,
    composer VARCHAR(220),
    milliseconds INTEGER NOT NULL,
    bytes INTEGER,
    unit_price DECIMAL(10,2) NOT NULL,
    CONSTRAINT track_pkey PRIMARY KEY (track_id),
    CONSTRAINT track_fk_album FOREIGN KEY (album_id) REFERENCES album(album_id),
    CONSTRAINT track_fk_media_type FOREIGN KEY (media_type_id) REFERENCES media_type(media_type_id),
    CONSTRAINT track_fk_genre FOREIGN KEY (genre_id) REFERENCES genre(genre_id)
);

CREATE TABLE playlist (
    playlist_id INTEGER NOT NULL,
    name VARCHAR(120),
    CONSTRAINT playlist_pkey PRIMARY KEY (playlist_id)
);

CREATE TABLE playlist_track (
    playlist_id INTEGER NOT NULL,
    track_id INTEGER NOT NULL,
    CONSTRAINT playlist_track_pkey PRIMARY KEY (playlist_id, track_id),
    CONSTRAINT playlist_track_fk_playlist FOREIGN KEY (playlist_id) REFERENCES playlist(playlist_id),
    CONSTRAINT playlist_track_fk_track FOREIGN KEY (track_id) REFERENCES track(track_id)
);

CREATE TABLE employee (
    employee_id INTEGER NOT NULL,
    last_name VARCHAR(20) NOT NULL,
    first_name VARCHAR(20) NOT NULL,
    title VARCHAR(30),
    reports_to INTEGER,
    birth_date DATE,
    hire_date DATE,
    address VARCHAR(70),
    city VARCHAR(40),
    state VARCHAR(40),
    country VARCHAR(40),
    postal_code VARCHAR(10),
    phone VARCHAR(24),
    fax VARCHAR(24),
    email VARCHAR(60),
    CONSTRAINT employee_pkey PRIMARY KEY (employee_id),
    CONSTRAINT employee_fk_reports_to FOREIGN KEY (reports_to) REFERENCES employee(employee_id)
);

CREATE TABLE customer (
    customer_id INTEGER NOT NULL,
    first_name VARCHAR(40) NOT NULL,
    last_name VARCHAR(20) NOT NULL,
    company VARCHAR(80),
    address VARCHAR(70),
    city VARCHAR(40),
    state VARCHAR(40),
    country VARCHAR(40),
    postal_code VARCHAR(10),
    phone VARCHAR(24),
    fax VARCHAR(24),
    email VARCHAR(60) NOT NULL,
    support_rep_id INTEGER,
    CONSTRAINT customer_pkey PRIMARY KEY (customer_id),
    CONSTRAINT customer_fk_support_rep FOREIGN KEY (support_rep_id) REFERENCES employee(employee_id)
);

CREATE TABLE invoice (
    invoice_id INTEGER NOT NULL,
    customer_id INTEGER NOT NULL,
    invoice_date DATE NOT NULL,
    billing_address VARCHAR(70),
    billing_city VARCHAR(40),
    billing_state VARCHAR(40),
    billing_country VARCHAR(40),
    billing_postal_code VARCHAR(10),
    total DECIMAL(10,2) NOT NULL,
    CONSTRAINT invoice_pkey PRIMARY KEY (invoice_id),
    CONSTRAINT invoice_fk_customer FOREIGN KEY (customer_id) REFERENCES customer(customer_id)
);

CREATE TABLE invoice_line (
    invoice_line_id INTEGER NOT NULL,
    invoice_id INTEGER NOT NULL,
    track_id INTEGER NOT NULL,
    unit_price DECIMAL(10,2) NOT NULL,
    quantity INTEGER NOT NULL,
    CONSTRAINT invoice_line_pkey PRIMARY KEY (invoice_line_id),
    CONSTRAINT invoice_line_fk_invoice FOREIGN KEY (invoice_id) REFERENCES invoice(invoice_id),
    CONSTRAINT invoice_line_fk_track FOREIGN KEY (track_id) REFERENCES track(track_id)
);
