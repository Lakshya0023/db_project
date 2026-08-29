-- =========================================================
-- SUPPLY CHAIN AND WAREHOUSE MANAGEMENT SYSTEM
-- PostgreSQL Schema
-- =========================================================

DROP TABLE IF EXISTS shipments CASCADE;
DROP TABLE IF EXISTS sales_order_items CASCADE;
DROP TABLE IF EXISTS sales_orders CASCADE;
DROP TABLE IF EXISTS purchase_order_items CASCADE;
DROP TABLE IF EXISTS purchase_orders CASCADE;
DROP TABLE IF EXISTS inventory CASCADE;
DROP TABLE IF EXISTS products CASCADE;
DROP TABLE IF EXISTS suppliers CASCADE;
DROP TABLE IF EXISTS warehouses CASCADE;
DROP TABLE IF EXISTS users CASCADE;

-- ---------------------------------------------------------
-- USERS (Admin / Staff / Supplier login)
-- ---------------------------------------------------------
CREATE TABLE users (
    user_id       SERIAL PRIMARY KEY,
    name          VARCHAR(100) NOT NULL,
    email         VARCHAR(150) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role          VARCHAR(20) NOT NULL CHECK (role IN ('admin', 'staff', 'supplier')),
    created_at    TIMESTAMP DEFAULT NOW()
);

-- ---------------------------------------------------------
-- SUPPLIERS
-- ---------------------------------------------------------
CREATE TABLE suppliers (
    supplier_id   SERIAL PRIMARY KEY,
    name          VARCHAR(150) NOT NULL,
    contact_email VARCHAR(150),
    contact_phone VARCHAR(20),
    address       TEXT,
    created_at    TIMESTAMP DEFAULT NOW()
);

-- ---------------------------------------------------------
-- WAREHOUSES
-- ---------------------------------------------------------
CREATE TABLE warehouses (
    warehouse_id SERIAL PRIMARY KEY,
    name         VARCHAR(150) NOT NULL,
    location     VARCHAR(255),
    capacity     INT CHECK (capacity >= 0),
    created_at   TIMESTAMP DEFAULT NOW()
);

-- ---------------------------------------------------------
-- PRODUCTS
-- ---------------------------------------------------------
CREATE TABLE products (
    product_id     SERIAL PRIMARY KEY,
    sku            VARCHAR(50) UNIQUE NOT NULL,
    name           VARCHAR(150) NOT NULL,
    description    TEXT,
    unit_price     NUMERIC(10, 2) NOT NULL CHECK (unit_price >= 0),
    reorder_level  INT DEFAULT 10 CHECK (reorder_level >= 0),
    supplier_id    INT REFERENCES suppliers(supplier_id) ON DELETE SET NULL,
    created_at     TIMESTAMP DEFAULT NOW()
);

-- ---------------------------------------------------------
-- INVENTORY (stock of a product at a specific warehouse)
-- ---------------------------------------------------------
CREATE TABLE inventory (
    inventory_id  SERIAL PRIMARY KEY,
    product_id    INT NOT NULL REFERENCES products(product_id) ON DELETE CASCADE,
    warehouse_id  INT NOT NULL REFERENCES warehouses(warehouse_id) ON DELETE CASCADE,
    quantity      INT NOT NULL DEFAULT 0 CHECK (quantity >= 0),
    UNIQUE (product_id, warehouse_id)
);

-- ---------------------------------------------------------
-- PURCHASE ORDERS (Warehouse buys from Supplier)
-- ---------------------------------------------------------
CREATE TABLE purchase_orders (
    po_id         SERIAL PRIMARY KEY,
    supplier_id   INT NOT NULL REFERENCES suppliers(supplier_id),
    warehouse_id  INT NOT NULL REFERENCES warehouses(warehouse_id),
    status        VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending','received','cancelled')),
    order_date    TIMESTAMP DEFAULT NOW()
);

CREATE TABLE purchase_order_items (
    po_item_id  SERIAL PRIMARY KEY,
    po_id       INT NOT NULL REFERENCES purchase_orders(po_id) ON DELETE CASCADE,
    product_id  INT NOT NULL REFERENCES products(product_id),
    quantity    INT NOT NULL CHECK (quantity > 0),
    unit_cost   NUMERIC(10, 2) NOT NULL CHECK (unit_cost >= 0)
);

-- ---------------------------------------------------------
-- SALES ORDERS (Warehouse sells to Customer)
-- ---------------------------------------------------------
CREATE TABLE sales_orders (
    so_id         SERIAL PRIMARY KEY,
    customer_name VARCHAR(150) NOT NULL,
    warehouse_id  INT NOT NULL REFERENCES warehouses(warehouse_id),
    status        VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending','fulfilled','cancelled')),
    order_date    TIMESTAMP DEFAULT NOW()
);

CREATE TABLE sales_order_items (
    so_item_id  SERIAL PRIMARY KEY,
    so_id       INT NOT NULL REFERENCES sales_orders(so_id) ON DELETE CASCADE,
    product_id  INT NOT NULL REFERENCES products(product_id),
    quantity    INT NOT NULL CHECK (quantity > 0),
    unit_price  NUMERIC(10, 2) NOT NULL CHECK (unit_price >= 0)
);

-- ---------------------------------------------------------
-- SHIPMENTS (tracks fulfillment of sales orders)
-- ---------------------------------------------------------
CREATE TABLE shipments (
    shipment_id     SERIAL PRIMARY KEY,
    so_id           INT NOT NULL REFERENCES sales_orders(so_id) ON DELETE CASCADE,
    carrier         VARCHAR(100),
    tracking_number VARCHAR(100),
    status          VARCHAR(20) DEFAULT 'preparing' CHECK (status IN ('preparing','shipped','delivered')),
    shipped_date    TIMESTAMP,
    delivered_date  TIMESTAMP
);

-- ---------------------------------------------------------
-- SAMPLE DATA
-- ---------------------------------------------------------
INSERT INTO warehouses (name, location, capacity) VALUES
('Central Warehouse', 'Chennai, TN', 10000),
('North Depot', 'Delhi, DL', 5000);

INSERT INTO suppliers (name, contact_email, contact_phone, address) VALUES
('Acme Traders', 'contact@acme.com', '9876543210', 'Mumbai, MH'),
('Global Parts Co.', 'sales@globalparts.com', '9123456780', 'Bangalore, KA');

INSERT INTO products (sku, name, description, unit_price, reorder_level, supplier_id) VALUES
('SKU-1001', 'Steel Bolt 10mm', 'Pack of 100', 250.00, 20, 1),
('SKU-1002', 'Ball Bearing 6mm', 'Pack of 50', 480.00, 15, 2),
('SKU-1003', 'Hydraulic Hose 2m', 'Reinforced rubber hose', 950.00, 10, 1);

INSERT INTO inventory (product_id, warehouse_id, quantity) VALUES
(1, 1, 100),
(2, 1, 40),
(3, 2, 8);   -- below reorder_level -> triggers low-stock report

-- Sample admin user (password: "admin123" -- hash this properly in real app)
INSERT INTO users (name, email, password_hash, role) VALUES
('Admin User', 'admin@warehouse.com', '$2b$10$replace_with_real_bcrypt_hash', 'admin');
