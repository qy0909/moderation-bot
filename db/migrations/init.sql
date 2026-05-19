-- USERS TABLE
CREATE TABLE IF NOT EXISTS users (
    user_id BIGINT PRIMARY KEY,
    username TEXT NOT NULL,
    total_messages INTEGER DEFAULT 0,
    rolling_toxicity_avg REAL DEFAULT 0.0
        CHECK (rolling_toxicity_avg >= 0 AND rolling_toxicity_avg <= 1),
    last_ewma REAL DEFAULT NULL,
    warning_count INTEGER DEFAULT 0,
    last_seen TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- MODERATION SETTINGS TABLE
CREATE TABLE IF NOT EXISTS moderation_settings (
    guild_id BIGINT PRIMARY KEY,
    toxicity_threshold REAL DEFAULT 0.75
        CHECK (toxicity_threshold >= 0 AND toxicity_threshold <= 1),
    sentiment_threshold REAL DEFAULT -0.60
        CHECK (sentiment_threshold >= -1 AND sentiment_threshold <= 1),
    auto_intervention_enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- MESSAGES TABLE
CREATE TABLE IF NOT EXISTS messages (
    message_id BIGINT PRIMARY KEY,
    guild_id BIGINT NOT NULL
        REFERENCES moderation_settings(guild_id) ON DELETE CASCADE,
    user_id BIGINT NOT NULL
        REFERENCES users(user_id) ON DELETE CASCADE,
    channel_id BIGINT NOT NULL,
    message_content TEXT,
    content_hash TEXT,
    sentiment_score REAL
        CHECK (sentiment_score >= -1 AND sentiment_score <= 1),
    toxicity_score REAL
        CHECK (toxicity_score >= 0 AND toxicity_score <= 1),
    model_name TEXT,
    model_version TEXT,
    is_flagged BOOLEAN DEFAULT FALSE,
    is_deleted BOOLEAN DEFAULT FALSE,
    message_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- INTERVENTIONS TABLE
CREATE TABLE IF NOT EXISTS interventions (
    intervention_id SERIAL PRIMARY KEY,
    guild_id BIGINT NOT NULL
        REFERENCES moderation_settings(guild_id) ON DELETE CASCADE,
    user_id BIGINT NOT NULL
        REFERENCES users(user_id) ON DELETE CASCADE,
    trigger_message_id BIGINT
        REFERENCES messages(message_id) ON DELETE SET NULL,
    action_type TEXT NOT NULL,
    severity_level TEXT
        CHECK (severity_level IN ('low', 'medium', 'high', 'critical')),
    reasoning TEXT,
    generated_response TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- SERVER METRICS TABLE (For SPC Engine)
CREATE TABLE IF NOT EXISTS server_metrics (
    metric_id SERIAL PRIMARY KEY,
    guild_id BIGINT NOT NULL
        REFERENCES moderation_settings(guild_id) ON DELETE CASCADE,
    rolling_avg_toxicity REAL,
    rolling_std_dev REAL,
    upper_control_limit REAL,
    messages_processed INTEGER DEFAULT 0,
    metric_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- PERFORMANCE INDEXES
CREATE INDEX IF NOT EXISTS idx_messages_guild_timestamp ON messages(guild_id, message_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_messages_toxicity ON messages(guild_id, toxicity_score DESC);
CREATE INDEX IF NOT EXISTS idx_interventions_user ON interventions(user_id);
CREATE INDEX IF NOT EXISTS idx_interventions_guild ON interventions(guild_id);
CREATE INDEX IF NOT EXISTS idx_server_metrics_guild ON server_metrics(guild_id, metric_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_users_last_seen ON users(last_seen DESC);