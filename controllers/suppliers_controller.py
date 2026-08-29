import psycopg2
from db.db import get_connection


def get_all_suppliers():
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM suppliers ORDER BY supplier_id")
        rows = cur.fetchall()
        cur.close()
        return rows, 200
    except Exception as e:
        print(e)
        return {"error": "Failed to fetch suppliers"}, 500
    finally:
        conn.close()


def get_supplier_by_id(supplier_id):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM suppliers WHERE supplier_id = %s", (supplier_id,))
        row = cur.fetchone()
        cur.close()
        if row is None:
            return {"error": "Supplier not found"}, 404
        return row, 200
    except Exception as e:
        print(e)
        return {"error": "Failed to fetch supplier"}, 500
    finally:
        conn.close()


def create_supplier(data):
    name = data.get("name")
    contact_email = data.get("contact_email")
    contact_phone = data.get("contact_phone")
    address = data.get("address")

    if not name:
        return {"error": "name is required"}, 400

    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO suppliers (name, contact_email, contact_phone, address)
            VALUES (%s, %s, %s, %s)
            RETURNING *
            """,
            (name, contact_email, contact_phone, address),
        )
        row = cur.fetchone()
        conn.commit()
        cur.close()
        return row, 201
    except Exception as e:
        conn.rollback()
        print(e)
        return {"error": "Failed to create supplier"}, 500
    finally:
        conn.close()


def update_supplier(supplier_id, data):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE suppliers
            SET name = COALESCE(%s, name),
                contact_email = COALESCE(%s, contact_email),
                contact_phone = COALESCE(%s, contact_phone),
                address = COALESCE(%s, address)
            WHERE supplier_id = %s
            RETURNING *
            """,
            (
                data.get("name"),
                data.get("contact_email"),
                data.get("contact_phone"),
                data.get("address"),
                supplier_id,
            ),
        )
        row = cur.fetchone()
        conn.commit()
        cur.close()
        if row is None:
            return {"error": "Supplier not found"}, 404
        return row, 200
    except Exception as e:
        conn.rollback()
        print(e)
        return {"error": "Failed to update supplier"}, 500
    finally:
        conn.close()


def delete_supplier(supplier_id):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "DELETE FROM suppliers WHERE supplier_id = %s RETURNING *", (supplier_id,)
        )
        row = cur.fetchone()
        conn.commit()
        cur.close()
        if row is None:
            return {"error": "Supplier not found"}, 404
        return {"message": "Supplier deleted", "supplier": row}, 200
    except psycopg2.errors.ForeignKeyViolation:
        conn.rollback()
        # purchase_orders.supplier_id has no ON DELETE rule, so this fires
        # if the supplier still has purchase orders tied to it.
        return {
            "error": "Cannot delete supplier: it has related purchase orders. Cancel or reassign those first."
        }, 409
    except Exception as e:
        conn.rollback()
        print(e)
        return {"error": "Failed to delete supplier"}, 500
    finally:
        conn.close()


def get_supplier_products(supplier_id):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT supplier_id FROM suppliers WHERE supplier_id = %s", (supplier_id,)
        )
        if cur.fetchone() is None:
            cur.close()
            return {"error": "Supplier not found"}, 404

        cur.execute(
            "SELECT * FROM products WHERE supplier_id = %s ORDER BY product_id",
            (supplier_id,),
        )
        rows = cur.fetchall()
        cur.close()
        return rows, 200
    except Exception as e:
        print(e)
        return {"error": "Failed to fetch products for supplier"}, 500
    finally:
        conn.close()
