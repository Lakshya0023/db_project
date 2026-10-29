"""
Demo data seeder.

Adds a realistic data set (suppliers, warehouses, products, stock, purchase
orders, sales orders, shipments) so every report in the Query Lab has
something interesting to show.

* Idempotent  - running it twice does nothing the second time.
* Non-destructive - it only ever INSERTs; your existing rows are untouched.
* Portable - written with plain SQL that works on PostgreSQL and SQLite.
"""
from datetime import datetime, timedelta

SEED_MARKER_SKU = "SKU-2001"

SUPPLIERS = [
    ("Acme Traders", "contact@acme.com", "9876543210", "Mumbai, MH"),
    ("Global Parts Co.", "sales@globalparts.com", "9123456780", "Bangalore, KA"),
    ("Precision Tools Ltd", "orders@precisiontools.in", "9988776655", "Pune, MH"),
    ("SteelCraft Industries", "hello@steelcraft.in", "9877001122", "Jamshedpur, JH"),
    ("Apex Electricals", "sales@apexelectricals.in", "9345612780", "Hyderabad, TS"),
]

WAREHOUSES = [
    ("Central Warehouse", "Chennai, TN", 10000),
    ("North Depot", "Delhi, DL", 5000),
    ("West Hub", "Mumbai, MH", 8000),
    ("South Annex", "Bengaluru, KA", 6000),
]

# sku, name, description, unit_price, reorder_level, supplier name
PRODUCTS = [
    ("SKU-1001", "Steel Bolt 10mm", "Pack of 100", 250.00, 20, "Acme Traders"),
    ("SKU-1002", "Ball Bearing 6mm", "Pack of 50", 480.00, 15, "Global Parts Co."),
    ("SKU-1003", "Hydraulic Hose 2m", "Reinforced rubber hose", 950.00, 10, "Acme Traders"),
    ("SKU-2001", "Copper Wire Roll", "50m roll, 2mm gauge", 620.00, 12, "Apex Electricals"),
    ("SKU-2002", "Industrial Drill Bit Set", "HSS, 25 piece set", 1450.00, 8, "Precision Tools Ltd"),
    ("SKU-2003", "Safety Helmet", "ISI marked, adjustable", 390.00, 25, "SteelCraft Industries"),
    ("SKU-2004", "Hex Nut M8", "Pack of 200", 180.00, 40, "Acme Traders"),
    ("SKU-2005", "Welding Rod 3.15mm", "Box of 5 kg", 720.00, 15, "SteelCraft Industries"),
    ("SKU-2006", "LED Panel Light 18W", "Cool white, square", 540.00, 20, "Apex Electricals"),
    ("SKU-2007", "Torque Wrench", "40-200 Nm", 2650.00, 5, "Precision Tools Ltd"),
    ("SKU-2008", "Pneumatic Valve 1/2in", "5/2 way solenoid", 1180.00, 10, "Global Parts Co."),
    ("SKU-2009", "Conveyor Belt 5m", "Rubber, 500mm wide", 5200.00, 3, "Global Parts Co."),
    ("SKU-2010", "Safety Gloves (Pair)", "Cut resistant", 95.00, 50, "SteelCraft Industries"),
]

# sku, warehouse name, quantity  (a few are deliberately below reorder level)
INVENTORY = [
    ("SKU-1001", "Central Warehouse", 100),
    ("SKU-1001", "North Depot", 55),
    ("SKU-1002", "Central Warehouse", 40),
    ("SKU-1002", "West Hub", 22),
    ("SKU-1003", "North Depot", 8),
    ("SKU-2001", "Central Warehouse", 6),
    ("SKU-2001", "South Annex", 35),
    ("SKU-2002", "Central Warehouse", 30),
    ("SKU-2002", "North Depot", 12),
    ("SKU-2003", "West Hub", 12),
    ("SKU-2003", "Central Warehouse", 90),
    ("SKU-2004", "Central Warehouse", 150),
    ("SKU-2005", "North Depot", 9),
    ("SKU-2005", "West Hub", 45),
    ("SKU-2006", "Central Warehouse", 70),
    ("SKU-2006", "South Annex", 28),
    ("SKU-2007", "North Depot", 6),
    ("SKU-2008", "South Annex", 4),
    ("SKU-2009", "West Hub", 3),
    ("SKU-2010", "Central Warehouse", 220),
    ("SKU-2010", "West Hub", 130),
]

# supplier, warehouse, status, days_ago, [(sku, qty, unit_cost)]
PURCHASE_ORDERS = [
    ("Apex Electricals", "Central Warehouse", "received", 75,
     [("SKU-2001", 60, 430.00), ("SKU-2006", 80, 380.00)]),
    ("Precision Tools Ltd", "North Depot", "received", 50,
     [("SKU-2002", 25, 1000.00), ("SKU-2007", 10, 1850.00)]),
    ("SteelCraft Industries", "West Hub", "received", 35,
     [("SKU-2003", 100, 260.00), ("SKU-2005", 60, 500.00), ("SKU-2010", 200, 60.00)]),
    ("Acme Traders", "Central Warehouse", "received", 20,
     [("SKU-1001", 200, 170.00), ("SKU-2004", 150, 120.00)]),
    ("Global Parts Co.", "South Annex", "pending", 5,
     [("SKU-2008", 20, 800.00), ("SKU-1002", 30, 330.00)]),
    ("Apex Electricals", "Central Warehouse", "pending", 3,
     [("SKU-2001", 40, 440.00)]),
    ("Acme Traders", "North Depot", "pending", 45,          # stale -> used by the "cancel stale POs" update
     [("SKU-1003", 30, 650.00)]),
    ("Global Parts Co.", "Central Warehouse", "cancelled", 60,
     [("SKU-2008", 10, 820.00)]),
]

# customer, warehouse, status, days_ago, [(sku, qty)], shipment or None
# shipment = (carrier, tracking, status, shipped_days_ago, delivered_days_ago)
SALES_ORDERS = [
    ("Metro Infra Pvt Ltd", "Central Warehouse", "fulfilled", 105, [("SKU-2005", 12)],
     ("BlueDart", "BD1000101", "delivered", 103, 100)),
    ("Rajesh Constructions", "Central Warehouse", "fulfilled", 85, [("SKU-1001", 40), ("SKU-2003", 30)],
     ("BlueDart", "BD1000234", "delivered", 83, 80)),
    ("Metro Infra Pvt Ltd", "North Depot", "fulfilled", 70, [("SKU-2002", 5), ("SKU-2007", 2)],
     ("DTDC", "DT5520011", "delivered", 68, 64)),
    ("Sunrise Hardware", "Central Warehouse", "fulfilled", 62,
     [("SKU-1001", 25), ("SKU-2004", 60), ("SKU-2010", 80)],
     ("Delhivery", "DL7781200", "delivered", 60, 57)),
    ("Kaveri Engineering", "West Hub", "fulfilled", 48, [("SKU-2005", 20), ("SKU-2003", 15)],
     ("BlueDart", "BD1000877", "delivered", 46, 43)),
    ("Orion Electricals", "North Depot", "cancelled", 40, [("SKU-2007", 1)], None),
    ("Deccan Builders", "Central Warehouse", "fulfilled", 33, [("SKU-2001", 15), ("SKU-2006", 25)],
     ("DTDC", "DT5520987", "shipped", 31, None)),
    ("Orion Electricals", "Central Warehouse", "fulfilled", 21, [("SKU-2006", 30), ("SKU-2001", 10)],
     ("Delhivery", "DL7781999", "shipped", 19, None)),
    ("Rajesh Constructions", "North Depot", "fulfilled", 14, [("SKU-2002", 3), ("SKU-1002", 10)],
     ("BlueDart", "BD1001500", "preparing", None, None)),
    ("Metro Infra Pvt Ltd", "Central Warehouse", "fulfilled", 9, [("SKU-1001", 30)], None),
    ("Sunrise Hardware", "West Hub", "fulfilled", 6, [("SKU-2010", 50), ("SKU-2003", 10)], None),
    ("Kaveri Engineering", "Central Warehouse", "pending", 4, [("SKU-2001", 20), ("SKU-2004", 10)], None),
    ("Deccan Builders", "South Annex", "pending", 2, [("SKU-2008", 8)], None),
    ("Rajesh Constructions", "Central Warehouse", "pending", 1, [("SKU-1001", 15)], None),
]


def _ts(days_ago):
    """Timestamp string (portable across PostgreSQL / SQLite)."""
    if days_ago is None:
        return None
    return (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d %H:%M:%S")


def _first(cur, sql, params):
    cur.execute(sql, params)
    row = cur.fetchone()
    return row


def _get_or_create(cur, select_sql, select_params, insert_sql, insert_params, id_col):
    row = _first(cur, select_sql, select_params)
    if row:
        return row[id_col], False
    cur.execute(insert_sql + " RETURNING " + id_col, insert_params)
    return cur.fetchone()[id_col], True


def seed_demo_data(conn):
    """Insert the demo data set. Returns a summary dict."""
    cur = conn.cursor()

    if _first(cur, "SELECT product_id FROM products WHERE sku = %s", (SEED_MARKER_SKU,)):
        cur.close()
        return {"seeded": False, "message": "Demo data is already loaded.", "added": {}}

    added = {"suppliers": 0, "warehouses": 0, "products": 0, "inventory": 0,
             "purchase_orders": 0, "sales_orders": 0, "shipments": 0}

    supplier_ids, warehouse_ids, product_ids, product_prices = {}, {}, {}, {}

    for name, email, phone, address in SUPPLIERS:
        sid, created = _get_or_create(
            cur,
            "SELECT supplier_id FROM suppliers WHERE name = %s", (name,),
            "INSERT INTO suppliers (name, contact_email, contact_phone, address) VALUES (%s, %s, %s, %s)",
            (name, email, phone, address), "supplier_id")
        supplier_ids[name] = sid
        added["suppliers"] += int(created)

    for name, location, capacity in WAREHOUSES:
        wid, created = _get_or_create(
            cur,
            "SELECT warehouse_id FROM warehouses WHERE name = %s", (name,),
            "INSERT INTO warehouses (name, location, capacity) VALUES (%s, %s, %s)",
            (name, location, capacity), "warehouse_id")
        warehouse_ids[name] = wid
        added["warehouses"] += int(created)

    for sku, name, desc, price, reorder, supplier in PRODUCTS:
        pid, created = _get_or_create(
            cur,
            "SELECT product_id FROM products WHERE sku = %s", (sku,),
            "INSERT INTO products (sku, name, description, unit_price, reorder_level, supplier_id) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (sku, name, desc, price, reorder, supplier_ids[supplier]), "product_id")
        product_ids[sku] = pid
        product_prices[sku] = price
        added["products"] += int(created)

    for sku, wname, qty in INVENTORY:
        exists = _first(
            cur, "SELECT inventory_id FROM inventory WHERE product_id = %s AND warehouse_id = %s",
            (product_ids[sku], warehouse_ids[wname]))
        if not exists:
            cur.execute(
                "INSERT INTO inventory (product_id, warehouse_id, quantity) VALUES (%s, %s, %s)",
                (product_ids[sku], warehouse_ids[wname], qty))
            added["inventory"] += 1

    for supplier, wname, status, days_ago, items in PURCHASE_ORDERS:
        cur.execute(
            "INSERT INTO purchase_orders (supplier_id, warehouse_id, status, order_date) "
            "VALUES (%s, %s, %s, %s) RETURNING po_id",
            (supplier_ids[supplier], warehouse_ids[wname], status, _ts(days_ago)))
        po_id = cur.fetchone()["po_id"]
        added["purchase_orders"] += 1
        for sku, qty, cost in items:
            cur.execute(
                "INSERT INTO purchase_order_items (po_id, product_id, quantity, unit_cost) "
                "VALUES (%s, %s, %s, %s)", (po_id, product_ids[sku], qty, cost))

    for customer, wname, status, days_ago, items, shipment in SALES_ORDERS:
        cur.execute(
            "INSERT INTO sales_orders (customer_name, warehouse_id, status, order_date) "
            "VALUES (%s, %s, %s, %s) RETURNING so_id",
            (customer, warehouse_ids[wname], status, _ts(days_ago)))
        so_id = cur.fetchone()["so_id"]
        added["sales_orders"] += 1
        for sku, qty in items:
            cur.execute(
                "INSERT INTO sales_order_items (so_id, product_id, quantity, unit_price) "
                "VALUES (%s, %s, %s, %s)", (so_id, product_ids[sku], qty, product_prices[sku]))
        if shipment:
            carrier, tracking, sh_status, shipped_ago, delivered_ago = shipment
            cur.execute(
                "INSERT INTO shipments (so_id, carrier, tracking_number, status, shipped_date, delivered_date) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                (so_id, carrier, tracking, sh_status, _ts(shipped_ago), _ts(delivered_ago)))
            added["shipments"] += 1

    conn.commit()
    cur.close()
    return {"seeded": True, "message": "Demo data loaded successfully.", "added": added}
