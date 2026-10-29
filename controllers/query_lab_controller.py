"""
Query Lab
=========

A catalogue of SQL operations that demonstrate the database concepts used in
this project:

    * 22 SELECT queries   (joins, aggregates, GROUP BY / HAVING, subqueries,
                           set operations, CASE, ...)
    *  5 INSERT operations (INSERT ... VALUES, multi-table transactions,
                            INSERT ... SELECT)
    *  5 UPDATE operations (bulk update, subquery update, transactional
                            stock transfer, conditional update)

Every statement is written ONCE, as a constant with named placeholders
(:name).  The same constant is both shown in the UI and executed, so the SQL a
reader sees is always exactly the SQL that runs.  Placeholders are converted to
driver parameters (%s) at run time, so user input is never concatenated into
SQL (no SQL-injection risk).  The SQL sticks to the common subset of
PostgreSQL and SQLite, because this project can run on either.
"""
import re
from datetime import datetime, timedelta
from decimal import Decimal

from db.db import get_connection
from db.seed import seed_demo_data

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
_PARAM_RE = re.compile(r"(?<!:):([a-z_][a-z0-9_]*)")


def _compile(sql, values):
    """':name' placeholders -> '%s' placeholders + ordered argument tuple."""
    names = _PARAM_RE.findall(sql)
    return _PARAM_RE.sub("%s", sql), tuple(values[n] for n in names)


def _clean(value):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime,)):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    return value


def _clean_rows(rows):
    return [{k: _clean(v) for k, v in dict(r).items()} for r in rows]


def _sql(text):
    return "\n".join(line.rstrip() for line in text.strip("\n").splitlines())


class QueryError(Exception):
    """A user-facing problem (bad input, business rule) with an HTTP status."""

    def __init__(self, message, status=400):
        super().__init__(message)
        self.message = message
        self.status = status


def _coerce(spec, raw, use_defaults=False):
    """Convert a raw request value to the type declared by a parameter spec.

    ``use_defaults`` is only True for read-only SELECT parameters.  For INSERT /
    UPDATE forms a blank required field is an error: defaults there are just
    pre-filled suggestions in the UI and must never be applied silently.
    """
    ptype = spec.get("type", "text")
    label = spec.get("label", spec["name"])
    if raw is None or str(raw).strip() == "":
        if spec.get("required", True):
            if not use_defaults or spec.get("default") is None:
                raise QueryError(f"'{label}' is required")
            raw = spec["default"]          # SELECT parameters fall back to their default
        else:
            return None                    # optional field left blank -> NULL
    try:
        if ptype in ("int", "supplier", "warehouse", "product"):
            value = int(raw)
        elif ptype == "number":
            value = float(raw)
        else:
            value = str(raw).strip()
    except (TypeError, ValueError):
        raise QueryError(f"'{label}' has an invalid value")
    if isinstance(value, (int, float)):
        if "min" in spec and value < spec["min"]:
            raise QueryError(f"'{label}' must be at least {spec['min']}")
        if "max" in spec and value > spec["max"]:
            raise QueryError(f"'{label}' must be at most {spec['max']}")
    return value


def _collect(specs, source, use_defaults=False):
    return {s["name"]: _coerce(s, source.get(s["name"]), use_defaults) for s in specs}


# ---------------------------------------------------------------------------
# 22 SELECT QUERIES
# ---------------------------------------------------------------------------
SELECT_QUERIES = [
    {
        "id": 1,
        "title": "Premium products above a price",
        "concept": "WHERE + ORDER BY + LEFT JOIN",
        "description": "Lists products priced at or above a minimum, most expensive first, with their supplier.",
        "params": [{"name": "min_price", "label": "Minimum price (₹)", "type": "number", "default": 500, "min": 0}],
        "sql": _sql("""
SELECT p.sku, p.name, p.unit_price, s.name AS supplier
FROM products p
LEFT JOIN suppliers s ON s.supplier_id = p.supplier_id
WHERE p.unit_price >= :min_price
ORDER BY p.unit_price DESC
"""),
    },
    {
        "id": 2,
        "title": "Search products by name or SKU",
        "concept": "LIKE pattern matching",
        "description": "Case-insensitive partial match on product name or SKU.",
        "params": [{"name": "term", "label": "Search text", "type": "text", "default": "steel", "like": True}],
        "sql": _sql("""
SELECT p.product_id, p.sku, p.name, p.description, p.unit_price
FROM products p
WHERE LOWER(p.name) LIKE LOWER(:term)
   OR LOWER(p.sku)  LIKE LOWER(:term)
ORDER BY p.name
"""),
    },
    {
        "id": 3,
        "title": "Inventory matrix (product x warehouse)",
        "concept": "3-table INNER JOIN",
        "description": "Every stock record joined with its product and warehouse names.",
        "params": [],
        "sql": _sql("""
SELECT w.name AS warehouse, p.sku, p.name AS product, i.quantity
FROM inventory i
JOIN products   p ON p.product_id   = i.product_id
JOIN warehouses w ON w.warehouse_id = i.warehouse_id
ORDER BY w.name, p.name
"""),
    },
    {
        "id": 4,
        "title": "Low-stock report",
        "concept": "LEFT JOIN + GROUP BY + HAVING",
        "description": "Products whose total stock across all warehouses is at or below the reorder level.",
        "params": [],
        "sql": _sql("""
SELECT p.sku, p.name, p.reorder_level,
       COALESCE(SUM(i.quantity), 0) AS total_stock
FROM products p
LEFT JOIN inventory i ON i.product_id = p.product_id
GROUP BY p.product_id, p.sku, p.name, p.reorder_level
HAVING COALESCE(SUM(i.quantity), 0) <= p.reorder_level
ORDER BY total_stock
"""),
    },
    {
        "id": 5,
        "title": "Warehouse capacity utilisation",
        "concept": "Aggregate + computed percentage",
        "description": "Units stored vs. capacity for each warehouse, as a percentage.",
        "params": [],
        "sql": _sql("""
SELECT w.name AS warehouse, w.capacity,
       COALESCE(SUM(i.quantity), 0) AS units_stored,
       ROUND(100.0 * COALESCE(SUM(i.quantity), 0) / NULLIF(w.capacity, 0), 2) AS utilisation_pct
FROM warehouses w
LEFT JOIN inventory i ON i.warehouse_id = w.warehouse_id
GROUP BY w.warehouse_id, w.name, w.capacity
ORDER BY utilisation_pct DESC
"""),
    },
    {
        "id": 6,
        "title": "Products supplied by each supplier",
        "concept": "LEFT JOIN + COUNT + AVG",
        "description": "Number of products and average price per supplier (suppliers with no products show 0).",
        "params": [],
        "sql": _sql("""
SELECT s.name AS supplier,
       COUNT(p.product_id) AS products_supplied,
       COALESCE(ROUND(AVG(p.unit_price), 2), 0) AS avg_price
FROM suppliers s
LEFT JOIN products p ON p.supplier_id = s.supplier_id
GROUP BY s.supplier_id, s.name
ORDER BY products_supplied DESC, s.name
"""),
    },
    {
        "id": 7,
        "title": "Stock value per warehouse",
        "concept": "SUM over an expression (qty x price)",
        "description": "Total rupee value of the stock held in every warehouse.",
        "params": [],
        "sql": _sql("""
SELECT w.name AS warehouse,
       COUNT(DISTINCT i.product_id)               AS distinct_products,
       COALESCE(SUM(i.quantity), 0)               AS units,
       COALESCE(SUM(i.quantity * p.unit_price), 0) AS stock_value
FROM warehouses w
LEFT JOIN inventory i ON i.warehouse_id = w.warehouse_id
LEFT JOIN products  p ON p.product_id   = i.product_id
GROUP BY w.warehouse_id, w.name
ORDER BY stock_value DESC
"""),
    },
    {
        "id": 8,
        "title": "Products that have never been sold",
        "concept": "NOT EXISTS (correlated subquery)",
        "description": "Catalogue items that do not appear on any sales order line.",
        "params": [],
        "sql": _sql("""
SELECT p.sku, p.name, p.unit_price
FROM products p
WHERE NOT EXISTS (
    SELECT 1
    FROM sales_order_items soi
    WHERE soi.product_id = p.product_id
)
ORDER BY p.name
"""),
    },
    {
        "id": 9,
        "title": "Top 5 best-selling products",
        "concept": "JOIN + GROUP BY + ORDER BY + LIMIT",
        "description": "Units sold and revenue per product, ignoring cancelled orders.",
        "params": [],
        "sql": _sql("""
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
"""),
    },
    {
        "id": 10,
        "title": "Revenue by customer",
        "concept": "GROUP BY + COUNT DISTINCT + SUM",
        "description": "Number of orders and total spend per customer (cancelled orders excluded).",
        "params": [],
        "sql": _sql("""
SELECT so.customer_name,
       COUNT(DISTINCT so.so_id)             AS orders,
       SUM(soi.quantity * soi.unit_price)   AS total_spent
FROM sales_orders so
JOIN sales_order_items soi ON soi.so_id = so.so_id
WHERE so.status <> 'cancelled'
GROUP BY so.customer_name
ORDER BY total_spent DESC
"""),
    },
    {
        "id": 11,
        "title": "Pending purchase orders with totals",
        "concept": "Multi-table JOIN + SUM",
        "description": "Open purchase orders with supplier, destination warehouse and total cost.",
        "params": [],
        "sql": _sql("""
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
"""),
    },
    {
        "id": 12,
        "title": "Sales orders above the average order value",
        "concept": "HAVING with a derived-table subquery",
        "description": "Orders whose total is greater than the average order total.",
        "params": [],
        "sql": _sql("""
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
"""),
    },
    {
        "id": 13,
        "title": "Products priced above the catalogue average",
        "concept": "Scalar subquery",
        "description": "Items that cost more than the average unit price of all products.",
        "params": [],
        "sql": _sql("""
SELECT sku, name, unit_price
FROM products
WHERE unit_price > (SELECT AVG(unit_price) FROM products)
ORDER BY unit_price DESC
"""),
    },
    {
        "id": 14,
        "title": "Products stocked in more than one warehouse",
        "concept": "HAVING COUNT(DISTINCT ...)",
        "description": "Products that have stock in at least two different warehouses.",
        "params": [],
        "sql": _sql("""
SELECT p.sku, p.name,
       COUNT(DISTINCT i.warehouse_id) AS warehouses_stocking,
       SUM(i.quantity)                AS total_units
FROM products p
JOIN inventory i ON i.product_id = p.product_id
WHERE i.quantity > 0
GROUP BY p.product_id, p.sku, p.name
HAVING COUNT(DISTINCT i.warehouse_id) > 1
ORDER BY total_units DESC
"""),
    },
    {
        "id": 15,
        "title": "Shipments currently in transit",
        "concept": "4-table JOIN with filter",
        "description": "Shipped-but-not-delivered parcels with customer, origin warehouse and carrier.",
        "params": [],
        "sql": _sql("""
SELECT sh.shipment_id, so.so_id, so.customer_name,
       w.name AS dispatched_from, sh.carrier, sh.tracking_number, sh.shipped_date
FROM shipments sh
JOIN sales_orders so ON so.so_id        = sh.so_id
JOIN warehouses   w  ON w.warehouse_id  = so.warehouse_id
WHERE sh.status = 'shipped'
ORDER BY sh.shipped_date
"""),
    },
    {
        "id": 16,
        "title": "Carrier performance summary",
        "concept": "Conditional aggregation (SUM + CASE)",
        "description": "How many shipments each carrier has delivered, in transit and still preparing.",
        "params": [],
        "sql": _sql("""
SELECT COALESCE(carrier, 'Unassigned') AS carrier,
       COUNT(*)                                          AS total_shipments,
       SUM(CASE WHEN status = 'delivered' THEN 1 ELSE 0 END) AS delivered,
       SUM(CASE WHEN status = 'shipped'   THEN 1 ELSE 0 END) AS in_transit,
       SUM(CASE WHEN status = 'preparing' THEN 1 ELSE 0 END) AS preparing
FROM shipments
GROUP BY COALESCE(carrier, 'Unassigned')
ORDER BY total_shipments DESC
"""),
    },
    {
        "id": 17,
        "title": "Monthly sales revenue",
        "concept": "GROUP BY on a derived expression (SUBSTR)",
        "description": "Orders and revenue grouped by year-month of the order date.",
        "params": [],
        "sql": _sql("""
SELECT SUBSTR(CAST(so.order_date AS VARCHAR), 1, 7) AS sale_month,
       COUNT(DISTINCT so.so_id)                     AS orders,
       SUM(soi.quantity * soi.unit_price)           AS revenue
FROM sales_orders so
JOIN sales_order_items soi ON soi.so_id = so.so_id
WHERE so.status <> 'cancelled'
GROUP BY sale_month
ORDER BY sale_month
"""),
    },
    {
        "id": 18,
        "title": "Gross margin per product",
        "concept": "Two derived tables joined together",
        "description": "Average purchase cost vs. average selling price for products that were both bought and sold.",
        "params": [],
        "sql": _sql("""
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
"""),
    },
    {
        "id": 19,
        "title": "Can pending sales orders be fulfilled?",
        "concept": "LEFT JOIN + CASE + string concatenation",
        "description": "Compares each pending order line with stock in that order's warehouse.",
        "params": [],
        "sql": _sql("""
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
"""),
    },
    {
        "id": 20,
        "title": "Suppliers ranked by purchase spend",
        "concept": "Aggregate over 3 joined tables",
        "description": "Total units and money spent with each supplier on received purchase orders.",
        "params": [],
        "sql": _sql("""
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
"""),
    },
    {
        "id": 21,
        "title": "Recent order activity feed",
        "concept": "UNION ALL",
        "description": "The 10 most recent purchase and sales orders combined into a single timeline.",
        "params": [],
        "sql": _sql("""
SELECT 'Purchase Order' AS event_type, po_id AS ref_id, status, order_date AS event_date
FROM purchase_orders
UNION ALL
SELECT 'Sales Order', so_id, status, order_date
FROM sales_orders
ORDER BY event_date DESC
LIMIT 10
"""),
    },
    {
        "id": 22,
        "title": "Orders that contain a given product",
        "concept": "IN (subquery) with a parameter",
        "description": "Which customers ordered a particular SKU, and in which orders.",
        "params": [{"name": "sku", "label": "Product SKU", "type": "text", "default": "SKU-1001"}],
        "sql": _sql("""
SELECT so.so_id, so.customer_name, so.status, so.order_date
FROM sales_orders so
WHERE so.so_id IN (
    SELECT soi.so_id
    FROM sales_order_items soi
    JOIN products p ON p.product_id = soi.product_id
    WHERE p.sku = :sku
)
ORDER BY so.order_date DESC
"""),
    },
]

_SELECT_BY_ID = {q["id"]: q for q in SELECT_QUERIES}


def run_select(query_id, args):
    spec = _SELECT_BY_ID.get(query_id)
    if spec is None:
        return {"error": "Unknown query"}, 404
    conn = None
    try:
        values = _collect(spec["params"], args, use_defaults=True)
        for p in spec["params"]:          # LIKE parameters get wildcards added
            if p.get("like"):
                values[p["name"]] = f"%{values[p['name']]}%"
        sql, params = _compile(spec["sql"], values)
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(sql, params)
        rows = _clean_rows(cur.fetchall())
        cur.close()
        columns = list(rows[0].keys()) if rows else []
        return {"id": query_id, "title": spec["title"], "row_count": len(rows),
                "columns": columns, "rows": rows}, 200
    except QueryError as e:
        return {"error": e.message}, e.status
    except Exception as e:
        print(e)
        return {"error": "Query failed to execute"}, 500
    finally:
        if conn is not None:
            conn.close()


# ---------------------------------------------------------------------------
# INSERT / UPDATE statements (each written once)
# ---------------------------------------------------------------------------
I1_SUPPLIER = _sql("""
INSERT INTO suppliers (name, contact_email, contact_phone, address)
VALUES (:name, :contact_email, :contact_phone, :address)
RETURNING *
""")

I2_PRODUCT = _sql("""
INSERT INTO products (sku, name, description, unit_price, reorder_level, supplier_id)
VALUES (:sku, :name, :description, :unit_price, :reorder_level, :supplier_id)
RETURNING *
""")
I2_STOCK = _sql("""
INSERT INTO inventory (product_id, warehouse_id, quantity)
VALUES (:product_id, :warehouse_id, :opening_stock)
""")

I3_PO = _sql("""
INSERT INTO purchase_orders (supplier_id, warehouse_id, status)
VALUES (:supplier_id, :warehouse_id, 'pending')
RETURNING po_id
""")
I3_ITEMS = _sql("""
INSERT INTO purchase_order_items (po_id, product_id, quantity, unit_cost)
SELECT :po_id, p.product_id,
       (p.reorder_level * :multiplier) - COALESCE(i.quantity, 0),
       ROUND(p.unit_price * 0.70, 2)
FROM products p
LEFT JOIN inventory i ON i.product_id = p.product_id
                     AND i.warehouse_id = :warehouse_id
WHERE p.supplier_id = :supplier_id
  AND COALESCE(i.quantity, 0) < p.reorder_level
""")

I4_SHIPMENTS = _sql("""
INSERT INTO shipments (so_id, carrier, tracking_number, status)
SELECT so.so_id, :carrier, 'TRK-' || CAST(so.so_id AS VARCHAR), 'preparing'
FROM sales_orders so
WHERE so.status = 'fulfilled'
  AND NOT EXISTS (
        SELECT 1 FROM shipments sh WHERE sh.so_id = so.so_id
  )
""")

I5_INVENTORY = _sql("""
INSERT INTO inventory (product_id, warehouse_id, quantity)
SELECT p.product_id, :warehouse_id, 0
FROM products p
WHERE NOT EXISTS (
        SELECT 1 FROM inventory i
        WHERE i.product_id = p.product_id
          AND i.warehouse_id = :warehouse_id
)
""")

U1_PRICES = _sql("""
UPDATE products
SET unit_price = ROUND(unit_price * (1 + :percent / 100.0), 2)
WHERE supplier_id = :supplier_id
""")

U2_REORDER = _sql("""
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
""")

U3_DEBIT = _sql("""
UPDATE inventory
SET quantity = quantity - :quantity
WHERE product_id = :product_id
  AND warehouse_id = :from_warehouse_id
  AND quantity >= :quantity
""")
U3_CREDIT = _sql("""
UPDATE inventory
SET quantity = quantity + :quantity
WHERE product_id = :product_id
  AND warehouse_id = :to_warehouse_id
""")
U3_CREDIT_NEW = _sql("""
INSERT INTO inventory (product_id, warehouse_id, quantity)
VALUES (:product_id, :to_warehouse_id, :quantity)
""")

U4_CANCEL = _sql("""
UPDATE purchase_orders
SET status = 'cancelled'
WHERE status = 'pending'
  AND order_date < :cutoff
""")

U5_CARRIER = _sql("""
UPDATE shipments
SET carrier = :new_carrier
WHERE carrier = :old_carrier
  AND status = 'preparing'
""")

DML_CATALOG = [
    {
        "id": "I1", "kind": "INSERT", "title": "Register a new supplier",
        "concept": "INSERT ... VALUES (single row, RETURNING)",
        "description": "Adds one supplier row and returns the stored record.",
        "sql": [I1_SUPPLIER],
        "fields": [
            {"name": "name", "label": "Supplier name", "type": "text", "default": "Prime Fasteners Pvt Ltd"},
            {"name": "contact_email", "label": "Contact email", "type": "text", "default": "sales@primefasteners.in", "required": False},
            {"name": "contact_phone", "label": "Contact phone", "type": "text", "default": "9811122334", "required": False},
            {"name": "address", "label": "Address", "type": "text", "default": "Coimbatore, TN", "required": False},
        ],
    },
    {
        "id": "I2", "kind": "INSERT", "title": "Onboard a product with opening stock",
        "concept": "Two INSERTs in one transaction",
        "description": "Creates a product and its first inventory record atomically - if either insert fails, both are rolled back.",
        "sql": [I2_PRODUCT, I2_STOCK],
        "fields": [
            {"name": "sku", "label": "SKU", "type": "text", "default": "SKU-3001"},
            {"name": "name", "label": "Product name", "type": "text", "default": "Angle Grinder 4in"},
            {"name": "description", "label": "Description", "type": "text", "default": "850W, 12000 RPM", "required": False},
            {"name": "unit_price", "label": "Unit price (₹)", "type": "number", "default": 2150, "min": 0},
            {"name": "reorder_level", "label": "Reorder level", "type": "int", "default": 6, "min": 0},
            {"name": "supplier_id", "label": "Supplier", "type": "supplier"},
            {"name": "warehouse_id", "label": "Warehouse", "type": "warehouse"},
            {"name": "opening_stock", "label": "Opening stock", "type": "int", "default": 25, "min": 0},
        ],
    },
    {
        "id": "I3", "kind": "INSERT", "title": "Draft a restock purchase order",
        "concept": "INSERT ... SELECT (bulk insert from a query)",
        "description": "Creates a pending purchase order and fills its lines automatically from every product of that supplier that is below its reorder level in the chosen warehouse.",
        "sql": [I3_PO, I3_ITEMS],
        "fields": [
            {"name": "supplier_id", "label": "Supplier", "type": "supplier"},
            {"name": "warehouse_id", "label": "Warehouse", "type": "warehouse"},
            {"name": "multiplier", "label": "Restock up to N x reorder level", "type": "int", "default": 2, "min": 1, "max": 10},
        ],
    },
    {
        "id": "I4", "kind": "INSERT", "title": "Create shipments for fulfilled orders that have none",
        "concept": "INSERT ... SELECT with NOT EXISTS",
        "description": "Finds fulfilled sales orders with no shipment record and inserts one 'preparing' shipment for each, with a generated tracking number.",
        "sql": [I4_SHIPMENTS],
        "fields": [
            {"name": "carrier", "label": "Carrier", "type": "text", "default": "BlueDart"},
        ],
    },
    {
        "id": "I5", "kind": "INSERT", "title": "Initialise a warehouse's stock matrix",
        "concept": "INSERT ... SELECT (cross product, skip existing)",
        "description": "Adds a zero-quantity inventory row for every product the chosen warehouse does not stock yet.",
        "sql": [I5_INVENTORY],
        "fields": [
            {"name": "warehouse_id", "label": "Warehouse", "type": "warehouse"},
        ],
    },
    {
        "id": "U1", "kind": "UPDATE", "title": "Revise a supplier's prices by a percentage",
        "concept": "Bulk UPDATE with arithmetic",
        "description": "Raises (or lowers, if negative) the unit price of every product from one supplier.",
        "sql": [U1_PRICES],
        "fields": [
            {"name": "supplier_id", "label": "Supplier", "type": "supplier"},
            {"name": "percent", "label": "Change (%)", "type": "number", "default": 5, "min": -90, "max": 100},
        ],
    },
    {
        "id": "U2", "kind": "UPDATE", "title": "Raise reorder level of fast-moving products",
        "concept": "UPDATE ... WHERE IN (subquery with GROUP BY / HAVING)",
        "description": "Increases the reorder level of every product whose total units sold meets a threshold.",
        "sql": [U2_REORDER],
        "fields": [
            {"name": "min_units", "label": "Units sold at least", "type": "int", "default": 50, "min": 1},
            {"name": "increase", "label": "Increase reorder level by", "type": "int", "default": 5, "min": 1, "max": 1000},
        ],
    },
    {
        "id": "U3", "kind": "UPDATE", "title": "Transfer stock between warehouses",
        "concept": "Multi-statement transactional UPDATE",
        "description": "Debits the source warehouse (only if enough stock) and credits the destination in a single transaction.",
        "sql": [U3_DEBIT, U3_CREDIT, U3_CREDIT_NEW],
        "fields": [
            {"name": "product_id", "label": "Product", "type": "product"},
            {"name": "from_warehouse_id", "label": "From warehouse", "type": "warehouse"},
            {"name": "to_warehouse_id", "label": "To warehouse", "type": "warehouse"},
            {"name": "quantity", "label": "Quantity", "type": "int", "default": 5, "min": 1},
        ],
    },
    {
        "id": "U4", "kind": "UPDATE", "title": "Cancel stale pending purchase orders",
        "concept": "UPDATE with a date condition",
        "description": "Marks as cancelled every purchase order that has been pending for more than N days.",
        "sql": [U4_CANCEL],
        "fields": [
            {"name": "days", "label": "Pending for more than (days)", "type": "int", "default": 30, "min": 1, "max": 3650},
        ],
    },
    {
        "id": "U5", "kind": "UPDATE", "title": "Switch carrier for shipments still preparing",
        "concept": "UPDATE with multiple WHERE conditions",
        "description": "Re-assigns every 'preparing' shipment from one carrier to another.",
        "sql": [U5_CARRIER],
        "fields": [
            {"name": "old_carrier", "label": "Current carrier", "type": "text", "default": "BlueDart"},
            {"name": "new_carrier", "label": "New carrier", "type": "text", "default": "Delhivery"},
        ],
    },
]
_DML_BY_ID = {d["id"]: d for d in DML_CATALOG}


class _Tx:
    """Runs statements on one cursor and records what was executed."""

    def __init__(self, cur):
        self.cur = cur
        self.log = []

    def run(self, sql, values):
        q, params = _compile(sql, values)
        self.cur.execute(q, params)
        affected = self.cur.rowcount
        self.log.append({"sql": sql, "params": {n: values[n] for n in _PARAM_RE.findall(sql)},
                         "rows_affected": affected if affected is not None and affected >= 0 else 0})
        return affected

    def mark_single_row(self):
        """INSERT ... RETURNING reports rowcount lazily on some drivers; it is always 1 here."""
        self.log[-1]["rows_affected"] = 1

    def fetch(self, sql, values=None):
        q, params = _compile(sql, values or {})
        self.cur.execute(q, params)
        return _clean_rows(self.cur.fetchall())


# -- INSERTS -----------------------------------------------------------------
def _i1(tx, v):
    tx.run(I1_SUPPLIER, v)
    row = tx.cur.fetchone()
    tx.mark_single_row()
    return "Supplier registered.", _clean_rows([row]) if row else []


def _i2(tx, v):
    tx.run(I2_PRODUCT, v)
    product = tx.cur.fetchone()
    tx.mark_single_row()
    v = dict(v, product_id=product["product_id"])
    tx.run(I2_STOCK, v)
    rows = tx.fetch(
        "SELECT p.sku, p.name, p.unit_price, w.name AS warehouse, i.quantity "
        "FROM products p JOIN inventory i ON i.product_id = p.product_id "
        "JOIN warehouses w ON w.warehouse_id = i.warehouse_id "
        "WHERE p.product_id = :product_id", v)
    return "Product created with opening stock.", rows


def _i3(tx, v):
    tx.run(I3_PO, v)
    po_id = tx.cur.fetchone()["po_id"]
    tx.mark_single_row()
    v = dict(v, po_id=po_id)
    inserted = tx.run(I3_ITEMS, v)
    if not inserted:
        raise QueryError("Nothing to restock: no product from this supplier is below its "
                         "reorder level in that warehouse.", 422)
    rows = tx.fetch(
        "SELECT poi.po_id, p.sku, p.name, poi.quantity, poi.unit_cost "
        "FROM purchase_order_items poi JOIN products p ON p.product_id = poi.product_id "
        "WHERE poi.po_id = :po_id ORDER BY p.sku", v)
    return f"Purchase order #{po_id} drafted with {inserted} line(s).", rows


def _i4(tx, v):
    inserted = tx.run(I4_SHIPMENTS, v)
    if not inserted:
        raise QueryError("Every fulfilled order already has a shipment - nothing to insert.", 422)
    rows = tx.fetch(
        "SELECT shipment_id, so_id, carrier, tracking_number, status FROM shipments "
        "WHERE carrier = :carrier AND status = 'preparing' ORDER BY shipment_id DESC", v)
    return f"{inserted} shipment(s) created.", rows[:inserted]


def _i5(tx, v):
    inserted = tx.run(I5_INVENTORY, v)
    if not inserted:
        raise QueryError("This warehouse already has a stock row for every product.", 422)
    rows = tx.fetch(
        "SELECT w.name AS warehouse, p.sku, p.name AS product, i.quantity "
        "FROM inventory i JOIN products p ON p.product_id = i.product_id "
        "JOIN warehouses w ON w.warehouse_id = i.warehouse_id "
        "WHERE i.warehouse_id = :warehouse_id ORDER BY p.sku", v)
    return f"{inserted} inventory row(s) added.", rows


# -- UPDATES -----------------------------------------------------------------
def _u1(tx, v):
    updated = tx.run(U1_PRICES, v)
    if not updated:
        raise QueryError("That supplier has no products to update.", 422)
    rows = tx.fetch("SELECT sku, name, unit_price FROM products WHERE supplier_id = :supplier_id "
                    "ORDER BY sku", v)
    return f"{updated} product price(s) updated.", rows


def _u2(tx, v):
    updated = tx.run(U2_REORDER, v)
    rows = tx.fetch("SELECT sku, name, reorder_level FROM products ORDER BY sku")
    if not updated:
        return "No product has sold that many units yet - nothing updated.", rows
    return f"{updated} product(s) now have a higher reorder level.", rows


def _u3(tx, v):
    if v["from_warehouse_id"] == v["to_warehouse_id"]:
        raise QueryError("Source and destination warehouses must be different.")
    debited = tx.run(U3_DEBIT, v)
    if debited != 1:
        raise QueryError("Insufficient stock in the source warehouse (or no stock record).", 409)
    credited = tx.run(U3_CREDIT, v)
    if credited == 0:                      # destination had no row yet
        tx.run(U3_CREDIT_NEW, v)
    rows = tx.fetch(
        "SELECT w.name AS warehouse, p.sku, p.name AS product, i.quantity "
        "FROM inventory i JOIN products p ON p.product_id = i.product_id "
        "JOIN warehouses w ON w.warehouse_id = i.warehouse_id "
        "WHERE i.product_id = :product_id AND i.warehouse_id IN (:from_warehouse_id, :to_warehouse_id)", v)
    return f"Moved {v['quantity']} unit(s) between warehouses.", rows


def _u4(tx, v):
    v = dict(v, cutoff=(datetime.now() - timedelta(days=v["days"])).strftime("%Y-%m-%d %H:%M:%S"))
    before = tx.fetch("SELECT po_id, status, order_date FROM purchase_orders "
                      "WHERE status = 'pending' AND order_date < :cutoff ORDER BY po_id", v)
    updated = tx.run(U4_CANCEL, v)
    if not updated:
        raise QueryError("No pending purchase order is older than that.", 422)
    rows = [dict(r, status="cancelled") for r in before]
    return f"{updated} purchase order(s) cancelled.", rows


def _u5(tx, v):
    if v["old_carrier"].lower() == v["new_carrier"].lower():
        raise QueryError("The new carrier must differ from the current one.")
    updated = tx.run(U5_CARRIER, v)
    if not updated:
        raise QueryError("No 'preparing' shipment uses that carrier.", 422)
    rows = tx.fetch("SELECT shipment_id, so_id, carrier, tracking_number, status FROM shipments "
                    "WHERE carrier = :new_carrier AND status = 'preparing' ORDER BY shipment_id", v)
    return f"{updated} shipment(s) re-assigned.", rows


_DML_HANDLERS = {"I1": _i1, "I2": _i2, "I3": _i3, "I4": _i4, "I5": _i5,
                 "U1": _u1, "U2": _u2, "U3": _u3, "U4": _u4, "U5": _u5}


def run_dml(dml_id, data):
    spec = _DML_BY_ID.get(dml_id.upper())
    if spec is None:
        return {"error": "Unknown operation"}, 404
    conn = None
    try:
        values = _collect(spec["fields"], data or {})
        conn = get_connection()
        cur = conn.cursor()
        tx = _Tx(cur)
        message, rows = _DML_HANDLERS[spec["id"]](tx, values)
        conn.commit()
        cur.close()
        return {"id": spec["id"], "kind": spec["kind"], "title": spec["title"], "message": message,
                "statements": tx.log, "columns": list(rows[0].keys()) if rows else [],
                "rows": rows}, 200
    except QueryError as e:
        if conn is not None:
            conn.rollback()
        return {"error": e.message}, e.status
    except Exception as e:
        if conn is not None:
            conn.rollback()
        text = str(e).lower()
        print(e)
        if "unique" in text or "duplicate" in text:
            return {"error": "A record with the same unique value (e.g. SKU) already exists."}, 409
        if "foreign key" in text or "violates foreign" in text:
            return {"error": "A referenced supplier / warehouse / product does not exist."}, 400
        if "check constraint" in text or "violates check" in text:
            return {"error": "A value violates a database CHECK constraint (e.g. negative quantity)."}, 400
        return {"error": "Operation failed"}, 500
    finally:
        if conn is not None:
            conn.close()


# ---------------------------------------------------------------------------
# catalogue + demo data
# ---------------------------------------------------------------------------
def get_catalog():
    def meta(item):
        return {k: v for k, v in item.items()}
    return {
        "select": [meta(q) for q in SELECT_QUERIES],
        "insert": [meta(d) for d in DML_CATALOG if d["kind"] == "INSERT"],
        "update": [meta(d) for d in DML_CATALOG if d["kind"] == "UPDATE"],
        "counts": {"select": len(SELECT_QUERIES),
                   "insert": sum(1 for d in DML_CATALOG if d["kind"] == "INSERT"),
                   "update": sum(1 for d in DML_CATALOG if d["kind"] == "UPDATE")},
    }, 200


def load_demo_data():
    conn = get_connection()
    try:
        return seed_demo_data(conn), 200
    except Exception as e:
        conn.rollback()
        print(e)
        return {"error": "Failed to load demo data"}, 500
    finally:
        conn.close()
