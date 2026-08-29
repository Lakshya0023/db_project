from db.db import get_connection


def get_all_warehouses():
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM warehouses ORDER BY warehouse_id")
        rows = cur.fetchall()
        cur.close()
        return rows, 200
    except Exception as e:
        print(e)
        return {"error": "Failed to fetch warehouses"}, 500
    finally:
        conn.close()


def get_warehouse_by_id(warehouse_id):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM warehouses WHERE warehouse_id = %s", (warehouse_id,))
        row = cur.fetchone()
        cur.close()
        if row is None:
            return {"error": "Warehouse not found"}, 404
        return row, 200
    except Exception as e:
        print(e)
        return {"error": "Failed to fetch warehouse"}, 500
    finally:
        conn.close()


def create_warehouse(data):
    name = data.get("name")
    location = data.get("location")
    capacity = data.get("capacity")

    if not name:
        return {"error": "name is required"}, 400

    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO warehouses (name, location, capacity)
            VALUES (%s, %s, %s)
            RETURNING *
            """,
            (name, location, capacity),
        )
        row = cur.fetchone()
        conn.commit()
        cur.close()
        return row, 201
    except Exception as e:
        conn.rollback()
        print(e)
        return {"error": "Failed to create warehouse"}, 500
    finally:
        conn.close()


def update_warehouse(warehouse_id, data):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE warehouses
            SET name = COALESCE(%s, name),
                location = COALESCE(%s, location),
                capacity = COALESCE(%s, capacity)
            WHERE warehouse_id = %s
            RETURNING *
            """,
            (
                data.get("name"),
                data.get("location"),
                data.get("capacity"),
                warehouse_id,
            ),
        )
        row = cur.fetchone()
        conn.commit()
        cur.close()
        if row is None:
            return {"error": "Warehouse not found"}, 404
        return row, 200
    except Exception as e:
        conn.rollback()
        print(e)
        return {"error": "Failed to update warehouse"}, 500
    finally:
        conn.close()


def delete_warehouse(warehouse_id):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "DELETE FROM warehouses WHERE warehouse_id = %s RETURNING *",
            (warehouse_id,),
        )
        row = cur.fetchone()
        conn.commit()
        cur.close()
        if row is None:
            return {"error": "Warehouse not found"}, 404
        return {"message": "Warehouse deleted", "warehouse": row}, 200
    except Exception as e:
        conn.rollback()
        print(e)
        # inventory/purchase_orders/sales_orders reference warehouse_id without
        # cascade, so deleting a warehouse still in use will raise a FK error
        # and land here as a generic 500 -> caught and explained below instead.
        if "foreign key" in str(e).lower():
            return {
                "error": "Cannot delete warehouse: it still has inventory or orders linked to it."
            }, 409
        return {"error": "Failed to delete warehouse"}, 500
    finally:
        conn.close()


def get_warehouse_stock(warehouse_id):
    """All inventory (product + quantity) currently held at this warehouse."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT warehouse_id FROM warehouses WHERE warehouse_id = %s",
            (warehouse_id,),
        )
        if cur.fetchone() is None:
            cur.close()
            return {"error": "Warehouse not found"}, 404

        cur.execute(
            """
            SELECT i.inventory_id, p.product_id, p.sku, p.name, i.quantity, p.reorder_level
            FROM inventory i
            JOIN products p ON i.product_id = p.product_id
            WHERE i.warehouse_id = %s
            ORDER BY p.name
            """,
            (warehouse_id,),
        )
        rows = cur.fetchall()
        cur.close()
        return rows, 200
    except Exception as e:
        print(e)
        return {"error": "Failed to fetch warehouse stock"}, 500
    finally:
        conn.close()
