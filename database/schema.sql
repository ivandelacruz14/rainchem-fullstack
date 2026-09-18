-- Rainchem database schema (MySQL / MariaDB)
-- Run with: mysql -u root -p < schema.sql

CREATE DATABASE IF NOT EXISTS rainchem CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE rainchem;

CREATE TABLE admins (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(120) NOT NULL,
    email VARCHAR(180) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(60) NOT NULL DEFAULT 'Admin',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(120) NOT NULL,
    email VARCHAR(180) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NULL,
    google_id VARCHAR(120) NULL UNIQUE,
    phone VARCHAR(30) NULL,
    verified TINYINT(1) NOT NULL DEFAULT 0,
    address_line1 VARCHAR(200) NULL,
    address_city VARCHAR(100) NULL,
    address_province VARCHAR(100) NULL,
    address_region VARCHAR(100) NULL,
    address_zip VARCHAR(20) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE email_verifications (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    code VARCHAR(10) NOT NULL,
    expires_at DATETIME NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE password_resets (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    token VARCHAR(120) NOT NULL UNIQUE,
    expires_at DATETIME NOT NULL,
    used TINYINT(1) NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE products (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    category VARCHAR(80) NOT NULL,
    price DECIMAL(10,2) NOT NULL,
    stock INT NOT NULL DEFAULT 0,
    rating DECIMAL(2,1) NOT NULL DEFAULT 4.5,
    reviews INT NOT NULL DEFAULT 0,
    image_glyph VARCHAR(60) NULL,
    image_photo LONGTEXT NULL,
    short_desc VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    specs JSON NULL,
    benefits JSON NULL,
    usage_steps JSON NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE orders (
    id INT AUTO_INCREMENT PRIMARY KEY,
    order_number VARCHAR(40) NOT NULL UNIQUE,
    user_id INT NULL,
    status ENUM('pending_confirmation','confirmed','processing','shipped','delivered','cancelled')
        NOT NULL DEFAULT 'pending_confirmation',
    tracking_number VARCHAR(40) NOT NULL,
    customer_name VARCHAR(150) NOT NULL,
    customer_phone VARCHAR(30) NOT NULL,
    customer_email VARCHAR(180) NOT NULL,
    address_line1 VARCHAR(200) NOT NULL,
    address_city VARCHAR(100) NOT NULL,
    address_province VARCHAR(100) NOT NULL,
    address_region VARCHAR(100) NOT NULL,
    address_zip VARCHAR(20) NOT NULL,
    payment_method VARCHAR(60) NOT NULL,
    subtotal DECIMAL(10,2) NOT NULL,
    shipping_fee DECIMAL(10,2) NOT NULL,
    total DECIMAL(10,2) NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    confirmed_at DATETIME NULL,
    cancelled_at DATETIME NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);

CREATE TABLE order_items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    order_id INT NOT NULL,
    product_id INT NULL,
    product_name VARCHAR(200) NOT NULL,
    unit_price DECIMAL(10,2) NOT NULL,
    discount_rate DECIMAL(4,2) NOT NULL DEFAULT 0,
    quantity INT NOT NULL,
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE SET NULL
);

CREATE TABLE order_status_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    order_id INT NOT NULL,
    status VARCHAR(40) NOT NULL,
    changed_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE
);

CREATE TABLE receipts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    order_id INT NOT NULL UNIQUE,
    receipt_number VARCHAR(40) NOT NULL UNIQUE,
    issued_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    items_snapshot JSON NOT NULL,
    subtotal DECIMAL(10,2) NOT NULL,
    shipping_fee DECIMAL(10,2) NOT NULL,
    total DECIMAL(10,2) NOT NULL,
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE
);

CREATE TABLE knowledge_base (
    id INT AUTO_INCREMENT PRIMARY KEY,
    question VARCHAR(500) NOT NULL,
    answer TEXT NOT NULL,
    category VARCHAR(80) NOT NULL,
    status ENUM('pending','approved') NOT NULL DEFAULT 'pending',
    hits INT NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE chat_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    question VARCHAR(500) NOT NULL,
    answer TEXT NOT NULL,
    matched_knowledge_id INT NULL,
    confidence INT NOT NULL DEFAULT 0,
    resolved TINYINT(1) NOT NULL DEFAULT 0,
    user_id INT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (matched_knowledge_id) REFERENCES knowledge_base(id) ON DELETE SET NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);

CREATE TABLE notifications (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NULL,
    channel VARCHAR(20) NOT NULL DEFAULT 'email',
    subject VARCHAR(200) NOT NULL,
    body TEXT NOT NULL,
    sent_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);

-- Seed data
-- Admin and demo customer accounts are created separately by
-- backend/seed.py so their passwords go through proper hashing.

INSERT INTO products (name, category, price, stock, rating, reviews, image_glyph, short_desc, description, specs, benefits, usage_steps) VALUES
('RAIMOL FLASH 4T Fully Synthetic 10W-40 Engine Oil', 'Oils & Fluids', 585.00, 140, 4.8, 212, 'oil-synthetic',
 'Full synthetic protection for high-revving 4-stroke engines.',
 'RAIMOL FLASH 4T is engineered for modern air- and liquid-cooled 4-stroke motorcycle engines. Maintains viscosity under high RPM and high heat, protects against clutch slip (JASO MA2 certified), and keeps your engine cleaner for longer between services.',
 JSON_ARRAY('Viscosity: 10W-40', 'JASO MA2 / API SL certified', 'Volume: 1 Liter', 'Recommended interval: every 3,000 km'),
 JSON_ARRAY('Maintains full engine power in stop-and-go traffic', 'Reduces carbon build-up with an added Oil Stabilizer', 'Protects wet clutch systems, no slip or glazing'),
 JSON_ARRAY('Warm up the engine for 2-3 minutes before draining old oil', 'Drain fully, replace the oil filter, then refill to the dipstick full mark', 'Recheck the level after a short ride and top up if needed')),

('RAIMOL FLASH 4T Semi-Synthetic 20W-50 Engine Oil', 'Oils & Fluids', 320.00, 200, 4.6, 165, 'oil-semi',
 'Everyday protection for carbureted and fuel-injected engines.',
 'A reliable semi-synthetic blend from the RAIMOL FLASH line for daily commuting and everyday riding. Good film strength for older engines and hot climates.',
 JSON_ARRAY('Viscosity: 20W-50', 'JASO MA / API SG', 'Volume: 1 Liter', 'Recommended interval: every 2,000 km'),
 JSON_ARRAY('Budget-friendly protection for daily commuters', 'Strong oil film for older, higher-mileage engines'),
 JSON_ARRAY('Change every 2,000 km or 2 months, whichever comes first', 'Check level weekly if riding daily in heavy traffic')),

('RAIMOL RadCool Concentrate Coolant (Red)', 'Coolant', 245.00, 180, 4.9, 301, 'coolant-red',
 'High-performance concentrate coolant. Mix 1:1 with distilled water.',
 'RAIMOL RadCool is a high-performance synthetic coolant formulated with a Cooling System Conditioner that reduces surface tension to help lower engine temperatures. Concentrate must be diluted before use.',
 JSON_ARRAY('Type: Concentrate (dilute 1:1)', 'Color: Red', 'Volume: 1 Liter', 'Boiling point (diluted): ~108C'),
 JSON_ARRAY('Cooling System Conditioner lowers surface tension for better heat transfer', 'Corrosion inhibitors safe for aluminum radiators'),
 JSON_ARRAY('Dilute 1:1 with distilled or de-ionized water, never tap water', 'Only fill when the engine is cool')),

('RAIMOL RadCool Ready-To-Use Coolant (Red)', 'Coolant', 195.00, 150, 4.7, 189, 'coolant-ready',
 'Pre-mixed and ready to pour, no dilution needed.',
 'The convenient pre-mixed version of RAIMOL RadCool. Pour directly into the radiator reservoir up to the full mark.',
 JSON_ARRAY('Type: Ready-to-use (pre-mixed)', 'Color: Red', 'Volume: 1 Liter'),
 JSON_ARRAY('No mixing or measuring required', 'Same corrosion protection as the concentrate formula'),
 JSON_ARRAY('Only open the reservoir cap when the engine is cool', 'Top up to the full line, do not overfill')),

('RAIMOL TriboFilm Chain & Component Lubricant', 'Accessories', 210.00, 220, 4.5, 98, 'chain-lube',
 'Anti-wear formula that minimizes metal-to-metal contact.',
 'RAIMOL TriboFilm is a wax-based chain lubricant built on anti-wear additive technology. It minimizes direct metal-to-metal rubbing, extending chain and sprocket life.',
 JSON_ARRAY('Format: 400ml aerosol', 'Safe for O-ring / X-ring chains', 'Apply every 300-500 km'),
 JSON_ARRAY('Anti-wear technology reduces metal-to-metal contact', 'Resists fling-off and water wash-off at highway speed'),
 JSON_ARRAY('Apply to a warm chain right after a ride', 'Wipe excess after 10-15 minutes')),

('RAIMOL Oil Filter (Universal Fit A)', 'Filters', 145.00, 260, 4.6, 143, 'oil-filter',
 'OEM-spec spin-on oil filter for common 125cc-160cc models.',
 'Precision-pleated filter media rated to trap particles as small as 15 microns, protecting your engine internals during every oil change.',
 JSON_ARRAY('Fits most 125cc-160cc engines', 'Filtration: 15 microns'),
 JSON_ARRAY('Traps contaminants as small as 15 microns'),
 JSON_ARRAY('Always replace at every full oil change', 'Hand-tighten only')),

('RAIMOL Air Filter (Foam, Washable)', 'Filters', 175.00, 190, 4.4, 76, 'air-filter',
 'Reusable foam air filter, clean, oil, and reuse.',
 'A washable dual-layer foam filter designed to be cleaned and re-oiled instead of replaced.',
 JSON_ARRAY('Type: Foam, washable', 'Clean every 3,000-5,000 km'),
 JSON_ARRAY('Reusable, saves money over disposable filters'),
 JSON_ARRAY('Wash in mild detergent, rinse, and air dry fully')),

('RAIMOL Ceramic Brake Pads (Front)', 'Brakes', 390.00, 130, 4.7, 121, 'brake-pads',
 'Low-dust ceramic compound for consistent stopping power.',
 'Ceramic composite pads offering quieter operation, less brake dust, and stable performance in wet and dry conditions.',
 JSON_ARRAY('Compound: Ceramic', 'Position: Front'),
 JSON_ARRAY('Low-dust ceramic compound keeps wheels cleaner'),
 JSON_ARRAY('Bed in new pads with gradual braking for the first 100 km')),

('RAIMOL DOT 4 Brake Fluid', 'Oils & Fluids', 165.00, 210, 4.8, 88, 'brake-fluid',
 'High boiling point brake fluid for hydraulic disc systems.',
 'DOT 4 glycol-based brake fluid with a high dry boiling point, recommended for hydraulic disc brake and clutch systems.',
 JSON_ARRAY('Type: DOT 4', 'Volume: 500ml'),
 JSON_ARRAY('High dry boiling point resists brake fade'),
 JSON_ARRAY('Never mix DOT 4 with DOT 5 silicone-based fluid')),

('Oil Change Service (Labor + Disposal)', 'Services', 150.00, 999, 4.9, 410, 'service-oil',
 'Professional oil change service at our partner service bays.',
 'Book a professional oil change at any Rainchem partner shop. Price covers labor and proper used-oil disposal.',
 JSON_ARRAY('Duration: ~20-30 mins', 'Includes labor and eco disposal'),
 JSON_ARRAY('Certified technicians at every partner bay'),
 JSON_ARRAY('Bring your order confirmation and plate number')),

('Radiator Flush & RadCool Service', 'Services', 250.00, 999, 4.8, 152, 'service-coolant',
 'Full radiator flush and RadCool refill service.',
 'We drain your old coolant, flush the system, and refill with RAIMOL RadCool to manufacturer-recommended levels.',
 JSON_ARRAY('Duration: ~30-45 mins', 'Includes flush and 1L RadCool'),
 JSON_ARRAY('Removes old, degraded coolant and built-up scale'),
 JSON_ARRAY('Best done every 12 months or 10,000 km')),

('RAIMOL Titanium Iridium Spark Plug', 'Accessories', 220.00, 175, 4.6, 64, 'spark-plug',
 'Iridium-tipped plug for improved ignition and fuel economy.',
 'A fine iridium center electrode gives a more consistent spark, smoother idle, and better fuel efficiency.',
 JSON_ARRAY('Type: Iridium', 'Fits most 110cc-160cc engines'),
 JSON_ARRAY('Finer iridium tip for a more consistent spark'),
 JSON_ARRAY('Gap the plug to manufacturer spec before installing'));

INSERT INTO knowledge_base (question, answer, category, status, hits) VALUES
('How often should I change my motorcycle oil?', 'For fully synthetic oil, we recommend changing it every 3,000 km or 3 months, whichever comes first. For semi-synthetic oil, change it every 2,000 km. Riding mostly in stop-and-go traffic or hot weather can shorten this interval.', 'Oil & Maintenance', 'approved', 34),
('How do I mix RadCool concentrate coolant?', 'RadCool Concentrate should be diluted 1:1 with distilled or de-ionized water before use, never tap water, since minerals can cause corrosion. We also carry RadCool Ready-To-Use if you prefer not to mix it yourself.', 'Coolant', 'approved', 27),
('Can I mix RadCool with other brands of coolant?', 'We do not recommend mixing coolant brands. Different coolants use different corrosion-inhibitor chemistry, and mixing them can reduce protection or cause a gel-like precipitate to form. Fully flush the old coolant before switching.', 'Coolant', 'approved', 19),
('What is the difference between fully synthetic and semi-synthetic oil?', 'Fully synthetic oil is chemically engineered for more consistent molecule size, giving better performance at high temperatures and longer intervals between changes. Semi-synthetic is a blend of synthetic and mineral oil, more affordable, and still solid for everyday commuting.', 'Oil & Maintenance', 'approved', 22),
('How long does delivery take?', 'Metro Manila orders typically arrive within 1-2 business days. Provincial orders take 3-5 business days depending on the courier and location. You can track your order anytime from My Orders using your tracking number.', 'Orders & Shipping', 'approved', 41),
('What payment methods do you accept?', 'We currently accept Cash on Delivery, GCash, and major debit or credit cards at checkout.', 'Orders & Shipping', 'approved', 30),
('Do you offer installation or service for the products I buy?', 'Yes. You can add an Oil Change Service or Radiator Flush & Coolant Service to your cart alongside your parts. Our partner service bays handle installation.', 'Services', 'approved', 15),
('Does RadCool coolant expire?', 'Unopened RadCool concentrate has a shelf life of about 3 years from the manufacture date. Once diluted and installed in a radiator, we recommend replacing it every 12 months or 10,000 km.', 'Coolant', 'pending', 4),
('Can I use car engine oil in my motorcycle?', 'It is not recommended. Car oils often contain friction modifiers meant to save fuel, which can cause wet-clutch slippage in motorcycles. Always use a motorcycle-specific oil rated JASO MA or MA2.', 'Oil & Maintenance', 'pending', 6);
