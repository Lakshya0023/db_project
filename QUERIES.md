# Query Lab - SQL Reference

This file lists every SQL operation available in the **Query Lab** tab of the app (sidebar → *Database → Query Lab*), generated from the code so it always matches what runs.

| Type | Count | Where it lives |
|---|---|---|
| SELECT | 22 | `controllers/query_lab_controller.py` → `SELECT_QUERIES` |
| INSERT | 5 | `controllers/query_lab_controller.py` → `DML_CATALOG` (I1-I5) |
| UPDATE | 5 | `controllers/query_lab_controller.py` → `DML_CATALOG` (U1-U5) |

`:name` marks a bound parameter - values are passed to the driver separately, never concatenated into the SQL.

**Try it:** click *Load demo data* in the Query Lab (or run `python seed_demo_data.py`) so every report has data, then press *Run*. REST access: `GET /api/query-lab/select/<id>`, `POST /api/query-lab/dml/<id>`.

---

## SELECT queries

| # | Query | Concept |
|---|---|---|
| Q1 | Premium products above a price | WHERE + ORDER BY + LEFT JOIN |
| Q2 | Search products by name or SKU | LIKE pattern matching |
| Q3 | Inventory matrix (product x warehouse) | 3-table INNER JOIN |
| Q4 | Low-stock report | LEFT JOIN + GROUP BY + HAVING |
| Q5 | Warehouse capacity utilisation | Aggregate + computed percentage |
| Q6 | Products supplied by each supplier | LEFT JOIN + COUNT + AVG |
| Q7 | Stock value per warehouse | SUM over an expression (qty x price) |
| Q8 | Products that have never been sold | NOT EXISTS (correlated subquery) |
| Q9 | Top 5 best-selling products | JOIN + GROUP BY + ORDER BY + LIMIT |
| Q10 | Revenue by customer | GROUP BY + COUNT DISTINCT + SUM |
| Q11 | Pending purchase orders with totals | Multi-table JOIN + SUM |
| Q12 | Sales orders above the average order value | HAVING with a derived-table subquery |
| Q13 | Products priced above the catalogue average | Scalar subquery |
| Q14 | Products stocked in more than one warehouse | HAVING COUNT(DISTINCT ...) |
| Q15 | Shipments currently in transit | 4-table JOIN with filter |
| Q16 | Carrier performance summary | Conditional aggregation (SUM + CASE) |
| Q17 | Monthly sales revenue | GROUP BY on a derived expression (SUBSTR) |
| Q18 | Gross margin per product | Two derived tables joined together |
| Q19 | Can pending sales orders be fulfilled? | LEFT JOIN + CASE + string concatenation |
| Q20 | Suppliers ranked by purchase spend | Aggregate over 3 joined tables |
| Q21 | Recent order activity feed | UNION ALL |
| Q22 | Orders that contain a given product | IN (subquery) with a parameter |

### Q1. Premium products above a price

*WHERE + ORDER BY + LEFT JOIN* - Lists products priced at or above a minimum, most expensive first, with their supplier.

Parameters: `min_price` (default `500`)

```sql
SELECT p.sku, p.name, p.unit_price, s.name AS supplier
FROM products p
LEFT JOIN suppliers s ON s.supplier_id = p.supplier_id
WHERE p.unit_price >= :min_price
ORDER BY p.unit_price DESC
```

### Q2. Search products by name or SKU

*LIKE pattern matching* - Case-insensitive partial match on product name or SKU.

Parameters: `term` (default `steel`)

```sql
SELECT p.product_id, p.sku, p.name, p.description, p.unit_price
FROM products p
WHERE LOWER(p.name) LIKE LOWER(:term)
   OR LOWER(p.sku)  LIKE LOWER(:term)
ORDER BY p.name
```

### Q3. Inventory matrix (product x warehouse)

*3-table INNER JOIN* - Every stock record joined with its product and warehouse names.

```sql
SELECT w.name AS warehouse, p.sku, p.name AS product, i.quantity
FROM inventory i
JOIN products   p ON p.product_id   = i.product_id
JOIN warehouses w ON w.warehouse_id = i.warehouse_id
ORDER BY w.name, p.name
```

### Q4. Low-stock report

*LEFT JOIN + GROUP BY + HAVING* - Products whose total stock across all warehouses is at or below the reorder level.

```sql
SELECT p.sku, p.name, p.reorder_level,
       COALESCE(SUM(i.quantity), 0) AS total_stock
FROM products p
LEFT JOIN inventory i ON i.product_id = p.product_id
GROUP BY p.product_id, p.sku, p.name, p.reorder_level
HAVING COALESCE(SUM(i.quantity), 0) <= p.reorder_level
ORDER BY total_stock
```

### Q5. Warehouse capacity utilisation

*Aggregate + computed percentage* - Units stored vs. capacity for each warehouse, as a percentage.

```sql
SELECT w.name AS warehouse, w.capacity,
       COALESCE(SUM(i.quantity), 0) AS units_stored,
       ROUND(100.0 * COALESCE(SUM(i.quantity), 0) / NULLIF(w.capacity, 0), 2) AS utilisation_pct
FROM warehouses w
LEFT JOIN inventory i ON i.warehouse_id = w.warehouse_id
GROUP BY w.warehouse_id, w.name, w.capacity
ORDER BY utilisation_pct DESC
```

### Q6. Products supplied by each supplier

*LEFT JOIN + COUNT + AVG* - Number of products and average price per supplier (suppliers with no products show 0).

```sql
SELECT s.name AS supplier,
       COUNT(p.product_id) AS products_supplied,
       COALESCE(ROUND(AVG(p.unit_price), 2), 0) AS avg_price
FROM suppliers s
LEFT JOIN products p ON p.supplier_id = s.supplier_id
GROUP BY s.supplier_id, s.name
ORDER BY products_supplied DESC, s.name
```

### Q7. Stock value per warehouse

*SUM over an expression (qty x price)* - Total rupee value of the stock held in every warehouse.

```sql
SELECT w.name AS warehouse,
       COUNT(DISTINCT i.product_id)               AS distinct_products,
       COALESCE(SUM(i.quantity), 0)               AS units,
       COALESCE(SUM(i.quantity * p.unit_price), 0) AS stock_value
FROM warehouses w
LEFT JOIN inventory i ON i.warehouse_id = w.warehouse_id
LEFT JOIN products  p ON p.product_id   = i.product_id
GROUP BY w.warehouse_id, w.name
ORDER BY stock_value DESC
```

### Q8. Products that have never been sold

*NOT EXISTS (correlated subquery)* - Catalogue items that do not appear on any sales order line.

```sql
SELECT p.sku, p.name, p.unit_price
FROM products p
WHERE NOT EXISTS (
    SELECT 1
    FROM sales_order_items soi
    WHERE soi.product_id = p.product_id
)
ORDER BY p.name
```

### Q9. Top 5 best-selling products

*JOIN + GROUP BY + ORDER BY + LIMIT* - Units sold and revenue per product, ignoring cancelled orders.

```sql
SELECT p.sku, p.name,
       SUM(soi.quantity)                    AS units_sold,
       SUM(soi.quantity * soi.unit_price)   AS revenue
FROM sales_order_items soi
JOIN sales_orders so ON so.so_id      = soi.so_id
JOIN products     p  ON p.product_id  = soi.product_id
WHERE so.status <> 'cancelled'
GROUP BY p.product_id, p.sku, p.name
ORDER BY units_sold DESC
LIMIT 5
```

### Q10. Revenue by customer

*GROUP BY + COUNT DISTINCT + SUM* - Number of orders and total spend per customer (cancelled orders excluded).

```sql
SELECT so.customer_name,
       COUNT(DISTINCT so.so_id)             AS orders,
       SUM(soi.quantity * soi.unit_price)   AS total_spent
FROM sales_orders so
JOIN sales_order_items soi ON soi.so_id = so.so_id
WHERE so.status <> 'cancelled'
GROUP BY so.customer_name
ORDER BY total_spent DESC
```

### Q11. Pending purchase orders with totals

*Multi-table JOIN + SUM* - Open purchase orders with supplier, destination warehouse and total cost.

```sql
SELECT po.po_id, s.name AS supplier, w.name AS warehouse, po.order_date,
       COUNT(poi.po_item_id)                       AS line_items,
       COALESCE(SUM(poi.quantity * poi.unit_cost), 0) AS total_cost
FROM purchase_orders po
JOIN suppliers  s ON s.supplier_id  = po.supplier_id
JOIN warehouses w ON w.warehouse_id = po.warehouse_id
LEFT JOIN purchase_order_items poi ON poi.po_id = po.po_id
WHERE po.status = 'pending'
GROUP BY po.po_id, s.name, w.name, po.order_date
ORDER BY po.order_date
```

### Q12. Sales orders above the average order value

*HAVING with a derived-table subquery* - Orders whose total is greater than the average order total.

```sql
SELECT so.so_id, so.customer_name,
       SUM(soi.quantity * soi.unit_price) AS order_total
FROM sales_orders so
JOIN sales_order_items soi ON soi.so_id = so.so_id
WHERE so.status <> 'cancelled'
GROUP BY so.so_id, so.customer_name
HAVING SUM(soi.quantity * soi.unit_price) > (
    SELECT AVG(totals.order_total)
    FROM (
        SELECT SUM(quantity * unit_price) AS order_total
        FROM sales_order_items
        GROUP BY so_id
    ) AS totals
)
ORDER BY order_total DESC
```

### Q13. Products priced above the catalogue average

*Scalar subquery* - Items that cost more than the average unit price of all products.

```sql
SELECT sku, name, unit_price
FROM products
WHERE unit_price > (SELECT AVG(unit_price) FROM products)
ORDER BY unit_price DESC
```

### Q14. Products stocked in more than one warehouse

*HAVING COUNT(DISTINCT ...)* - Products that have stock in at least two different warehouses.

```sql
SELECT p.sku, p.name,
       COUNT(DISTINCT i.warehouse_id) AS warehouses_stocking,
       SUM(i.quantity)                AS total_units
FROM products p
JOIN inventory i ON i.product_id = p.product_id
WHERE i.quantity > 0
GROUP BY p.product_id, p.sku, p.name
HAVING COUNT(DISTINCT i.warehouse_id) > 1
ORDER BY total_units DESC
```

### Q15. Shipments currently in transit

*4-table JOIN with filter* - Shipped-but-not-delivered parcels with customer, origin warehouse and carrier.

```sql
SELECT sh.shipment_id, so.so_id, so.customer_name,
       w.name AS dispatched_from, sh.carrier, sh.tracking_number, sh.shipped_date
FROM shipments sh
JOIN sales_orders so ON so.so_id        = sh.so_id
JOIN warehouses   w  ON w.warehouse_id  = so.warehouse_id
WHERE sh.status = 'shipped'
ORDER BY sh.shipped_date
```

### Q16. Carrier performance summary

*Conditional aggregation (SUM + CASE)* - How many shipments each carrier has delivered, in transit and still preparing.

```sql
SELECT COALESCE(carrier, 'Unassigned') AS carrier,
       COUNT(*)                                          AS total_shipments,
       SUM(CASE WHEN status = 'delivered' THEN 1 ELSE 0 END) AS delivered,
       SUM(CASE WHEN status = 'shipped'   THEN 1 ELSE 0 END) AS in_transit,
       SUM(CASE WHEN status = 'preparing' THEN 1 ELSE 0 END) AS preparing
FROM shipments
GROUP BY COALESCE(carrier, 'Unassigned')
ORDER BY total_shipments DESC
```

### Q17. Monthly sales revenue

*GROUP BY on a derived expression (SUBSTR)* - Orders and revenue grouped by year-month of the order date.

```sql
SELECT SUBSTR(CAST(so.order_date AS VARCHAR), 1, 7) AS sale_month,
       COUNT(DISTINCT so.so_id)                     AS orders,
       SUM(soi.quantity * soi.unit_price)           AS revenue
FROM sales_orders so
JOIN sales_order_items soi ON soi.so_id = so.so_id
WHERE so.status <> 'cancelled'
GROUP BY sale_month
ORDER BY sale_month
```

### Q18. Gross margin per product

*Two derived tables joined together* - Average purchase cost vs. average selling price for products that were both bought and sold.

```sql
SELECT p.sku, p.name,
       ROUND(buy.avg_cost, 2)                    AS avg_purchase_cost,
       ROUND(sell.avg_price, 2)                  AS avg_selling_price,
       ROUND(sell.avg_price - buy.avg_cost, 2)   AS margin_per_unit
FROM products p
JOIN (SELECT product_id, AVG(unit_cost) AS avg_cost
      FROM purchase_order_items
      GROUP BY product_id) buy  ON buy.product_id  = p.product_id
JOIN (SELECT product_id, AVG(unit_price) AS avg_price
      FROM sales_order_items
      GROUP BY product_id) sell ON sell.product_id = p.product_id
ORDER BY margin_per_unit DESC
```

### Q19. Can pending sales orders be fulfilled?

*LEFT JOIN + CASE + string concatenation* - Compares each pending order line with stock in that order's warehouse.

```sql
SELECT so.so_id, so.customer_name, p.name AS product,
       soi.quantity AS requested,
       COALESCE(i.quantity, 0) AS in_stock,
       CASE
           WHEN COALESCE(i.quantity, 0) >= soi.quantity THEN 'Can fulfil'
           ELSE 'Short by ' || CAST(soi.quantity - COALESCE(i.quantity, 0) AS VARCHAR)
       END AS availability
FROM sales_orders so
JOIN sales_order_items soi ON soi.so_id = so.so_id
JOIN products p            ON p.product_id = soi.product_id
LEFT JOIN inventory i      ON i.product_id = soi.product_id
                          AND i.warehouse_id = so.warehouse_id
WHERE so.status = 'pending'
ORDER BY so.so_id, p.name
```

### Q20. Suppliers ranked by purchase spend

*Aggregate over 3 joined tables* - Total units and money spent with each supplier on received purchase orders.

```sql
SELECT s.name AS supplier,
       COUNT(DISTINCT po.po_id)           AS received_orders,
       SUM(poi.quantity)                  AS units_bought,
       SUM(poi.quantity * poi.unit_cost)  AS total_spend
FROM suppliers s
JOIN purchase_orders po       ON po.supplier_id = s.supplier_id
                             AND po.status = 'received'
JOIN purchase_order_items poi ON poi.po_id = po.po_id
GROUP BY s.supplier_id, s.name
ORDER BY total_spend DESC
```

### Q21. Recent order activity feed

*UNION ALL* - The 10 most recent purchase and sales orders combined into a single timeline.

```sql
SELECT 'Purchase Order' AS event_type, po_id AS ref_id, status, order_date AS event_date
FROM purchase_orders
UNION ALL
SELECT 'Sales Order', so_id, status, order_date
FROM sales_orders
ORDER BY event_date DESC
LIMIT 10
```

### Q22. Orders that contain a given product

*IN (subquery) with a parameter* - Which customers ordered a particular SKU, and in which orders.

Parameters: `sku` (default `SKU-1001`)

```sql
SELECT so.so_id, so.customer_name, so.status, so.order_date
FROM sales_orders so
WHERE so.so_id IN (
    SELECT soi.so_id
    FROM sales_order_items soi
    JOIN products p ON p.product_id = soi.product_id
    WHERE p.sku = :sku
)
ORDER BY so.order_date DESC
```

---

## INSERT operations

| # | Operation | Concept |
|---|---|---|
| I1 | Register a new supplier | INSERT ... VALUES (single row, RETURNING) |
| I2 | Onboard a product with opening stock | Two INSERTs in one transaction |
| I3 | Draft a restock purchase order | INSERT ... SELECT (bulk insert from a query) |
| I4 | Create shipments for fulfilled orders that have none | INSERT ... SELECT with NOT EXISTS |
| I5 | Initialise a warehouse's stock matrix | INSERT ... SELECT (cross product, skip existing) |

### I1. Register a new supplier

*INSERT ... VALUES (single row, RETURNING)* - Adds one supplier row and returns the stored record.

Inputs: `name`, `contact_email`, `contact_phone`, `address`

```sql
INSERT INTO suppliers (name, contact_email, contact_phone, address)
VALUES (:name, :contact_email, :contact_phone, :address)
RETURNING *
```

### I2. Onboard a product with opening stock

*Two INSERTs in one transaction* - Creates a product and its first inventory record atomically - if either insert fails, both are rolled back.

Inputs: `sku`, `name`, `description`, `unit_price`, `reorder_level`, `supplier_id`, `warehouse_id`, `opening_stock`

Statement 1:
```sql
INSERT INTO products (sku, name, description, unit_price, reorder_level, supplier_id)
VALUES (:sku, :name, :description, :unit_price, :reorder_level, :supplier_id)
RETURNING *
```

Statement 2:
```sql
INSERT INTO inventory (product_id, warehouse_id, quantity)
VALUES (:product_id, :warehouse_id, :opening_stock)
```

All statements run in **one transaction** - any failure rolls everything back.

### I3. Draft a restock purchase order

*INSERT ... SELECT (bulk insert from a query)* - Creates a pending purchase order and fills its lines automatically from every product of that supplier that is below its reorder level in the chosen warehouse.

Inputs: `supplier_id`, `warehouse_id`, `multiplier`

Statement 1:
```sql
INSERT INTO purchase_orders (supplier_id, warehouse_id, status)
VALUES (:supplier_id, :warehouse_id, 'pending')
RETURNING po_id
```

Statement 2:
```sql
INSERT INTO purchase_order_items (po_id, product_id, quantity, unit_cost)
SELECT :po_id, p.product_id,
       (p.reorder_level * :multiplier) - COALESCE(i.quantity, 0),
       ROUND(p.unit_price * 0.70, 2)
FROM products p
LEFT JOIN inventory i ON i.product_id = p.product_id
                     AND i.warehouse_id = :warehouse_id
WHERE p.supplier_id = :supplier_id
  AND COALESCE(i.quantity, 0) < p.reorder_level
```

All statements run in **one transaction** - any failure rolls everything back.

### I4. Create shipments for fulfilled orders that have none

*INSERT ... SELECT with NOT EXISTS* - Finds fulfilled sales orders with no shipment record and inserts one 'preparing' shipment for each, with a generated tracking number.

Inputs: `carrier`

```sql
INSERT INTO shipments (so_id, carrier, tracking_number, status)
SELECT so.so_id, :carrier, 'TRK-' || CAST(so.so_id AS VARCHAR), 'preparing'
FROM sales_orders so
WHERE so.status = 'fulfilled'
  AND NOT EXISTS (
        SELECT 1 FROM shipments sh WHERE sh.so_id = so.so_id
  )
```

### I5. Initialise a warehouse's stock matrix

*INSERT ... SELECT (cross product, skip existing)* - Adds a zero-quantity inventory row for every product the chosen warehouse does not stock yet.

Inputs: `warehouse_id`

```sql
INSERT INTO inventory (product_id, warehouse_id, quantity)
SELECT p.product_id, :warehouse_id, 0
FROM products p
WHERE NOT EXISTS (
        SELECT 1 FROM inventory i
        WHERE i.product_id = p.product_id
          AND i.warehouse_id = :warehouse_id
)
```

---

## UPDATE operations

| # | Operation | Concept |
|---|---|---|
| U1 | Revise a supplier's prices by a percentage | Bulk UPDATE with arithmetic |
| U2 | Raise reorder level of fast-moving products | UPDATE ... WHERE IN (subquery with GROUP BY / HAVING) |
| U3 | Transfer stock between warehouses | Multi-statement transactional UPDATE |
| U4 | Cancel stale pending purchase orders | UPDATE with a date condition |
| U5 | Switch carrier for shipments still preparing | UPDATE with multiple WHERE conditions |

### U1. Revise a supplier's prices by a percentage

*Bulk UPDATE with arithmetic* - Raises (or lowers, if negative) the unit price of every product from one supplier.

Inputs: `supplier_id`, `percent`

```sql
UPDATE products
SET unit_price = ROUND(unit_price * (1 + :percent / 100.0), 2)
WHERE supplier_id = :supplier_id
```

### U2. Raise reorder level of fast-moving products

*UPDATE ... WHERE IN (subquery with GROUP BY / HAVING)* - Increases the reorder level of every product whose total units sold meets a threshold.

Inputs: `min_units`, `increase`

```sql
UPDATE products
SET reorder_level = reorder_level + :increase
WHERE product_id IN (
    SELECT soi.product_id
    FROM sales_order_items soi
    JOIN sales_orders so ON so.so_id = soi.so_id
    WHERE so.status <> 'cancelled'
    GROUP BY soi.product_id
    HAVING SUM(soi.quantity) >= :min_units
)
```

### U3. Transfer stock between warehouses

*Multi-statement transactional UPDATE* - Debits the source warehouse (only if enough stock) and credits the destination in a single transaction.

Inputs: `product_id`, `from_warehouse_id`, `to_warehouse_id`, `quantity`

Statement 1:
```sql
UPDATE inventory
SET quantity = quantity - :quantity
WHERE product_id = :product_id
  AND warehouse_id = :from_warehouse_id
  AND quantity >= :quantity
```

Statement 2:
```sql
UPDATE inventory
SET quantity = quantity + :quantity
WHERE product_id = :product_id
  AND warehouse_id = :to_warehouse_id
```

Statement 3:
```sql
INSERT INTO inventory (product_id, warehouse_id, quantity)
VALUES (:product_id, :to_warehouse_id, :quantity)
```

All statements run in **one transaction** - any failure rolls everything back.

### U4. Cancel stale pending purchase orders

*UPDATE with a date condition* - Marks as cancelled every purchase order that has been pending for more than N days.

Inputs: `days`

```sql
UPDATE purchase_orders
SET status = 'cancelled'
WHERE status = 'pending'
  AND order_date < :cutoff
```

### U5. Switch carrier for shipments still preparing

*UPDATE with multiple WHERE conditions* - Re-assigns every 'preparing' shipment from one carrier to another.

Inputs: `old_carrier`, `new_carrier`

```sql
UPDATE shipments
SET carrier = :new_carrier
WHERE carrier = :old_carrier
  AND status = 'preparing'
```

---

## Concepts covered

- **Joins:** INNER, LEFT, multi-table (up to 4 tables), joins against derived tables (subqueries in FROM)
- **Aggregation:** COUNT, SUM, AVG, COUNT(DISTINCT), GROUP BY, HAVING, conditional aggregation (SUM + CASE)
- **Subqueries:** scalar, IN, NOT EXISTS (correlated), derived tables, subquery inside HAVING and UPDATE
- **Set operations:** UNION ALL
- **Filtering / sorting:** WHERE, LIKE, ORDER BY, LIMIT, COALESCE / NULLIF
- **DML:** INSERT ... VALUES, INSERT ... SELECT, multi-table transactional INSERT, bulk UPDATE, UPDATE with subquery, transactional stock transfer
- **Safety:** parameterised queries (no SQL injection), transactions with rollback, CHECK / FK / UNIQUE violations reported as clear errors
