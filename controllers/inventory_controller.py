import psycopg2
from db.db import get_connection


def get_all_inventory():
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT i.inventory_id, i.quantity,
                   p.product_id, p.sku, p.name AS product_name, p.reorder_level,
                   w.warehouse_id, w.name AS warehouse_name
            FROM inventory i
            JOIN products p ON i.product_id = p.product_id
            JOIN warehouses w ON i.warehouse_id = w.warehouse_id
            ORDER BY w.name, p.name
        """)
        rows = cur.fetchall()
        cur.close()
        return rows, 200
    except Exception as e:
        print(e)
        return {"error": "Failed to fetch inventory"}, 500
    finally:
        conn.close()


def get_inventory_by_id(inventory_id):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT i.inventory_id, i.quantity,
                   p.product_id, p.sku, p.name AS product_name,
                   w.warehouse_id, w.name AS warehouse_name
            FROM inventory i
            JOIN products p ON i.product_id = p.product_id
            JOIN warehouses w ON i.warehouse_id = w.warehouse_id
            WHERE i.inventory_id = %s
        """, (inventory_id,))
        row = cur.fetchone()
        cur.close()
        if row is None:
            return {"error": "Inventory record not found"}, 404
        return row, 200
    except Exception as e:
        print(e)
        return {"error": "Failed to fetch inventory record"}, 500
    finally:
        conn.close()


def create_inventory_record(data):
    """
    Creates a new (product, warehouse) stock record.
    If one already exists for that pair, returns a 409 -- use the
    /adjust endpoint to change quantity on an existing record instead.
    """
    product_id = data.get("product_id")
    warehouse_id = data.get("warehouse_id")
    quantity = data.get("quantity", 0)

    if product_id is None or warehouse_id is None:
        return {"error": "product_id and warehouse_id are required"}, 400
    if quantity < 0:
        return {"error": "quantity cannot be negative"}, 400

    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO inventory (product_id, warehouse_id, quantity)
            VALUES (%s, %s, %s)
            RETURNING *
            """,
            (product_id, warehouse_id, quantity),
        )
        row = cur.fetchone()
        conn.commit()
        cur.close()
        return row, 201
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        return {
            "error": "An inventory record for this product/warehouse already exists. Use PATCH /adjust instead."
        }, 409
    except psycopg2.errors.ForeignKeyViolation:
        conn.rollback()
        return {"error": "product_id or warehouse_id does not exist"}, 400
    except Exception as e:
        conn.rollback()
        print(e)
        return {"error": "Failed to create inventory record"}, 500
    finally:
        conn.close()


def delete_inventory_record(inventory_id):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "DELETE FROM inventory WHERE inventory_id = %s RETURNING *",
            (inventory_id,),
        )
        row = cur.fetchone()
        conn.commit()
        cur.close()
        if row is None:
            return {"error": "Inventory record not found"}, 404
        return {"message": "Inventory record deleted", "inventory": row}, 200
    except Exception as e:
        conn.rollback()
        print(e)
        return {"error": "Failed to delete inventory record"}, 500
    finally:
        conn.close()


def adjust_stock(data):
    """
    Business logic endpoint: safely increment or decrement stock for a
    (product_id, warehouse_id) pair in a single transaction.

    Body: { "product_id": 1, "warehouse_id": 1, "change": -5 }
    Positive change = stock in (e.g. received from supplier).
    Negative change = stock out (e.g. sold/shipped).

    Uses "SELECT ... FOR UPDATE" to lock the row for the duration of the
    transaction, preventing two concurrent requests from both reading the
    same quantity and causing a lost update / going negative.
    """
    product_id = data.get("product_id")
    warehouse_id = data.get("warehouse_id")
    change = data.get("change")

    if product_id is None or warehouse_id is None or change is None:
        return {"error": "product_id, warehouse_id, and change are required"}, 400

    conn = get_connection()
    try:
        cur = conn.cursor()

        # Lock the row so concurrent adjustments can't race each other
        cur.execute(
            """
            SELECT inventory_id, quantity FROM inventory
            WHERE product_id = %s AND warehouse_id = %s
            FOR UPDATE
            """,
            (product_id, warehouse_id),
        )
        record = cur.fetchone()

        if record is None:
            conn.rollback()
            return {
                "error": "No inventory record exists for this product/warehouse. Create one first."
            }, 404

        new_quantity = record["quantity"] + change
        if new_quantity < 0:
            conn.rollback()
            return {
                "error": f"Cannot apply change of {change}: only {record['quantity']} in stock."
            }, 400

        cur.execute(
            """
            UPDATE inventory SET quantity = %s
            WHERE inventory_id = %s
            RETURNING *
            """,
            (new_quantity, record["inventory_id"]),
        )
        updated = cur.fetchone()
        conn.commit()
        cur.close()
        return updated, 200
    except Exception as e:
        conn.rollback()
        print(e)
        return {"error": "Failed to adjust stock"}, 500
    finally:
        conn.close()
