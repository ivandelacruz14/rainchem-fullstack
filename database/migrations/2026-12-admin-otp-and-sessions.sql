

CREATE TABLE IF NOT EXISTS admin_sessions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    admin_id INT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_seen_at DATETIME NOT NULL,
    expires_at DATETIME NOT NULL,
    ended_at DATETIME NULL,
    end_reason VARCHAR(20) NULL,
    INDEX ix_admin_sessions_admin (admin_id),
    FOREIGN KEY (admin_id) REFERENCES admins(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS admin_login_challenges (
    id INT AUTO_INCREMENT PRIMARY KEY,
    admin_id INT NOT NULL,
    challenge_hash VARCHAR(64) NOT NULL,
    salt VARCHAR(32) NOT NULL,
    code_hash VARCHAR(64) NOT NULL,
    expires_at DATETIME NOT NULL,
    attempts SMALLINT NOT NULL DEFAULT 0,
    used TINYINT(1) NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX ix_admin_login_challenges_admin (admin_id),
    INDEX ix_admin_login_challenges_hash (challenge_hash),
    FOREIGN KEY (admin_id) REFERENCES admins(id) ON DELETE CASCADE
);
