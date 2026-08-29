from db.db import get_connection


def get_all_shipments():
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT sh.*, so.customer_name, so.warehouse_id
            FROM shipments sh
            JOIN sales_orders so ON sh.so_id = so.so_id
            ORDER BY sh.shipment_id DESC
        """)
        rows = cur.fetchall()
        cur.close()
        return rows, 200
    except Exception as e:
        print(e)
        return {"error": "Failed to fetch shipments"}, 500
    finally:
        conn.close()


def get_shipment_by_id(shipment_id):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT sh.*, so.customer_name, so.warehouse_id
            FROM shipments sh
            JOIN sales_orders so ON sh.so_id = so.so_id
            WHERE sh.shipment_id = %s
        """, (shipment_id,))
        row = cur.fetchone()
        cur.close()
        if row is None:
            return {"error": "Shipment not found"}, 404
        return row, 200
    except Exception as e:
        print(e)
        return {"error": "Failed to fetch shipment"}, 500
    finally:
        conn.close()


def mark_shipped(shipment_id, data):
    carrier = data.get("carrier")
    tracking_number = data.get("tracking_number")

    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM shipments WHERE shipment_id = %s FOR UPDATE", (shipment_id,))
        shipment = cur.fetchone()
        if shipment is None:
            conn.rollback()
            return {"error": "Shipment not found"}, 404
        if shipment["status"] != "preparing":
            conn.rollback()
            return {"error": f"Shipment is already '{shipment['status']}', cannot mark as shipped"}, 400

        cur.execute(
            """
            UPDATE shipments
            SET status = 'shipped',
                carrier = COALESCE(%s, carrier),
                tracking_number = COALESCE(%s, tracking_number),
                shipped_date = NOW()
            WHERE shipment_id = %s
            RETURNING *
            """,
            (carrier, tracking_number, shipment_id),
        )
        row = cur.fetchone()
        conn.commit()
        cur.close()
        return row, 200
    except Exception as e:
        conn.rollback()
        print(e)
        return {"error": "Failed to mark shipment as shipped"}, 500
    finally:
        conn.close()


def mark_delivered(shipment_id):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM shipments WHERE shipment_id = %s FOR UPDATE", (shipment_id,))
        shipment = cur.fetchone()
        if shipment is None:
            conn.rollback()
            return {"error": "Shipment not found"}, 404
        if shipment["status"] != "shipped":
            conn.rollback()
            return {"error": f"Shipment must be 'shipped' before it can be marked delivered (currently '{shipment['status']}')"}, 400

        cur.execute(
            """
            UPDATE shipments
            SET status = 'delivered', delivered_date = NOW()
            WHERE shipment_id = %s
            RETURNING *
            """,
            (shipment_id,),
        )
        row = cur.fetchone()
        conn.commit()
        cur.close()
        return row, 200
    except Exception as e:
        conn.rollback()
        print(e)
        return {"error": "Failed to mark shipment as delivered"}, 500
    finally:
        conn.close()
