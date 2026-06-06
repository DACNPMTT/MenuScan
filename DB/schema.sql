-- MenuScan database schema - Sprint 0 / Task S0-05
-- PostgreSQL 16+

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    name VARCHAR(150) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE menus (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    image_url TEXT NOT NULL,
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_menus_user
        FOREIGN KEY (user_id)
        REFERENCES users (id)
        ON DELETE CASCADE
);

CREATE TABLE food_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    menu_id UUID NOT NULL,
    name VARCHAR(255) NOT NULL,
    price NUMERIC(14, 2) NOT NULL,
    description TEXT,

    CONSTRAINT ck_food_items_price_non_negative
        CHECK (price >= 0),

    CONSTRAINT fk_food_items_menu
        FOREIGN KEY (menu_id)
        REFERENCES menus (id)
        ON DELETE CASCADE
);

CREATE TABLE scan_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    menu_id UUID NOT NULL,
    raw_text TEXT,
    status VARCHAR(30) NOT NULL DEFAULT 'pending',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT ck_scan_sessions_status
        CHECK (status IN ('pending', 'processing', 'completed', 'failed')),

    CONSTRAINT fk_scan_sessions_user
        FOREIGN KEY (user_id)
        REFERENCES users (id)
        ON DELETE CASCADE,

    CONSTRAINT fk_scan_sessions_menu
        FOREIGN KEY (menu_id)
        REFERENCES menus (id)
        ON DELETE CASCADE
);

CREATE INDEX idx_menus_user_id
    ON menus (user_id);

CREATE INDEX idx_food_items_menu_id
    ON food_items (menu_id);

CREATE INDEX idx_scan_sessions_user_id
    ON scan_sessions (user_id);

CREATE INDEX idx_scan_sessions_menu_id
    ON scan_sessions (menu_id);

CREATE INDEX idx_scan_sessions_status
    ON scan_sessions (status);
