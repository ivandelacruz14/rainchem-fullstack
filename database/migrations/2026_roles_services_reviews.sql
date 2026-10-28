-- Rainchem: roles and permissions, services with area pricing, product reviews, server-side cart.
-- The Flask app applies all of this automatically at startup (app/services/schema_updates.py).
-- Run this file by hand only if the database user cannot ALTER/CREATE, or you prefer to apply it yourself.
-- Safe to run once. The three ALTER statements fail with "Duplicate column" if already applied; that is harmless.
-- Nothing here drops or rewrites existing data.

ALTER TABLE admins ADD COLUMN permissions JSON NULL;
ALTER TABLE admins ADD COLUMN is_active TINYINT(1) NOT NULL DEFAULT 1;
ALTER TABLE products ADD COLUMN owner_admin_id INT NULL;
ALTER TABLE products ADD CONSTRAINT fk_products_owner_admin FOREIGN KEY (owner_admin_id) REFERENCES admins(id) ON DELETE SET NULL;

CREATE TABLE IF NOT EXISTS product_reviews (
    id INT AUTO_INCREMENT PRIMARY KEY,
    product_id INT NOT NULL,
    order_id INT NOT NULL,
    user_id INT NOT NULL,
    rating SMALLINT NOT NULL,
    comment VARCHAR(500) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_review_order_product (order_id, product_id),
    INDEX ix_product_reviews_product (product_id),
    FOREIGN KEY (product_id) REFERENCES products(id),
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS cart_items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    product_id INT NOT NULL,
    quantity INT NOT NULL DEFAULT 1,
    updated_at DATETIME NULL,
    UNIQUE KEY uq_cart_user_product (user_id, product_id),
    INDEX ix_cart_items_user (user_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS services (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(150) NOT NULL,
    category VARCHAR(80) NULL,
    description TEXT NOT NULL,
    requirements TEXT NULL,
    is_active TINYINT(1) NOT NULL DEFAULT 1,
    owner_admin_id INT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NULL,
    FOREIGN KEY (owner_admin_id) REFERENCES admins(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS service_areas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    service_id INT NOT NULL,
    area_name VARCHAR(120) NOT NULL,
    price DECIMAL(10,2) NOT NULL,
    is_available TINYINT(1) NOT NULL DEFAULT 1,
    notes VARCHAR(255) NULL,
    UNIQUE KEY uq_service_area_name (service_id, area_name),
    FOREIGN KEY (service_id) REFERENCES services(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS service_bookings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    booking_number VARCHAR(40) NOT NULL UNIQUE,
    user_id INT NOT NULL,
    service_id INT NOT NULL,
    service_area_id INT NULL,
    service_name VARCHAR(150) NOT NULL,
    area_name VARCHAR(120) NOT NULL,
    price DECIMAL(10,2) NOT NULL,
    customer_name VARCHAR(150) NOT NULL,
    customer_phone VARCHAR(30) NOT NULL,
    customer_email VARCHAR(180) NULL,
    address VARCHAR(255) NOT NULL,
    preferred_date DATE NULL,
    notes VARCHAR(500) NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'requested',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NULL,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (service_id) REFERENCES services(id),
    FOREIGN KEY (service_area_id) REFERENCES service_areas(id) ON DELETE SET NULL
);

-- Rainchem: product sales (percentage off for a date range).
-- The Flask app creates this table automatically at startup. Run by hand only if you prefer to.
-- Nothing here changes or deletes existing data.

CREATE TABLE IF NOT EXISTS product_sales (
    id INT AUTO_INCREMENT PRIMARY KEY,
    product_id INT NOT NULL,
    discount_percent SMALLINT NOT NULL,
    starts_at DATETIME NOT NULL,
    ends_at DATETIME NOT NULL,
    label VARCHAR(60) NULL,
    is_active TINYINT(1) NOT NULL DEFAULT 1,
    created_by INT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX ix_product_sales_product (product_id),
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
    FOREIGN KEY (created_by) REFERENCES admins(id) ON DELETE SET NULL
);

-- Rainchem: Head Admin approval for product changes (add, edit, delete) with an emailed one-time code.
-- The Flask app creates these tables automatically at startup. Run by hand only if you prefer to.
-- Nothing here changes or deletes existing data.

CREATE TABLE IF NOT EXISTS change_requests (
    id INT AUTO_INCREMENT PRIMARY KEY,
    kind VARCHAR(30) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    product_id INT NULL,
    target_name VARCHAR(200) NOT NULL,
    payload JSON NULL,
    image_photo LONGTEXT NULL,
    requested_by INT NULL,
    requester_name VARCHAR(120) NOT NULL DEFAULT '',
    requester_role VARCHAR(60) NOT NULL DEFAULT '',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    decided_by INT NULL,
    decider_name VARCHAR(120) NULL,
    decided_at DATETIME NULL,
    decision_note VARCHAR(255) NULL,
    INDEX ix_change_requests_product (product_id),
    FOREIGN KEY (requested_by) REFERENCES admins(id) ON DELETE SET NULL,
    FOREIGN KEY (decided_by) REFERENCES admins(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS approval_otps (
    id INT AUTO_INCREMENT PRIMARY KEY,
    change_request_id INT NOT NULL,
    admin_id INT NOT NULL,
    salt VARCHAR(32) NOT NULL,
    code_hash VARCHAR(64) NOT NULL,
    expires_at DATETIME NOT NULL,
    attempts SMALLINT NOT NULL DEFAULT 0,
    used TINYINT(1) NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX ix_approval_otps_request (change_request_id),
    FOREIGN KEY (change_request_id) REFERENCES change_requests(id) ON DELETE CASCADE,
    FOREIGN KEY (admin_id) REFERENCES admins(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS admin_email_changes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    admin_id INT NOT NULL,
    new_email VARCHAR(180) NOT NULL,
    salt VARCHAR(32) NOT NULL,
    code_hash VARCHAR(64) NOT NULL,
    expires_at DATETIME NOT NULL,
    attempts SMALLINT NOT NULL DEFAULT 0,
    used TINYINT(1) NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX ix_admin_email_changes_admin (admin_id),
    FOREIGN KEY (admin_id) REFERENCES admins(id) ON DELETE CASCADE
);