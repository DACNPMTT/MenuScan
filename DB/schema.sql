-- MenuScan MVP database schema reference.
-- PostgreSQL 16+.
-- Source of truth: app/alembic/versions/001_create_mvp_schema.py.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

DO $$
BEGIN
    CREATE TYPE user_role AS ENUM ('USER', 'ADMIN');
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

DO $$
BEGIN
    CREATE TYPE user_status AS ENUM ('ACTIVE', 'LOCKED', 'DISABLED');
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

DO $$
BEGIN
    CREATE TYPE scan_status AS ENUM (
        'PENDING',
        'PROCESSING',
        'COMPLETED',
        'FAILED'
    );
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) NOT NULL,
    display_name VARCHAR(150),
    preferred_language VARCHAR(10) NOT NULL DEFAULT 'vi',
    role user_role NOT NULL DEFAULT 'USER',
    status user_status NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMPTZ,

    CONSTRAINT ck_users_preferred_language
        CHECK (preferred_language IN ('vi', 'en'))
);

CREATE UNIQUE INDEX uq_users_email_lower
    ON users (LOWER(email));

CREATE TABLE magic_link_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) NOT NULL,
    user_id UUID,
    token_hash VARCHAR(255) NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    consumed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_magic_link_tokens_user_id_users
        FOREIGN KEY (user_id)
        REFERENCES users (id),

    CONSTRAINT uq_magic_link_tokens_token_hash
        UNIQUE (token_hash)
);

CREATE INDEX ix_magic_link_tokens_email_created_at
    ON magic_link_tokens (email, created_at DESC);

CREATE TABLE user_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID,
    refresh_token_hash VARCHAR(255) NOT NULL,
    user_agent TEXT,
    ip_address INET,
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_rotated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_user_sessions_user_id_users
        FOREIGN KEY (user_id)
        REFERENCES users (id)
        ON DELETE CASCADE,

    CONSTRAINT uq_user_sessions_refresh_token_hash
        UNIQUE (refresh_token_hash)
);

CREATE INDEX ix_user_sessions_user_id
    ON user_sessions (user_id);

CREATE TABLE scan_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    source_object_key TEXT NOT NULL,
    source_file_name VARCHAR(255) NOT NULL,
    source_mime_type VARCHAR(100) NOT NULL,
    source_file_size BIGINT NOT NULL,
    source_page_count SMALLINT NOT NULL DEFAULT 1,
    target_language VARCHAR(10) NOT NULL,
    status scan_status NOT NULL DEFAULT 'PENDING',
    stage VARCHAR(30),
    progress SMALLINT NOT NULL DEFAULT 0,
    error_code VARCHAR(100),
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    deleted_at TIMESTAMPTZ,

    CONSTRAINT fk_scan_sessions_user_id_users
        FOREIGN KEY (user_id)
        REFERENCES users (id),

    CONSTRAINT ck_scan_sessions_mime_type
        CHECK (
            source_mime_type IN (
                'image/jpeg',
                'image/png',
                'image/webp',
                'application/pdf'
            )
        ),

    CONSTRAINT ck_scan_sessions_file_size
        CHECK (source_file_size BETWEEN 1 AND 10485760),

    CONSTRAINT ck_scan_sessions_page_count
        CHECK (source_page_count BETWEEN 1 AND 5),

    CONSTRAINT ck_scan_sessions_target_language
        CHECK (target_language IN ('vi', 'en')),

    CONSTRAINT ck_scan_sessions_progress
        CHECK (progress BETWEEN 0 AND 100),

    CONSTRAINT ck_scan_sessions_failed_error_code
        CHECK (status != 'FAILED' OR error_code IS NOT NULL),

    CONSTRAINT ck_scan_sessions_completed_at
        CHECK (status != 'COMPLETED' OR completed_at IS NOT NULL)
);

CREATE INDEX ix_scan_sessions_user_id
    ON scan_sessions (user_id);

CREATE TABLE ocr_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scan_session_id UUID NOT NULL,
    raw_text TEXT NOT NULL,
    detected_language VARCHAR(10),
    confidence_score NUMERIC(5, 4),
    provider VARCHAR(50),
    provider_metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    processing_time_ms INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_ocr_results_scan_session_id_scan_sessions
        FOREIGN KEY (scan_session_id)
        REFERENCES scan_sessions (id)
        ON DELETE CASCADE,

    CONSTRAINT uq_ocr_results_scan_session_id
        UNIQUE (scan_session_id),

    CONSTRAINT ck_ocr_results_confidence
        CHECK (confidence_score BETWEEN 0 AND 1),

    CONSTRAINT ck_ocr_results_processing_time
        CHECK (processing_time_ms >= 0)
);

CREATE TABLE menus (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scan_session_id UUID NOT NULL,
    title VARCHAR(255) NOT NULL,
    source_language VARCHAR(10),
    target_language VARCHAR(10) NOT NULL,
    default_currency CHAR(3),
    is_saved BOOLEAN NOT NULL DEFAULT FALSE,
    saved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_menus_scan_session_id_scan_sessions
        FOREIGN KEY (scan_session_id)
        REFERENCES scan_sessions (id)
        ON DELETE CASCADE,

    CONSTRAINT uq_menus_scan_session_id
        UNIQUE (scan_session_id),

    CONSTRAINT ck_menus_saved_at
        CHECK (NOT is_saved OR saved_at IS NOT NULL),

    CONSTRAINT ck_menus_target_language
        CHECK (target_language IN ('vi', 'en'))
);

CREATE TABLE food_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    menu_id UUID NOT NULL,
    original_name VARCHAR(255) NOT NULL,
    translated_name VARCHAR(255),
    original_description TEXT,
    translated_description TEXT,
    price NUMERIC(14, 2),
    currency CHAR(3),
    category VARCHAR(100),
    confidence_score NUMERIC(5, 4),
    sort_order INTEGER NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_food_items_menu_id_menus
        FOREIGN KEY (menu_id)
        REFERENCES menus (id)
        ON DELETE CASCADE,

    CONSTRAINT uq_food_items_menu_id_sort_order
        UNIQUE (menu_id, sort_order),

    CONSTRAINT ck_food_items_price_non_negative
        CHECK (price >= 0),

    CONSTRAINT ck_food_items_confidence
        CHECK (confidence_score BETWEEN 0 AND 1),

    CONSTRAINT ck_food_items_sort_order
        CHECK (sort_order >= 0)
);

CREATE INDEX ix_food_items_menu_id
    ON food_items (menu_id);
