-- MenuScan database schema.
-- PostgreSQL 16+.
--
-- GENERATED from the SQLAlchemy models at Alembic head `e8b5d3f07a24`.
-- The Alembic migrations in app/alembic/versions/ remain the authoritative
-- source of truth; this file is a readable full-schema snapshot kept in sync
-- with them. Regenerate it when you add a migration -- do not hand-edit.
--
-- 20 tables: 19 business + 1 infrastructure (ai_throttle).

-- ---------------------------------------------------------------------------
-- Enum types
-- ---------------------------------------------------------------------------

CREATE TYPE user_role AS ENUM ('USER', 'ADMIN');
CREATE TYPE user_status AS ENUM ('ACTIVE', 'LOCKED', 'DISABLED');
CREATE TYPE scan_status AS ENUM ('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED');
CREATE TYPE preference_type AS ENUM ('LIKE', 'DISLIKE', 'AVOID', 'ALLERGY', 'DIETARY_RULE');
CREATE TYPE menu_status AS ENUM ('DRAFT', 'CONFIRMED');
CREATE TYPE bill_status AS ENUM ('DRAFT', 'FINALIZED');
CREATE TYPE dining_session_mode AS ENUM ('PERSONAL', 'GROUP');
CREATE TYPE dining_session_status AS ENUM ('COLLECTING', 'SCANNING', 'COMPLETED', 'CLOSED');
CREATE TYPE bill_adjustment_type AS ENUM ('DISCOUNT', 'SURCHARGE', 'TAX', 'SERVICE_CHARGE', 'ROUNDING');
CREATE TYPE bill_adjustment_calculation_type AS ENUM ('FIXED', 'PERCENTAGE');
CREATE TYPE recommendation_verdict AS ENUM ('RECOMMENDED', 'OK', 'CAUTION', 'AVOID');

-- ---------------------------------------------------------------------------
-- Tables
-- ---------------------------------------------------------------------------

CREATE TABLE ai_throttle (
    subject_type VARCHAR(8) NOT NULL,
    subject_id VARCHAR(255) NOT NULL,
    action VARCHAR(16) NOT NULL,
    last_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_ai_throttle PRIMARY KEY (subject_type, subject_id, action)
);

CREATE TABLE users (
    id UUID NOT NULL,
    email VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255),
    display_name VARCHAR(150),
    preferred_language VARCHAR(10) DEFAULT 'vi' NOT NULL,
    allergies TEXT[] DEFAULT '{}'::text[] NOT NULL,
    dietary_preferences TEXT[] DEFAULT '{}'::text[] NOT NULL,
    role user_role DEFAULT 'USER' NOT NULL,
    status user_status DEFAULT 'ACTIVE' NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    deleted_at TIMESTAMP WITH TIME ZONE,
    CONSTRAINT pk_users PRIMARY KEY (id),
    CONSTRAINT ck_users_preferred_language CHECK (preferred_language IN ('vi', 'en'))
);
CREATE UNIQUE INDEX uq_users_email_lower ON users (lower(email));

CREATE TABLE food_profiles (
    id UUID NOT NULL,
    user_id UUID NOT NULL,
    display_name VARCHAR(150) NOT NULL,
    preferred_language VARCHAR(10) NOT NULL,
    is_default BOOLEAN DEFAULT 'false' NOT NULL,
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    deleted_at TIMESTAMP WITH TIME ZONE,
    CONSTRAINT pk_food_profiles PRIMARY KEY (id),
    CONSTRAINT ck_food_profiles_preferred_language CHECK (preferred_language ~ '^[a-z]{2,3}(-[a-z0-9]{2,8})*$'),
    CONSTRAINT fk_food_profiles_user_id_users FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);
CREATE INDEX ix_food_profiles_user_id ON food_profiles (user_id);
CREATE UNIQUE INDEX uq_food_profiles_user_default ON food_profiles (user_id) WHERE is_default = true AND deleted_at IS NULL;

CREATE TABLE magic_link_tokens (
    id UUID NOT NULL,
    email VARCHAR(255) NOT NULL,
    user_id UUID,
    token_hash VARCHAR(255) NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    consumed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_magic_link_tokens PRIMARY KEY (id),
    CONSTRAINT fk_magic_link_tokens_user_id_users FOREIGN KEY(user_id) REFERENCES users (id),
    CONSTRAINT uq_magic_link_tokens_token_hash UNIQUE (token_hash)
);
CREATE INDEX ix_magic_link_tokens_email_created_at ON magic_link_tokens (email, created_at DESC);

CREATE TABLE scan_sessions (
    id UUID NOT NULL,
    user_id UUID,
    source_object_key TEXT NOT NULL,
    source_file_name VARCHAR(255) NOT NULL,
    source_mime_type VARCHAR(100) NOT NULL,
    source_file_size BIGINT NOT NULL,
    source_page_count SMALLINT DEFAULT '1' NOT NULL,
    target_language VARCHAR(10) NOT NULL,
    status scan_status DEFAULT 'PENDING' NOT NULL,
    stage VARCHAR(30),
    progress SMALLINT DEFAULT '0' NOT NULL,
    error_code VARCHAR(100),
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    deleted_at TIMESTAMP WITH TIME ZONE,
    CONSTRAINT pk_scan_sessions PRIMARY KEY (id),
    CONSTRAINT ck_scan_sessions_mime_type CHECK (source_mime_type IN ('image/jpeg', 'image/png', 'image/webp', 'application/pdf')),
    CONSTRAINT ck_scan_sessions_file_size CHECK (source_file_size BETWEEN 1 AND 10485760),
    CONSTRAINT ck_scan_sessions_page_count CHECK (source_page_count BETWEEN 1 AND 8),
    CONSTRAINT ck_scan_sessions_target_language CHECK (target_language ~ '^[a-z]{2,3}(-[a-z0-9]{2,8})*$'),
    CONSTRAINT ck_scan_sessions_progress CHECK (progress BETWEEN 0 AND 100),
    CONSTRAINT ck_scan_sessions_failed_error_code CHECK (status != 'FAILED' OR error_code IS NOT NULL),
    CONSTRAINT ck_scan_sessions_completed_at CHECK (status != 'COMPLETED' OR completed_at IS NOT NULL),
    CONSTRAINT fk_scan_sessions_user_id_users FOREIGN KEY(user_id) REFERENCES users (id)
);
CREATE INDEX ix_scan_sessions_user_id ON scan_sessions (user_id);

CREATE TABLE user_sessions (
    id UUID NOT NULL,
    user_id UUID NOT NULL,
    refresh_token_hash VARCHAR(255) NOT NULL,
    user_agent TEXT,
    ip_address INET,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    revoked_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    last_rotated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_user_sessions PRIMARY KEY (id),
    CONSTRAINT fk_user_sessions_user_id_users FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE,
    CONSTRAINT uq_user_sessions_refresh_token_hash UNIQUE (refresh_token_hash)
);
CREATE INDEX ix_user_sessions_user_id ON user_sessions (user_id);

CREATE TABLE food_profile_preferences (
    id UUID NOT NULL,
    food_profile_id UUID NOT NULL,
    code VARCHAR(80) NOT NULL,
    category VARCHAR(40) NOT NULL,
    preference_type preference_type NOT NULL,
    intensity SMALLINT,
    importance SMALLINT DEFAULT '3' NOT NULL,
    note TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_food_profile_preferences PRIMARY KEY (id),
    CONSTRAINT uq_food_profile_preferences_profile_code_type UNIQUE (food_profile_id, code, preference_type),
    CONSTRAINT ck_food_profile_preferences_intensity CHECK (intensity BETWEEN 0 AND 5),
    CONSTRAINT ck_food_profile_preferences_importance CHECK (importance BETWEEN 1 AND 5),
    CONSTRAINT fk_food_profile_preferences_food_profile_id_food_profiles FOREIGN KEY(food_profile_id) REFERENCES food_profiles (id) ON DELETE CASCADE
);
CREATE INDEX ix_food_profile_preferences_food_profile_id ON food_profile_preferences (food_profile_id);

CREATE TABLE menus (
    id UUID NOT NULL,
    scan_session_id UUID NOT NULL,
    title VARCHAR(255) NOT NULL,
    source_language VARCHAR(10),
    target_language VARCHAR(10) NOT NULL,
    default_currency CHAR(3),
    is_saved BOOLEAN DEFAULT 'false' NOT NULL,
    status menu_status DEFAULT 'DRAFT' NOT NULL,
    saved_at TIMESTAMP WITH TIME ZONE,
    deleted_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_menus PRIMARY KEY (id),
    CONSTRAINT ck_menus_target_language CHECK (target_language ~ '^[a-z]{2,3}(-[a-z0-9]{2,8})*$'),
    CONSTRAINT ck_menus_saved_at CHECK (NOT is_saved OR saved_at IS NOT NULL),
    CONSTRAINT uq_menus_scan_session_id UNIQUE (scan_session_id),
    CONSTRAINT fk_menus_scan_session_id_scan_sessions FOREIGN KEY(scan_session_id) REFERENCES scan_sessions (id) ON DELETE CASCADE
);
CREATE INDEX ix_menus_deleted_at ON menus (deleted_at);
CREATE INDEX ix_menus_updated_at ON menus (updated_at);

CREATE TABLE ocr_results (
    id UUID NOT NULL,
    scan_session_id UUID NOT NULL,
    raw_text TEXT NOT NULL,
    detected_language VARCHAR(10),
    confidence_score NUMERIC(5, 4),
    provider VARCHAR(50),
    provider_metadata JSONB DEFAULT '{}'::jsonb NOT NULL,
    processing_time_ms INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_ocr_results PRIMARY KEY (id),
    CONSTRAINT ck_ocr_results_confidence CHECK (confidence_score BETWEEN 0 AND 1),
    CONSTRAINT ck_ocr_results_processing_time CHECK (processing_time_ms >= 0),
    CONSTRAINT uq_ocr_results_scan_session_id UNIQUE (scan_session_id),
    CONSTRAINT fk_ocr_results_scan_session_id_scan_sessions FOREIGN KEY(scan_session_id) REFERENCES scan_sessions (id) ON DELETE CASCADE
);

CREATE TABLE scan_source_files (
    id UUID NOT NULL,
    scan_session_id UUID NOT NULL,
    object_key TEXT NOT NULL,
    file_name VARCHAR(255) NOT NULL,
    mime_type VARCHAR(100) NOT NULL,
    file_size BIGINT NOT NULL,
    page_count SMALLINT DEFAULT '1' NOT NULL,
    sort_order SMALLINT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_scan_source_files PRIMARY KEY (id),
    CONSTRAINT ck_scan_source_files_source_file_mime_type CHECK (mime_type IN ('image/jpeg', 'image/png', 'image/webp', 'application/pdf')),
    CONSTRAINT ck_scan_source_files_source_file_size CHECK (file_size BETWEEN 1 AND 10485760),
    CONSTRAINT ck_scan_source_files_source_file_sort_order CHECK (sort_order >= 0),
    CONSTRAINT fk_scan_source_files_scan_session_id_scan_sessions FOREIGN KEY(scan_session_id) REFERENCES scan_sessions (id) ON DELETE CASCADE
);
CREATE INDEX ix_scan_source_files_scan_session_id ON scan_source_files (scan_session_id);

CREATE TABLE bills (
    id UUID NOT NULL,
    user_id UUID NOT NULL,
    menu_id UUID NOT NULL,
    status bill_status DEFAULT 'DRAFT' NOT NULL,
    currency CHAR(3) NOT NULL,
    subtotal_amount NUMERIC(14, 2) DEFAULT '0' NOT NULL,
    adjustment_total NUMERIC(14, 2) DEFAULT '0' NOT NULL,
    total_amount NUMERIC(14, 2) DEFAULT '0' NOT NULL,
    note TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    finalized_at TIMESTAMP WITH TIME ZONE,
    CONSTRAINT pk_bills PRIMARY KEY (id),
    CONSTRAINT ck_bills_status CHECK (status IN ('DRAFT', 'FINALIZED')),
    CONSTRAINT ck_bills_finalized_at CHECK (status != 'FINALIZED' OR finalized_at IS NOT NULL),
    CONSTRAINT ck_bills_subtotal_amount_non_negative CHECK (subtotal_amount >= 0),
    CONSTRAINT ck_bills_total_amount_non_negative CHECK (total_amount >= 0),
    CONSTRAINT fk_bills_user_id_users FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE RESTRICT,
    CONSTRAINT fk_bills_menu_id_menus FOREIGN KEY(menu_id) REFERENCES menus (id) ON DELETE RESTRICT
);
CREATE INDEX ix_bills_menu_id ON bills (menu_id);
CREATE INDEX ix_bills_user_id ON bills (user_id);

CREATE TABLE dining_sessions (
    id UUID NOT NULL,
    created_by_user_id UUID,
    scan_session_id UUID,
    menu_id UUID,
    mode dining_session_mode NOT NULL,
    status dining_session_status DEFAULT 'COLLECTING' NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    completed_at TIMESTAMP WITH TIME ZONE,
    closed_at TIMESTAMP WITH TIME ZONE,
    deleted_at TIMESTAMP WITH TIME ZONE,
    CONSTRAINT pk_dining_sessions PRIMARY KEY (id),
    CONSTRAINT ck_dining_sessions_completed_has_scan_and_menu CHECK (status != 'COMPLETED' OR (scan_session_id IS NOT NULL AND menu_id IS NOT NULL)),
    CONSTRAINT fk_dining_sessions_created_by_user_id_users FOREIGN KEY(created_by_user_id) REFERENCES users (id) ON DELETE SET NULL,
    CONSTRAINT uq_dining_sessions_scan_session_id UNIQUE (scan_session_id),
    CONSTRAINT fk_dining_sessions_scan_session_id_scan_sessions FOREIGN KEY(scan_session_id) REFERENCES scan_sessions (id) ON DELETE SET NULL,
    CONSTRAINT uq_dining_sessions_menu_id UNIQUE (menu_id),
    CONSTRAINT fk_dining_sessions_menu_id_menus FOREIGN KEY(menu_id) REFERENCES menus (id) ON DELETE SET NULL
);
CREATE INDEX ix_dining_sessions_created_by_user_id ON dining_sessions (created_by_user_id);
CREATE INDEX ix_dining_sessions_menu_id ON dining_sessions (menu_id);
CREATE INDEX ix_dining_sessions_scan_session_id ON dining_sessions (scan_session_id);

CREATE TABLE food_items (
    id UUID NOT NULL,
    menu_id UUID NOT NULL,
    original_name VARCHAR(255) NOT NULL,
    translated_name VARCHAR(255),
    original_description TEXT,
    translated_description TEXT,
    assistant_summary TEXT,
    main_ingredients TEXT[] DEFAULT '{}'::text[] NOT NULL,
    ingredient_tags TEXT[] DEFAULT '{}'::text[] NOT NULL,
    flavor_tags TEXT[] DEFAULT '{}'::text[] NOT NULL,
    texture_tags TEXT[] DEFAULT '{}'::text[] NOT NULL,
    cooking_methods TEXT[] DEFAULT '{}'::text[] NOT NULL,
    spice_level SMALLINT,
    sweetness_level SMALLINT,
    saltiness_level SMALLINT,
    sourness_level SMALLINT,
    richness_level SMALLINT,
    oiliness_level SMALLINT,
    risk_notes TEXT,
    price NUMERIC(14, 2),
    currency CHAR(3),
    category VARCHAR(100),
    allergens TEXT[] DEFAULT '{}'::text[] NOT NULL,
    dietary_tags TEXT[] DEFAULT '{}'::text[] NOT NULL,
    confidence_score NUMERIC(5, 4),
    sort_order INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_food_items PRIMARY KEY (id),
    CONSTRAINT uq_food_items_menu_id_sort_order UNIQUE (menu_id, sort_order),
    CONSTRAINT ck_food_items_price_non_negative CHECK (price >= 0),
    CONSTRAINT ck_food_items_spice_level CHECK (spice_level BETWEEN 0 AND 5),
    CONSTRAINT ck_food_items_sweetness_level CHECK (sweetness_level BETWEEN 0 AND 5),
    CONSTRAINT ck_food_items_saltiness_level CHECK (saltiness_level BETWEEN 0 AND 5),
    CONSTRAINT ck_food_items_sourness_level CHECK (sourness_level BETWEEN 0 AND 5),
    CONSTRAINT ck_food_items_richness_level CHECK (richness_level BETWEEN 0 AND 5),
    CONSTRAINT ck_food_items_oiliness_level CHECK (oiliness_level BETWEEN 0 AND 5),
    CONSTRAINT ck_food_items_confidence CHECK (confidence_score BETWEEN 0 AND 1),
    CONSTRAINT ck_food_items_sort_order CHECK (sort_order >= 0),
    CONSTRAINT fk_food_items_menu_id_menus FOREIGN KEY(menu_id) REFERENCES menus (id) ON DELETE CASCADE
);
CREATE INDEX ix_food_items_menu_id ON food_items (menu_id);

CREATE TABLE bill_adjustments (
    id UUID NOT NULL,
    bill_id UUID NOT NULL,
    type bill_adjustment_type NOT NULL,
    label VARCHAR(255) NOT NULL,
    calculation_type bill_adjustment_calculation_type DEFAULT 'FIXED' NOT NULL,
    value NUMERIC(14, 2) NOT NULL,
    calculated_amount NUMERIC(14, 2) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_bill_adjustments PRIMARY KEY (id),
    CONSTRAINT ck_bill_adjustments_value_non_negative CHECK (value >= 0),
    CONSTRAINT ck_bill_adjustments_percentage_value_within_bounds CHECK (calculation_type != 'PERCENTAGE' OR value <= 100),
    CONSTRAINT fk_bill_adjustments_bill_id_bills FOREIGN KEY(bill_id) REFERENCES bills (id) ON DELETE CASCADE
);
CREATE INDEX ix_bill_adjustments_bill_id ON bill_adjustments (bill_id);

CREATE TABLE bill_items (
    id UUID NOT NULL,
    bill_id UUID NOT NULL,
    food_item_id UUID,
    name_snapshot VARCHAR(255) NOT NULL,
    unit_price_snapshot NUMERIC(14, 2) NOT NULL,
    currency CHAR(3) NOT NULL,
    quantity INTEGER DEFAULT '1' NOT NULL,
    line_total NUMERIC(14, 2) NOT NULL,
    sort_order INTEGER DEFAULT '0' NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_bill_items PRIMARY KEY (id),
    CONSTRAINT ck_bill_items_quantity_positive CHECK (quantity > 0),
    CONSTRAINT ck_bill_items_unit_price_snapshot_non_negative CHECK (unit_price_snapshot >= 0),
    CONSTRAINT ck_bill_items_line_total_non_negative CHECK (line_total >= 0),
    CONSTRAINT fk_bill_items_bill_id_bills FOREIGN KEY(bill_id) REFERENCES bills (id) ON DELETE CASCADE,
    CONSTRAINT fk_bill_items_food_item_id_food_items FOREIGN KEY(food_item_id) REFERENCES food_items (id) ON DELETE SET NULL
);
CREATE INDEX ix_bill_items_bill_id ON bill_items (bill_id);

CREATE TABLE dining_session_invites (
    id UUID NOT NULL,
    dining_session_id UUID NOT NULL,
    token_hash VARCHAR(255) NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE,
    revoked_at TIMESTAMP WITH TIME ZONE,
    max_uses INTEGER,
    use_count INTEGER DEFAULT '0' NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_dining_session_invites PRIMARY KEY (id),
    CONSTRAINT ck_dining_session_invites_max_uses_positive CHECK (max_uses > 0),
    CONSTRAINT ck_dining_session_invites_use_count_non_negative CHECK (use_count >= 0),
    CONSTRAINT ck_dining_session_invites_use_count_within_max_uses CHECK (max_uses IS NULL OR use_count <= max_uses),
    CONSTRAINT fk_dining_session_invites_dining_session_id_dining_sessions FOREIGN KEY(dining_session_id) REFERENCES dining_sessions (id) ON DELETE CASCADE,
    CONSTRAINT uq_dining_session_invites_token_hash UNIQUE (token_hash)
);
CREATE INDEX ix_dining_session_invites_dining_session_id ON dining_session_invites (dining_session_id);

CREATE TABLE dining_session_participants (
    id UUID NOT NULL,
    dining_session_id UUID NOT NULL,
    user_id UUID,
    display_name VARCHAR(150) NOT NULL,
    joined_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    left_at TIMESTAMP WITH TIME ZONE,
    CONSTRAINT pk_dining_session_participants PRIMARY KEY (id),
    CONSTRAINT fk_dining_participants_dining_session_id FOREIGN KEY(dining_session_id) REFERENCES dining_sessions (id) ON DELETE CASCADE,
    CONSTRAINT fk_dining_session_participants_user_id_users FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE SET NULL
);
CREATE INDEX ix_dining_session_participants_dining_session_id ON dining_session_participants (dining_session_id);
CREATE INDEX ix_dining_session_participants_user_id ON dining_session_participants (user_id);

CREATE TABLE food_item_recommendations (
    id UUID NOT NULL,
    dining_session_id UUID NOT NULL,
    food_item_id UUID NOT NULL,
    verdict recommendation_verdict NOT NULL,
    score NUMERIC(5, 2),
    explanation TEXT,
    why_suitable TEXT,
    why_not_suitable TEXT,
    suggested_for TEXT[] DEFAULT '{}'::text[] NOT NULL,
    warning_for TEXT[] DEFAULT '{}'::text[] NOT NULL,
    fit_reasons TEXT[] DEFAULT '{}'::text[] NOT NULL,
    risk_reasons TEXT[] DEFAULT '{}'::text[] NOT NULL,
    warning_reasons TEXT[] DEFAULT '{}'::text[] NOT NULL,
    confidence_score NUMERIC(5, 4),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_food_item_recommendations PRIMARY KEY (id),
    CONSTRAINT uq_food_item_recommendations_session_item UNIQUE (dining_session_id, food_item_id),
    CONSTRAINT ck_food_item_recommendations_score CHECK (score BETWEEN 0 AND 100),
    CONSTRAINT ck_food_item_recommendations_confidence CHECK (confidence_score BETWEEN 0 AND 1),
    CONSTRAINT fk_food_item_recommendations_dining_session_id_dining_sessions FOREIGN KEY(dining_session_id) REFERENCES dining_sessions (id) ON DELETE CASCADE,
    CONSTRAINT fk_food_item_recommendations_food_item_id_food_items FOREIGN KEY(food_item_id) REFERENCES food_items (id) ON DELETE CASCADE
);
CREATE INDEX ix_food_item_recommendations_dining_session_id ON food_item_recommendations (dining_session_id);
CREATE INDEX ix_food_item_recommendations_food_item_id ON food_item_recommendations (food_item_id);

CREATE TABLE dining_session_participant_preferences (
    id UUID NOT NULL,
    participant_id UUID NOT NULL,
    code VARCHAR(80) NOT NULL,
    category VARCHAR(40) NOT NULL,
    preference_type preference_type NOT NULL,
    intensity SMALLINT,
    importance SMALLINT DEFAULT '3' NOT NULL,
    note TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_dining_session_participant_preferences PRIMARY KEY (id),
    CONSTRAINT uq_dining_participant_preferences_participant_code_type UNIQUE (participant_id, code, preference_type),
    CONSTRAINT ck_dining_session_participant_preferences_intensity CHECK (intensity BETWEEN 0 AND 5),
    CONSTRAINT ck_dining_session_participant_preferences_importance CHECK (importance BETWEEN 1 AND 5),
    CONSTRAINT fk_dining_participant_preferences_participant_id FOREIGN KEY(participant_id) REFERENCES dining_session_participants (id) ON DELETE CASCADE
);
CREATE INDEX ix_dining_session_participant_preferences_participant_id ON dining_session_participant_preferences (participant_id);

CREATE TABLE food_item_recommendation_participant_breakdowns (
    id UUID NOT NULL,
    food_item_recommendation_id UUID NOT NULL,
    participant_id UUID NOT NULL,
    verdict recommendation_verdict NOT NULL,
    score NUMERIC(5, 2),
    explanation TEXT,
    fit_reasons TEXT[] DEFAULT '{}'::text[] NOT NULL,
    risk_reasons TEXT[] DEFAULT '{}'::text[] NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_food_item_recommendation_participant_breakdowns PRIMARY KEY (id),
    CONSTRAINT uq_food_item_rec_breakdowns_recommendation_participant UNIQUE (food_item_recommendation_id, participant_id),
    CONSTRAINT ck_food_item_recommendation_participant_breakdowns_score CHECK (score BETWEEN 0 AND 100),
    CONSTRAINT fk_food_item_rec_breakdowns_recommendation_id FOREIGN KEY(food_item_recommendation_id) REFERENCES food_item_recommendations (id) ON DELETE CASCADE,
    CONSTRAINT fk_food_item_recommendation_breakdowns_participant_id FOREIGN KEY(participant_id) REFERENCES dining_session_participants (id) ON DELETE CASCADE
);
CREATE INDEX ix_food_item_recommendation_breakdowns_participant_id ON food_item_recommendation_participant_breakdowns (participant_id);
CREATE INDEX ix_food_item_recommendation_breakdowns_recommendation_id ON food_item_recommendation_participant_breakdowns (food_item_recommendation_id);
