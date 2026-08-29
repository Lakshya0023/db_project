import psycopg2
from db.db import get_connection


def get_all_purchase_orders():
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT po.po_id, po.status, po.order_date,
                   s.supplier_id, s.name AS supplier_name,
                   w.warehouse_id, w.name AS warehouse_name
            FROM purchase_orders po
            JOIN suppliers s ON po.supplier_id = s.supplier_id
            JOIN warehouses w ON po.warehouse_id = w.warehouse_id
            ORDER BY po.order_date DESC
        """)
        rows = cur.fetchall()
        cur.close()
        return rows, 200
    except Exception as e:
        print(e)
        return {"error": "Failed to fetch purchase orders"}, 500
    finally:
        conn.close()


def get_purchase_order_by_id(po_id):
    """Returns the PO header along with its line items."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT po.po_id, po.status, po.order_date,
                   s.supplier_id, s.name AS supplier_name,
                   w.warehouse_id, w.name AS warehouse_name
            FROM purchase_orders po
            JOIN suppliers s ON po.supplier_id = s.supplier_id
            JOIN warehouses w ON po.warehouse_id = w.warehouse_id
            WHERE po.po_id = %s
        """, (po_id,))
        header = cur.fetchone()
        if header is None:
            cur.close()
            return {"error": "Purchase order not found"}, 404

        cur.execute("""
            SELECT poi.po_item_id, poi.quantity, poi.unit_cost,
                   p.product_id, p.sku, p.name AS product_name
            FROM purchase_order_items poi
            JOIN products p ON poi.product_id = p.product_id
            WHERE poi.po_id = %s
            ORDER BY poi.po_item_id
        """, (po_id,))
        items = cur.fetchall()
        cur.close()

        header["items"] = items
        return header, 200
    except Exception as e:
        print(e)
        return {"error": "Failed to fetch purchase order"}, 500
    finally:
        conn.close()


def create_purchase_order(data):
    """
    Creates a PO header + its line items in a single transaction.

    Body:
    {
      "supplier_id": 1,
      "warehouse_id": 1,
      "items": [
        {"product_id": 1, "quantity": 50, "unit_cost": 200.00},
        {"product_id": 2, "quantity": 30, "unit_cost": 400.00}
      ]
    }
    """
    supplier_id = data.get("supplier_id")
    warehouse_id = data.get("warehouse_id")
    items = data.get("items")

    if not supplier_id or not warehouse_id:
        return {"error": "supplier_id and warehouse_id are required"}, 400
    if not items or not isinstance(items, list) or len(items) == 0:
        return {"error": "items must be a non-empty array"}, 400

    for item in items:
        if not item.get("product_id") or not item.get("quantity") or item.get("unit_cost") is None:
            return {"error": "each item requires product_id, quantity, and unit_cost"}, 400
        if item["quantity"] <= 0:
            return {"error": "item quantity must be greater than 0"}, 400

    conn = get_connection()
    try:
        cur = conn.cursor()

        cur.execute(
            """
            INSERT INTO purchase_orders (supplier_id, warehouse_id, status)
            VALUES (%s, %s, 'pending')
            RETURNING *
            """,
            (supplier_id, warehouse_id),
        )
        po = cur.fetchone()

        inserted_items = []
        for item in items:
            cur.execute(
                """
                INSERT INTO purchase_order_items (po_id, product_id, quantity, unit_cost)
                VALUES (%s, %s, %s, %s)
                RETURNING *
                """,
                (po["po_id"], item["product_id"], item["quantity"], item["unit_cost"]),
            )
            inserted_items.append(cur.fetchone())

        conn.commit()
        cur.close()

        po["items"] = inserted_items
        return po, 201
    except psycopg2.errors.ForeignKeyViolation:
        conn.rollback()
        return {"error": "supplier_id, warehouse_id, or a product_id does not exist"}, 400
    except Exception as e:
        conn.rollback()
        print(e)
        return {"error": "Failed to create purchase order"}, 500
    finally:
        conn.close()


def update_purchase_order_status(po_id, data):
    """Update only the status field, e.g. to 'cancelled'. Use /receive to mark 'received'."""
    status = data.get("status")
    if status not in ("pending", "cancelled"):
        return {
            "error": "status must be 'pending' or 'cancelled' (use /receive to mark as received)"
        }, 400

    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE purchase_orders SET status = %s
            WHERE po_id = %s
            RETURNING *
            """,
            (status, po_id),
        )
        row = cur.fetchone()
        conn.commit()
        cur.close()
        if row is None:
            return {"error": "Purchase order not found"}, 404
        return row, 200
    except Exception as e:
        conn.rollback()
        print(e)
        return {"error": "Failed to update purchase order"}, 500
    finally:
        conn.close()


def delete_purchase_order(po_id):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "DELETE FROM purchase_orders WHERE po_id = %s RETURNING *", (po_id,)
        )
        row = cur.fetchone()
        conn.commit()
        cur.close()
        if row is None:
            return {"error": "Purchase order not found"}, 404
        return {"message": "Purchase order deleted", "purchase_order": row}, 200
    except Exception as e:
        conn.rollback()
        print(e)
        return {"error": "Failed to delete purchase order"}, 500
    finally:
        conn.close()


def receive_purchase_order(po_id):
    """
    Business logic endpoint: marks a PO as 'received' and adds its item
    quantities into inventory at the PO's warehouse -- all in one transaction.

    For each line item:
      - locks (or creates) the matching inventory row with SELECT ... FOR UPDATE
      - increments quantity by the ordered amount
    If the PO is not 'pending', or doesn't exist, nothing is changed.
    """
    conn = get_connection()
    try:
        cur = conn.cursor()

        cur.execute(
            "SELECT * FROM purchase_orders WHERE po_id = %s FOR UPDATE", (po_id,)
        )
        po = cur.fetchone()
        if po is None:
            conn.rollback()
            return {"error": "Purchase order not found"}, 404
        if po["status"] != "pending":
            conn.rollback()
            return {"error": f"Purchase order is already '{po['status']}', cannot receive again"}, 400

        cur.execute(
            "SELECT * FROM purchase_order_items WHERE po_id = %s", (po_id,)
        )
        items = cur.fetchall()

        for item in items:
            # Lock existing inventory row for this product/warehouse, if any
            cur.execute(
                """
                SELECT inventory_id, quantity FROM inventory
                WHERE product_id = %s AND warehouse_id = %s
                FOR UPDATE
                """,
                (item["product_id"], po["warehouse_id"]),
            )
            inv = cur.fetchone()

            if inv is None:
                # First time this product is stocked at this warehouse
                cur.execute(
                    """
                    INSERT INTO inventory (product_id, warehouse_id, quantity)
                    VALUES (%s, %s, %s)
                    """,
                    (item["product_id"], po["warehouse_id"], item["quantity"]),
                )
            else:
                cur.execute(
                    "UPDATE inventory SET quantity = quantity + %s WHERE inventory_id = %s",
                    (item["quantity"], inv["inventory_id"]),
                )

        cur.execute(
            """
            UPDATE purchase_orders SET status = 'received'
            WHERE po_id = %s
            RETURNING *
            """,
            (po_id,),
        )
        updated_po = cur.fetchone()

        conn.commit()
        cur.close()
        return updated_po, 200
    except Exception as e:
        conn.rollback()
        print(e)
        return {"error": "Failed to receive purchase order"}, 500
    finally:
        conn.close()
