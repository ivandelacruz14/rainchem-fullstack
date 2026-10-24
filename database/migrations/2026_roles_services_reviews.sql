-- Rainchem update: roles, product ownership, per-product reviews, services.
-- The Flask app applies the same changes automatically on startup (see
-- backend/app/services/schema_updates.py). Run this file by hand only if the
-- database user used by the app is not allowed to ALTER or CREATE tables.
-- Nothing here drops or deletes data. Each ALTER fails harmlessly if the column exists.

ALTER TABLE admins ADD COLUMN permissions JSON NULL;
ALTER TABLE admins ADD COLUMN is_active TINYINT(1) NOT NULL DEFAULT 1;
ALTER TABLE products ADD COLUMN owner_admin_id INT NULL;
ALTER TABLE products ADD CONSTRAINT fk_products_owner_admin FOREIGN KEY (owner_admin_id) REFERENCES admins(id);

CREATE TABLE IF NOT EXISTS product_reviews (
    id INT AUTO_INCREMENT PRIMARY KEY,
    product_id INT NOT NULL,
    order_id INT NOT NULL,
    user_id INT NOT NULL,
    rating SMALLINT NOT NULL,
    comment VARCHAR(500) NULL,
    created_at DATETIME NULL,
    UNIQUE KEY uq_review_order_product (order_id, product_id),
    KEY ix_product_reviews_product_id (product_id),
    FOREIGN KEY (product_id) REFERENCES products(id),
    FOREIGN KEY (order_id) REFERENCES orders(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS services (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(160) NOT NULL,
    category VARCHAR(80) NULL,
    description TEXT NOT NULL,
    requirements TEXT NULL,
    is_active TINYINT(1) NOT NULL DEFAULT 1,
    owner_admin_id INT NULL,
    created_at DATETIME NULL,
    FOREIGN KEY (owner_admin_id) REFERENCES admins(id)
);

CREATE TABLE IF NOT EXISTS service_areas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    service_id INT NOT NULL,
    area_name VARCHAR(120) NOT NULL,
    price DECIMAL(10,2) NOT NULL,
    is_available TINYINT(1) NOT NULL DEFAULT 1,
    note VARCHAR(255) NULL,
    UNIQUE KEY uq_service_area_name (service_id, area_name),
    KEY ix_service_areas_service_id (service_id),
    FOREIGN KEY (service_id) REFERENCES services(id)
);

CREATE TABLE IF NOT EXISTS service_bookings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    service_id INT NOT NULL,
    area_id INT NULL,
    service_name VARCHAR(160) NOT NULL,
    area_name VARCHAR(120) NOT NULL,
    price DECIMAL(10,2) NOT NULL,
    contact_name VARCHAR(150) NOT NULL,
    contact_phone VARCHAR(30) NOT NULL,
    address VARCHAR(255) NOT NULL,
    preferred_date DATE NULL,
    notes VARCHAR(500) NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'requested',
    created_at DATETIME NULL,
    KEY ix_service_bookings_user_id (user_id),
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (service_id) REFERENCES services(id),
    FOREIGN KEY (area_id) REFERENCES service_areas(id)
);

-- Copies reviews customers already left on whole orders into per-product reviews.
INSERT INTO product_reviews (product_id, order_id, user_id, rating, comment, created_at)
SELECT oi.product_id, o.id, o.user_id, o.review_rating, o.review_comment, COALESCE(o.reviewed_at, o.created_at)
FROM orders o
JOIN order_items oi ON oi.order_id = o.id
WHERE o.review_rating IS NOT NULL AND o.user_id IS NOT NULL AND oi.product_id IS NOT NULL AND o.status = 'delivered'
  AND NOT EXISTS (SELECT 1 FROM product_reviews pr WHERE pr.order_id = o.id AND pr.product_id = oi.product_id);
