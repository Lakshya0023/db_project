import os
import sqlite3
import re
import datetime
from dotenv import load_dotenv

load_dotenv()

# Determine DB backend mode
DB_TYPE = os.getenv("DB_TYPE", "auto")  # 'postgres', 'sqlite', or 'auto'
SQLITE_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "warehouse.db")

# Cache whether PostgreSQL is available
_USE_POSTGRES = None


def is_postgres_available():
    global _USE_POSTGRES
    if _USE_POSTGRES is not None:
        return _USE_POSTGRES

    if DB_TYPE == "sqlite":
        _USE_POSTGRES = False
        return False

    try:
        import psycopg2
        import psycopg2.extras
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST", "localhost"),
            port=os.getenv("DB_PORT", "5432"),
            dbname=os.getenv("DB_NAME", "warehouse_db"),
            user=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASSWORD", ""),
            connect_timeout=2
        )
        conn.close()
        _USE_POSTGRES = True
        return True
    except Exception:
        if DB_TYPE == "postgres":
            raise
        _USE_POSTGRES = False
        return False


class SQLiteCursorWrapper:
    def __init__(self, raw_cursor):
        self._cur = raw_cursor

    def execute(self, query, params=None):
        # 1. Strip 'FOR UPDATE' for SQLite compatibility
        clean_query = re.sub(r'\s+FOR\s+UPDATE\b', '', query, flags=re.IGNORECASE)
        
        # 2. Replace %s with ? for SQLite parameters
        clean_query = clean_query.replace('%s', '?')

        try:
            if params is not None:
                # Convert params tuple/list for SQLite
                return self._cur.execute(clean_query, tuple(params))
            else:
                return self._cur.execute(clean_query)
        except sqlite3.IntegrityError as e:
            # Map SQLite integrity errors to psycopg2-like behavior if needed
            import psycopg2.errors
            err_msg = str(e).lower()
            if "unique" in err_msg:
                raise psycopg2.errors.UniqueViolation(str(e))
            elif "foreign key" in err_msg:
                raise psycopg2.errors.ForeignKeyViolation(str(e))
            raise

    def fetchone(self):
        row = self._cur.fetchone()
        if row is None:
            return None
        return dict(row)

    def fetchall(self):
        rows = self._cur.fetchall()
        return [dict(r) for r in rows]

    def close(self):
        self._cur.close()

    @property
    def rowcount(self):
        return self._cur.rowcount


class SQLiteConnectionWrapper:
    def __init__(self, raw_conn):
        self._conn = raw_conn

    def cursor(self):
        return SQLiteCursorWrapper(self._conn.cursor())

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._conn.close()


def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


def init_sqlite_db():
    """Initializes SQLite tables and sample data if not already present."""
    conn = sqlite3.connect(SQLITE_DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    cur = conn.cursor()

    # Check if products table exists
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='products'")
    if cur.fetchone() is None:
        # Schema definition compatible with SQLite
        schema_script = """
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK (role IN ('admin', 'staff', 'supplier')),
            created_at TEXT DEFAULT (datetime('now', 'localtime'))
        );

        CREATE TABLE IF NOT EXISTS suppliers (
            supplier_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            contact_email TEXT,
            contact_phone TEXT,
            address TEXT,
            created_at TEXT DEFAULT (datetime('now', 'localtime'))
        );

        CREATE TABLE IF NOT EXISTS warehouses (
            warehouse_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            location TEXT,
            capacity INTEGER CHECK (capacity >= 0),
            created_at TEXT DEFAULT (datetime('now', 'localtime'))
        );

        CREATE TABLE IF NOT EXISTS products (
            product_id INTEGER PRIMARY KEY AUTOINCREMENT,
            sku TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            unit_price REAL NOT NULL CHECK (unit_price >= 0),
            reorder_level INTEGER DEFAULT 10 CHECK (reorder_level >= 0),
            supplier_id INTEGER REFERENCES suppliers(supplier_id) ON DELETE SET NULL,
            created_at TEXT DEFAULT (datetime('now', 'localtime'))
        );

        CREATE TABLE IF NOT EXISTS inventory (
            inventory_id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL REFERENCES products(product_id) ON DELETE CASCADE,
            warehouse_id INTEGER NOT NULL REFERENCES warehouses(warehouse_id) ON DELETE CASCADE,
            quantity INTEGER NOT NULL DEFAULT 0 CHECK (quantity >= 0),
            UNIQUE (product_id, warehouse_id)
        );

        CREATE TABLE IF NOT EXISTS purchase_orders (
            po_id INTEGER PRIMARY KEY AUTOINCREMENT,
            supplier_id INTEGER NOT NULL REFERENCES suppliers(supplier_id),
            warehouse_id INTEGER NOT NULL REFERENCES warehouses(warehouse_id),
            status TEXT DEFAULT 'pending' CHECK (status IN ('pending','received','cancelled')),
            order_date TEXT DEFAULT (datetime('now', 'localtime'))
        );

        CREATE TABLE IF NOT EXISTS purchase_order_items (
            po_item_id INTEGER PRIMARY KEY AUTOINCREMENT,
            po_id INTEGER NOT NULL REFERENCES purchase_orders(po_id) ON DELETE CASCADE,
            product_id INTEGER NOT NULL REFERENCES products(product_id),
            quantity INTEGER NOT NULL CHECK (quantity > 0),
            unit_cost REAL NOT NULL CHECK (unit_cost >= 0)
        );

        CREATE TABLE IF NOT EXISTS sales_orders (
            so_id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT NOT NULL,
            warehouse_id INTEGER NOT NULL REFERENCES warehouses(warehouse_id),
            status TEXT DEFAULT 'pending' CHECK (status IN ('pending','fulfilled','cancelled')),
            order_date TEXT DEFAULT (datetime('now', 'localtime'))
        );

        CREATE TABLE IF NOT EXISTS sales_order_items (
            so_item_id INTEGER PRIMARY KEY AUTOINCREMENT,
            so_id INTEGER NOT NULL REFERENCES sales_orders(so_id) ON DELETE CASCADE,
            product_id INTEGER NOT NULL REFERENCES products(product_id),
            quantity INTEGER NOT NULL CHECK (quantity > 0),
            unit_price REAL NOT NULL CHECK (unit_price >= 0)
        );

        CREATE TABLE IF NOT EXISTS shipments (
            shipment_id INTEGER PRIMARY KEY AUTOINCREMENT,
            so_id INTEGER NOT NULL REFERENCES sales_orders(so_id) ON DELETE CASCADE,
            carrier TEXT,
            tracking_number TEXT,
            status TEXT DEFAULT 'preparing' CHECK (status IN ('preparing','shipped','delivered')),
            shipped_date TEXT,
            delivered_date TEXT
        );

        -- Sample Data
        INSERT INTO warehouses (name, location, capacity) VALUES
        ('Central Warehouse', 'Chennai, TN', 10000),
        ('North Depot', 'Delhi, DL', 5000);

        INSERT INTO suppliers (name, contact_email, contact_phone, address) VALUES
        ('Acme Traders', 'contact@acme.com', '9876543210', 'Mumbai, MH'),
        ('Global Parts Co.', 'sales@globalparts.com', '9123456780', 'Bangalore, KA');

        INSERT INTO products (sku, name, description, unit_price, reorder_level, supplier_id) VALUES
        ('SKU-1001', 'Steel Bolt 10mm', 'Pack of 100', 250.00, 20, 1),
        ('SKU-1002', 'Ball Bearing 6mm', 'Pack of 50', 480.00, 15, 2),
        ('SKU-1003', 'Hydraulic Hose 2m', 'Reinforced rubber hose', 950.00, 10, 1);

        INSERT INTO inventory (product_id, warehouse_id, quantity) VALUES
        (1, 1, 100),
        (2, 1, 40),
        (3, 2, 8);

        INSERT INTO users (name, email, password_hash, role) VALUES
        ('Admin User', 'admin@warehouse.com', '$2b$10$replace_with_real_bcrypt_hash', 'admin');
        """
        cur.executescript(schema_script)
        conn.commit()
    cur.close()
    conn.close()


def get_connection():
    """
    Opens a new database connection.
    Connects to PostgreSQL if available, or seamlessly uses SQLite.
    """
    if is_postgres_available():
        import psycopg2
        import psycopg2.extras
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST", "localhost"),
            port=os.getenv("DB_PORT", "5432"),
            dbname=os.getenv("DB_NAME", "warehouse_db"),
            user=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASSWORD", ""),
            cursor_factory=psycopg2.extras.RealDictCursor,
        )
        return conn
    else:
        # SQLite mode
        init_sqlite_db()
        conn = sqlite3.connect(SQLITE_DB_PATH)
        conn.row_factory = dict_factory
        conn.execute("PRAGMA foreign_keys = ON;")
        # Register custom SQL function NOW()
        conn.create_function("NOW", 0, lambda: datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        return SQLiteConnectionWrapper(conn)


def test_connection():
    """Called once at startup to confirm the DB is reachable."""
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT NOW() as now")
        result = cur.fetchone()
        cur.close()
        conn.close()
        engine = "PostgreSQL" if is_postgres_available() else f"Embedded SQLite ({SQLITE_DB_PATH})"
        print(f"✅ Database connected via {engine} at {result['now']}")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
