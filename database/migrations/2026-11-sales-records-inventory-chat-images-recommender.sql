-- Rainchem: sales records, inventory movements and alerts, audit log, chat images, chat conversation status,
-- product SKU, and the verified product documents used by the recommendation assistant.
-- The Flask app applies all of this automatically at startup (app/services/schema_updates.py), including filling the
-- sales records from existing orders and recording a baseline of today's stock. Run this file by hand only if you prefer to.
-- The four ALTER statements fail with "Duplicate column" if already applied; that is harmless.
-- Nothing here drops or rewrites existing data. The old Distributor module's columns (products.owner_admin_id,
-- services.owner_admin_id) are left in place on purpose; they are no longer used.

ALTER TABLE products ADD COLUMN sku VARCHAR(40) NULL;
ALTER TABLE live_conversations ADD COLUMN status VARCHAR(12) NOT NULL DEFAULT 'open';
ALTER TABLE live_conversations ADD COLUMN resolved_at DATETIME NULL;
ALTER TABLE live_conversations ADD COLUMN user_last_seen_at DATETIME NULL;

CREATE TABLE IF NOT EXISTS audit_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    admin_id INT NULL,
    admin_name VARCHAR(120) NOT NULL DEFAULT '',
    action VARCHAR(60) NOT NULL,
    entity_type VARCHAR(40) NOT NULL,
    entity_id VARCHAR(60) NOT NULL,
    old_value JSON NULL,
    new_value JSON NULL,
    reason VARCHAR(500) NULL,
    INDEX ix_audit_logs_created (created_at),
    INDEX ix_audit_logs_action (action),
    FOREIGN KEY (admin_id) REFERENCES admins(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS inventory_movements (
    id INT AUTO_INCREMENT PRIMARY KEY,
    product_id INT NULL,
    product_name VARCHAR(200) NOT NULL DEFAULT '',
    movement_type VARCHAR(24) NOT NULL,
    quantity_change INT NOT NULL,
    order_id INT NULL,
    reference VARCHAR(120) NULL,
    reason VARCHAR(255) NULL,
    actor_admin_id INT NULL,
    actor_name VARCHAR(120) NOT NULL DEFAULT '',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX ix_inventory_movements_product (product_id),
    INDEX ix_inventory_movements_order (order_id),
    INDEX ix_inventory_movements_created (created_at),
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE SET NULL,
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE SET NULL,
    FOREIGN KEY (actor_admin_id) REFERENCES admins(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS inventory_alerts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    fingerprint VARCHAR(190) NOT NULL UNIQUE,
    category VARCHAR(30) NOT NULL,
    product_id INT NULL,
    product_name VARCHAR(200) NULL,
    order_id INT NULL,
    order_number VARCHAR(40) NULL,
    expected_value VARCHAR(80) NULL,
    recorded_value VARCHAR(80) NULL,
    difference VARCHAR(80) NULL,
    explanation TEXT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'open',
    assigned_admin_id INT NULL,
    assigned_name VARCHAR(120) NULL,
    resolution_note TEXT NULL,
    resolved_by VARCHAR(120) NULL,
    detected_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    resolved_at DATETIME NULL,
    INDEX ix_inventory_alerts_category (category),
    INDEX ix_inventory_alerts_product (product_id),
    INDEX ix_inventory_alerts_order (order_id),
    INDEX ix_inventory_alerts_detected (detected_at),
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE SET NULL,
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE SET NULL,
    FOREIGN KEY (assigned_admin_id) REFERENCES admins(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS sales_records (
    id INT AUTO_INCREMENT PRIMARY KEY,
    order_item_id INT NOT NULL UNIQUE,
    order_id INT NOT NULL,
    order_number VARCHAR(40) NOT NULL,
    transaction_ref VARCHAR(120) NOT NULL DEFAULT '',
    sold_at DATETIME NOT NULL,
    customer_id INT NULL,
    customer_name VARCHAR(150) NOT NULL DEFAULT '',
    product_id INT NULL,
    product_name VARCHAR(200) NOT NULL,
    sku VARCHAR(40) NULL,
    category VARCHAR(80) NULL,
    quantity INT NOT NULL,
    list_unit_price DECIMAL(10,2) NOT NULL,
    unit_price DECIMAL(10,2) NOT NULL,
    subtotal DECIMAL(10,2) NOT NULL,
    discount_amount DECIMAL(10,2) NOT NULL DEFAULT 0,
    line_total DECIMAL(10,2) NOT NULL,
    shipping_share DECIMAL(10,2) NOT NULL DEFAULT 0,
    tax_amount DECIMAL(10,2) NOT NULL DEFAULT 0,
    order_total DECIMAL(10,2) NOT NULL,
    payment_method VARCHAR(60) NOT NULL DEFAULT '',
    payment_status VARCHAR(20) NOT NULL DEFAULT '',
    order_status VARCHAR(30) NOT NULL DEFAULT '',
    fulfillment_status VARCHAR(30) NOT NULL DEFAULT '',
    refund_status VARCHAR(20) NOT NULL DEFAULT 'none',
    return_status VARCHAR(20) NOT NULL DEFAULT 'none',
    state VARCHAR(12) NOT NULL DEFAULT 'pending',
    notes VARCHAR(500) NULL,
    overrides JSON NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NULL,
    INDEX ix_sales_records_order (order_id),
    INDEX ix_sales_records_number (order_number),
    INDEX ix_sales_records_sold (sold_at),
    INDEX ix_sales_records_product (product_id),
    INDEX ix_sales_records_state (state),
    FOREIGN KEY (order_item_id) REFERENCES order_items(id) ON DELETE CASCADE,
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS live_attachments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    message_id INT NOT NULL UNIQUE,
    conversation_id INT NOT NULL,
    stored_name VARCHAR(60) NOT NULL,
    mime VARCHAR(30) NOT NULL,
    size INT NOT NULL,
    sha256 VARCHAR(64) NOT NULL,
    data LONGBLOB NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX ix_live_attachments_conversation (conversation_id),
    FOREIGN KEY (message_id) REFERENCES live_messages(id) ON DELETE CASCADE,
    FOREIGN KEY (conversation_id) REFERENCES live_conversations(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS product_documents (
    id INT AUTO_INCREMENT PRIMARY KEY,
    product_id INT NULL,
    title VARCHAR(200) NOT NULL,
    doc_type VARCHAR(32) NOT NULL DEFAULT 'technical_data_sheet',
    version VARCHAR(40) NULL,
    source VARCHAR(255) NULL,
    content TEXT NOT NULL,
    facts JSON NULL,
    verified TINYINT(1) NOT NULL DEFAULT 0,
    authorized TINYINT(1) NOT NULL DEFAULT 0,
    verified_by VARCHAR(120) NULL,
    verified_at DATETIME NULL,
    created_by VARCHAR(120) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NULL,
    INDEX ix_product_documents_product (product_id),
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS recommendation_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) NOT NULL,
    application VARCHAR(30) NULL,
    slots_given JSON NULL,
    product_ids JSON NULL,
    document_ids JSON NULL,
    top_score FLOAT NULL,
    elapsed_ms INT NULL,
    INDEX ix_recommendation_logs_created (created_at)
);
