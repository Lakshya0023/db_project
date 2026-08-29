import psycopg2
from db.db import get_connection


def get_all_products():
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT p.*, s.name AS supplier_name
            FROM products p
            LEFT JOIN suppliers s ON p.supplier_id = s.supplier_id
            ORDER BY p.product_id
        """)
        rows = cur.fetchall()
        cur.close()
        return rows, 200
    except Exception as e:
        print(e)
        return {"error": "Failed to fetch products"}, 500
    finally:
        conn.close()


def get_product_by_id(product_id):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM products WHERE product_id = %s", (product_id,))
        row = cur.fetchone()
        cur.close()
        if row is None:
            return {"error": "Product not found"}, 404
        return row, 200
    except Exception as e:
        print(e)
        return {"error": "Failed to fetch product"}, 500
    finally:
        conn.close()


def create_product(data):
    sku = data.get("sku")
    name = data.get("name")
    description = data.get("description")
    unit_price = data.get("unit_price")
    reorder_level = data.get("reorder_level", 10)
    supplier_id = data.get("supplier_id")

    if not sku or not name or unit_price is None:
        return {"error": "sku, name, and unit_price are required"}, 400

    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO products (sku, name, description, unit_price, reorder_level, supplier_id)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING *
            """,
            (sku, name, description, unit_price, reorder_level, supplier_id),
        )
        row = cur.fetchone()
        conn.commit()
        cur.close()
        return row, 201
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        return {"error": "A product with this SKU already exists"}, 409
    except Exception as e:
        conn.rollback()
        print(e)
        return {"error": "Failed to create product"}, 500
    finally:
        conn.close()


def update_product(product_id, data):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE products
            SET sku = COALESCE(%s, sku),
                name = COALESCE(%s, name),
                description = COALESCE(%s, description),
                unit_price = COALESCE(%s, unit_price),
                reorder_level = COALESCE(%s, reorder_level),
                supplier_id = COALESCE(%s, supplier_id)
            WHERE product_id = %s
            RETURNING *
            """,
            (
                data.get("sku"),
                data.get("name"),
                data.get("description"),
                data.get("unit_price"),
                data.get("reorder_level"),
                data.get("supplier_id"),
                product_id,
            ),
        )
        row = cur.fetchone()
        conn.commit()
        cur.close()
        if row is None:
            return {"error": "Product not found"}, 404
        return row, 200
    except Exception as e:
        conn.rollback()
        print(e)
        return {"error": "Failed to update product"}, 500
    finally:
        conn.close()


def delete_product(product_id):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "DELETE FROM products WHERE product_id = %s RETURNING *", (product_id,)
        )
        row = cur.fetchone()
        conn.commit()
        cur.close()
        if row is None:
            return {"error": "Product not found"}, 404
        return {"message": "Product deleted", "product": row}, 200
    except Exception as e:
        conn.rollback()
        print(e)
        return {"error": "Failed to delete product"}, 500
    finally:
        conn.close()


def get_low_stock_products():
    """Business logic endpoint: products whose stock has fallen at/below reorder_level."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT p.product_id, p.sku, p.name, p.reorder_level,
                   i.warehouse_id, w.name AS warehouse_name, i.quantity
            FROM inventory i
            JOIN products p ON i.product_id = p.product_id
            JOIN warehouses w ON i.warehouse_id = w.warehouse_id
            WHERE i.quantity <= p.reorder_level
            ORDER BY i.quantity ASC
        """)
        rows = cur.fetchall()
        cur.close()
        return rows, 200
    except Exception as e:
        print(e)
        return {"error": "Failed to fetch low-stock report"}, 500
    finally:
        conn.close()
