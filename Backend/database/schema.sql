-- =====================================================================
-- Multi-Agent Customer Support System — Schema
-- Tables: customers, orders, support_tickets
-- Target: Supabase (PostgreSQL 15+)
-- =====================================================================

-- Clean slate (safe for dev; remove for production)
DROP TABLE IF EXISTS support_tickets CASCADE;
DROP TABLE IF EXISTS orders CASCADE;
DROP TABLE IF EXISTS customers CASCADE;

-- ---------------------------------------------------------------------
-- customers
-- ---------------------------------------------------------------------
CREATE TABLE customers (
    id              BIGSERIAL PRIMARY KEY,
    full_name       TEXT        NOT NULL,
    email           TEXT        NOT NULL UNIQUE,
    phone           TEXT,
    address         TEXT,
    city            TEXT,
    country         TEXT,
    loyalty_tier    TEXT        NOT NULL DEFAULT 'standard'
                    CHECK (loyalty_tier IN ('standard','silver','gold','platinum')),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_customers_email ON customers(email);

-- ---------------------------------------------------------------------
-- orders
-- ---------------------------------------------------------------------
CREATE TABLE orders (
    id              BIGSERIAL PRIMARY KEY,
    customer_id     BIGINT      NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    product_name    TEXT        NOT NULL,
    quantity        INTEGER     NOT NULL CHECK (quantity > 0),
    unit_price      NUMERIC(10,2) NOT NULL CHECK (unit_price >= 0),
    total_amount    NUMERIC(10,2) GENERATED ALWAYS AS (quantity * unit_price) STORED,
    status          TEXT        NOT NULL DEFAULT 'pending'
                    CHECK (status IN ('pending','processing','shipped','delivered','cancelled','returned')),
    order_date      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    tracking_number TEXT
);

CREATE INDEX idx_orders_customer_id ON orders(customer_id);
CREATE INDEX idx_orders_status      ON orders(status);

-- ---------------------------------------------------------------------
-- support_tickets
-- ---------------------------------------------------------------------
CREATE TABLE support_tickets (
    id              BIGSERIAL PRIMARY KEY,
    customer_id     BIGINT      NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    order_id        BIGINT      REFERENCES orders(id) ON DELETE SET NULL,
    subject         TEXT        NOT NULL,
    description     TEXT        NOT NULL,
    category        TEXT        NOT NULL
                    CHECK (category IN ('billing','shipping','product','technical','refund','general')),
    priority        TEXT        NOT NULL DEFAULT 'medium'
                    CHECK (priority IN ('low','medium','high','urgent')),
    status          TEXT        NOT NULL DEFAULT 'open'
                    CHECK (status IN ('open','in_progress','waiting_customer','resolved','closed')),
    assigned_agent  TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_tickets_customer_id ON support_tickets(customer_id);
CREATE INDEX idx_tickets_order_id    ON support_tickets(order_id);
CREATE INDEX idx_tickets_status      ON support_tickets(status);

-- Keep updated_at fresh
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_support_tickets_updated_at
BEFORE UPDATE ON support_tickets
FOR EACH ROW EXECUTE FUNCTION set_updated_at();


-- =====================================================================
-- SEED DATA — 15 rows per table
-- =====================================================================

-- -------- customers (15) ---------------------------------------------
INSERT INTO customers (full_name, email, phone, address, city, country, loyalty_tier) VALUES
('Alice Johnson',    'alice.johnson@example.com',   '+1-415-555-0101', '221B Baker St',       'San Francisco', 'USA',     'gold'),
('Bob Smith',        'bob.smith@example.com',       '+1-212-555-0102', '456 Park Ave',        'New York',      'USA',     'silver'),
('Carla Gomez',      'carla.gomez@example.com',     '+34-91-555-0103', 'Calle Mayor 12',      'Madrid',        'Spain',   'standard'),
('David Lee',        'david.lee@example.com',       '+82-2-555-0104',  '77 Gangnam-daero',    'Seoul',         'Korea',   'platinum'),
('Evelyn Brown',     'evelyn.brown@example.com',    '+44-20-555-0105', '10 Downing Close',    'London',        'UK',      'gold'),
('Farhan Ali',       'farhan.ali@example.com',      '+971-4-555-0106', 'Sheikh Zayed Rd 88',  'Dubai',         'UAE',     'silver'),
('Grace Chen',       'grace.chen@example.com',      '+65-6555-0107',   '5 Orchard Blvd',      'Singapore',     'Singapore','standard'),
('Henry Walker',     'henry.walker@example.com',    '+1-312-555-0108', '900 Michigan Ave',    'Chicago',       'USA',     'standard'),
('Isabella Rossi',   'isabella.rossi@example.com',  '+39-06-555-0109', 'Via Roma 45',         'Rome',          'Italy',   'gold'),
('Jamal Williams',   'jamal.williams@example.com',  '+1-404-555-0110', '12 Peachtree St',     'Atlanta',       'USA',     'silver'),
('Kenji Tanaka',     'kenji.tanaka@example.com',    '+81-3-555-0111',  '3-1 Shibuya',         'Tokyo',         'Japan',   'platinum'),
('Laura Martin',     'laura.martin@example.com',    '+33-1-555-0112',  '7 Rue de Rivoli',     'Paris',         'France',  'standard'),
('Mohammed Khan',    'm.khan@example.com',          '+92-21-555-0113', '55 Clifton Rd',       'Karachi',       'Pakistan','silver'),
('Nina Petrova',     'nina.petrova@example.com',    '+7-495-555-0114', 'Tverskaya Ul 9',      'Moscow',        'Russia',  'standard'),
('Oliver Dubois',    'oliver.dubois@example.com',   '+32-2-555-0115',  'Grand Place 1',       'Brussels',      'Belgium', 'gold');

-- -------- orders (15) ------------------------------------------------
INSERT INTO orders (customer_id, product_name, quantity, unit_price, status, order_date, tracking_number) VALUES
( 1, 'Wireless Noise-Cancelling Headphones', 1, 299.99, 'delivered',  NOW() - INTERVAL '30 days', 'TRK1001AAA'),
( 2, 'Smart LED Desk Lamp',                  2,  49.50, 'shipped',    NOW() - INTERVAL '10 days', 'TRK1002BBB'),
( 3, '4K Action Camera',                     1, 399.00, 'processing', NOW() - INTERVAL '3 days',  NULL),
( 4, 'Mechanical Keyboard',                  1, 159.95, 'delivered',  NOW() - INTERVAL '45 days', 'TRK1004CCC'),
( 5, 'Yoga Mat Pro',                         3,  35.00, 'delivered',  NOW() - INTERVAL '60 days', 'TRK1005DDD'),
( 6, 'Ergonomic Office Chair',               1, 429.00, 'returned',   NOW() - INTERVAL '25 days', 'TRK1006EEE'),
( 7, 'Portable Bluetooth Speaker',           2,  79.99, 'delivered',  NOW() - INTERVAL '20 days', 'TRK1007FFF'),
( 8, 'Fitness Smartwatch',                   1, 249.00, 'cancelled',  NOW() - INTERVAL '15 days', NULL),
( 9, 'Espresso Machine',                     1, 549.00, 'delivered',  NOW() - INTERVAL '40 days', 'TRK1009GGG'),
(10, 'Running Shoes (Size 10)',              1, 129.99, 'shipped',    NOW() - INTERVAL '6 days',  'TRK1010HHH'),
(11, 'Gaming Monitor 27"',                   1, 379.00, 'pending',    NOW() - INTERVAL '1 day',   NULL),
(12, 'Leather Messenger Bag',                1, 189.50, 'delivered',  NOW() - INTERVAL '22 days', 'TRK1012III'),
(13, 'Wireless Charger Pad',                 4,  25.00, 'delivered',  NOW() - INTERVAL '18 days', 'TRK1013JJJ'),
(14, 'Electric Toothbrush',                  2,  89.90, 'shipped',    NOW() - INTERVAL '4 days',  'TRK1014KKK'),
(15, 'Drone with 4K Camera',                 1, 899.00, 'processing', NOW() - INTERVAL '2 days',  NULL);

-- -------- support_tickets (15) ---------------------------------------
INSERT INTO support_tickets
    (customer_id, order_id, subject, description, category, priority, status, assigned_agent, created_at) VALUES
( 1,  1, 'Right earcup intermittent static',     'After 30 days the right side crackles at high volume.',                 'product',   'medium', 'in_progress',     'agent_product',   NOW() - INTERVAL '5 days'),
( 2,  2, 'Received only 1 of 2 lamps',           'Order shows 2 units but package contained 1. Need the missing unit.',   'shipping',  'high',   'open',            'agent_shipping',  NOW() - INTERVAL '2 days'),
( 3,  3, 'When will my camera ship?',            'Order still processing after 3 days. Requesting ETA.',                  'shipping',  'low',    'waiting_customer','agent_shipping',  NOW() - INTERVAL '1 day'),
( 4,  4, 'Keyboard key not registering',         'The "E" key requires multiple presses. Firmware updated already.',      'technical', 'medium', 'open',            'agent_technical', NOW() - INTERVAL '7 days'),
( 5,  5, 'Refund request for 3rd mat',           'One mat was duplicate of a previous order. Please refund one unit.',    'refund',    'medium', 'resolved',        'agent_billing',   NOW() - INTERVAL '20 days'),
( 6,  6, 'Chair return — pickup pending',        'Return initiated but no pickup scheduled yet. Driver never arrived.',   'shipping',  'high',   'in_progress',     'agent_shipping',  NOW() - INTERVAL '12 days'),
( 7,  7, 'Speaker battery drains in 2 hours',    'Advertised 10h runtime; getting ~2h. Possible defective battery.',      'product',   'high',   'open',            'agent_product',   NOW() - INTERVAL '3 days'),
( 8,  8, 'Charge appears even though cancelled', 'Order cancelled but still see pending charge on card.',                 'billing',   'urgent', 'in_progress',     'agent_billing',   NOW() - INTERVAL '10 days'),
( 9,  9, 'How to descale espresso machine',      'Could not find descale instructions in the manual.',                    'general',   'low',    'resolved',        'agent_general',   NOW() - INTERVAL '35 days'),
(10, 10, 'Need to change shipping address',      'Moved last week. Please redirect to new address before delivery.',      'shipping',  'urgent', 'open',            'agent_shipping',  NOW() - INTERVAL '6 hours'),
(11, 11, 'Can I add a second monitor to order?', 'Would like to add another unit before shipping and combine shipping.',  'general',   'low',    'open',            'agent_general',   NOW() - INTERVAL '3 hours'),
(12, 12, 'Strap stitching came loose',           'Within 2 weeks the strap stitching unravelled near the buckle.',        'product',   'medium', 'waiting_customer','agent_product',   NOW() - INTERVAL '4 days'),
(13, 13, 'Chargers not working with phone',      'Two of the four chargers do not charge a Pixel 8.',                     'technical', 'medium', 'open',            'agent_technical', NOW() - INTERVAL '2 days'),
(14, 14, 'Missing replacement heads',            'Listing said 4 heads included; box contained 2.',                       'shipping',  'medium', 'resolved',        'agent_shipping',  NOW() - INTERVAL '1 day'),
(15, 15, 'Login issue on mobile app',            'Cannot log into drone companion app on iOS 18. Password reset failed.', 'technical', 'high',   'in_progress',     'agent_technical', NOW() - INTERVAL '8 hours');

-- =====================================================================
-- Quick verification
-- =====================================================================
-- SELECT 'customers'        AS table_name, COUNT(*) FROM customers
-- UNION ALL SELECT 'orders',          COUNT(*) FROM orders
-- UNION ALL SELECT 'support_tickets', COUNT(*) FROM support_tickets;
