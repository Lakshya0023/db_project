import psycopg2
from db.db import get_connection


def get_all_sales_orders():
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT so.so_id, so.customer_name, so.status, so.order_date,
                   w.warehouse_id, w.name AS warehouse_name
            FROM sales_orders so
            JOIN warehouses w ON so.warehouse_id = w.warehouse_id
            ORDER BY so.order_date DESC
        """)
        rows = cur.fetchall()
        cur.close()
        return rows, 200
    except Exception as e:
        print(e)
        return {"error": "Failed to fetch sales orders"}, 500
    finally:
        conn.close()


def get_sales_order_by_id(so_id):
    """Returns the sales order header, its line items, and any shipment."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT so.so_id, so.customer_name, so.status, so.order_date,
                   w.warehouse_id, w.name AS warehouse_name
            FROM sales_orders so
            JOIN warehouses w ON so.warehouse_id = w.warehouse_id
            WHERE so.so_id = %s
        """, (so_id,))
        header = cur.fetchone()
        if header is None:
            cur.close()
            return {"error": "Sales order not found"}, 404

        cur.execute("""
            SELECT soi.so_item_id, soi.quantity, soi.unit_price,
                   p.product_id, p.sku, p.name AS product_name
            FROM sales_order_items soi
            JOIN products p ON soi.product_id = p.product_id
            WHERE soi.so_id = %s
            ORDER BY soi.so_item_id
        """, (so_id,))
        items = cur.fetchall()

        cur.execute("SELECT * FROM shipments WHERE so_id = %s", (so_id,))
        shipment = cur.fetchone()
        cur.close()

        header["items"] = items
        header["shipment"] = shipment
        return header, 200
    except Exception as e:
        print(e)
        return {"error": "Failed to fetch sales order"}, 500
    finally:
        conn.close()


def create_sales_order(data):
    """
    Creates a sales order header + line items in a single transaction.
    Does NOT touch inventory yet -- that only happens on /fulfill.

    Body:
    {
      "customer_name": "Jane Doe",
      "warehouse_id": 1,
      "items": [
        {"product_id": 1, "quantity": 5, "unit_price": 300.00},
        {"product_id": 2, "quantity": 2, "unit_price": 550.00}
      ]
    }
    """
    customer_name = data.get("customer_name")
    warehouse_id = data.get("warehouse_id")
    items = data.get("items")

    if not customer_name or not warehouse_id:
        return {"error": "customer_name and warehouse_id are required"}, 400
    if not items or not isinstance(items, list) or len(items) == 0:
        return {"error": "items must be a non-empty array"}, 400

    for item in items:
        if not item.get("product_id") or not item.get("quantity") or item.get("unit_price") is None:
            return {"error": "each item requires product_id, quantity, and unit_price"}, 400
        if item["quantity"] <= 0:
            return {"error": "item quantity must be greater than 0"}, 400

    conn = get_connection()
    try:
        cur = conn.cursor()

        cur.execute(
            """
            INSERT INTO sales_orders (customer_name, warehouse_id, status)
            VALUES (%s, %s, 'pending')
            RETURNING *
            """,
            (customer_name, warehouse_id),
        )
        so = cur.fetchone()

        inserted_items = []
        for item in items:
            cur.execute(
                """
                INSERT INTO sales_order_items (so_id, product_id, quantity, unit_price)
                VALUES (%s, %s, %s, %s)
                RETURNING *
                """,
                (so["so_id"], item["product_id"], item["quantity"], item["unit_price"]),
            )
            inserted_items.append(cur.fetchone())

        conn.commit()
        cur.close()

        so["items"] = inserted_items
        return so, 201
    except psycopg2.errors.ForeignKeyViolation:
        conn.rollback()
        return {"error": "warehouse_id or a product_id does not exist"}, 400
    except Exception as e:
        conn.rollback()
        print(e)
        return {"error": "Failed to create sales order"}, 500
    finally:
        conn.close()


def delete_sales_order(so_id):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "DELETE FROM sales_orders WHERE so_id = %s RETURNING *", (so_id,)
        )
        row = cur.fetchone()
        conn.commit()
        cur.close()
        if row is None:
            return {"error": "Sales order not found"}, 404
        return {"message": "Sales order deleted", "sales_order": row}, 200
    except Exception as e:
        conn.rollback()
        print(e)
        return {"error": "Failed to delete sales order"}, 500
    finally:
        conn.close()


def cancel_sales_order(so_id):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM sales_orders WHERE so_id = %s FOR UPDATE", (so_id,))
        so = cur.fetchone()
        if so is None:
            conn.rollback()
            return {"error": "Sales order not found"}, 404
        if so["status"] != "pending":
            conn.rollback()
            return {"error": f"Order is already '{so['status']}', cannot cancel"}, 400

        cur.execute(
            "UPDATE sales_orders SET status = 'cancelled' WHERE so_id = %s RETURNING *",
            (so_id,),
        )
        row = cur.fetchone()
        conn.commit()
        cur.close()
        return row, 200
    except Exception as e:
        conn.rollback()
        print(e)
        return {"error": "Failed to cancel sales order"}, 500
    finally:
        conn.close()


def fulfill_sales_order(so_id):
    """
    Business logic endpoint: fulfills a pending sales order in one transaction.

    1. Locks the sales order row; rejects if not 'pending'.
    2. Locks each affected inventory row (product+warehouse) with FOR UPDATE.
    3. Verifies every item has enough stock -- if ANY item is short, the whole
       transaction rolls back and nothing is changed (partial fulfillment
       would leave the warehouse in an inconsistent state).
    4. Decrements inventory for every item.
    5. Creates a 'preparing' shipment record for the order.
    6. Marks the order 'fulfilled'.
    """
    conn = get_connection()
    try:
        cur = conn.cursor()

        cur.execute("SELECT * FROM sales_orders WHERE so_id = %s FOR UPDATE", (so_id,))
        so = cur.fetchone()
        if so is None:
            conn.rollback()
            return {"error": "Sales order not found"}, 404
        if so["status"] != "pending":
            conn.rollback()
            return {"error": f"Order is already '{so['status']}', cannot fulfill"}, 400

        cur.execute("SELECT * FROM sales_order_items WHERE so_id = %s", (so_id,))
        items = cur.fetchall()

        # First pass: lock every relevant inventory row and check stock.
        # If anything is short, bail out before changing any data.
        locked_inventory = {}
        shortages = []
        for item in items:
            cur.execute(
                """
                SELECT inventory_id, quantity FROM inventory
                WHERE product_id = %s AND warehouse_id = %s
                FOR UPDATE
                """,
                (item["product_id"], so["warehouse_id"]),
            )
            inv = cur.fetchone()
            available = inv["quantity"] if inv else 0

            if available < item["quantity"]:
                shortages.append({
                    "product_id": item["product_id"],
                    "requested": item["quantity"],
                    "available": available,
                })
            else:
                locked_inventory[item["so_item_id"]] = inv

        if shortages:
            conn.rollback()
            return {
                "error": "Insufficient stock to fulfill this order",
                "shortages": shortages,
            }, 409

        # Second pass: all items confirmed available -- now decrement.
        for item in items:
            inv = locked_inventory[item["so_item_id"]]
            cur.execute(
                "UPDATE inventory SET quantity = quantity - %s WHERE inventory_id = %s",
                (item["quantity"], inv["inventory_id"]),
            )

        cur.execute(
            """
            INSERT INTO shipments (so_id, status)
            VALUES (%s, 'preparing')
            RETURNING *
            """,
            (so_id,),
        )
        shipment = cur.fetchone()

        cur.execute(
            "UPDATE sales_orders SET status = 'fulfilled' WHERE so_id = %s RETURNING *",
            (so_id,),
        )
        updated_so = cur.fetchone()

        conn.commit()
        cur.close()

        updated_so["shipment"] = shipment
        return updated_so, 200
    except Exception as e:
        conn.rollback()
        print(e)
        return {"error": "Failed to fulfill sales order"}, 500
    finally:
        conn.close()
