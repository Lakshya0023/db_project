import os
import sqlite3
import re
import datetime
import shutil
from dotenv import load_dotenv

load_dotenv()

DB_TYPE = os.getenv("DB_TYPE", "auto")  # 'postgres', 'sqlite', or 'auto'

# Cache whether PostgreSQL is available
_USE_POSTGRES = None


def get_sqlite_db_path():
    """
    Returns a writable SQLite database path.
    In serverless environments like Vercel / AWS Lambda where /var/task is read-only,
    this automatically copies/creates the database in /tmp/warehouse.db.
    """
    bundle_db = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "warehouse.db")
    
    is_serverless = bool(
        os.getenv("VERCEL") or 
        os.getenv("AWS_LAMBDA_FUNCTION_NAME") or 
        os.getenv("LAMBDA_TASK_ROOT") or
        os.getenv("NOW_REGION")
    )
    
    # Check if project directory is read-only
    db_dir = os.path.dirname(bundle_db)
    is_readonly = not os.access(db_dir, os.W_OK) if os.path.exists(db_dir) else True

    if is_serverless or is_readonly:
        tmp_db = "/tmp/warehouse.db"
        if not os.path.exists(tmp_db):
            if os.path.exists(bundle_db):
                try:
                    shutil.copyfile(bundle_db, tmp_db)
                except Exception as e:
                    print(f"Notice: Could not copy bundle DB to /tmp: {e}")
        return tmp_db

    return bundle_db


def get_postgres_dsn():
    """Returns PostgreSQL connection string or None if not configured."""
    for key in ("DATABASE_URL", "POSTGRES_URL", "POSTGRES_PRISMA_URL", "POSTGRES_URL_NON_POOLING"):
        val = os.getenv(key)
        if val:
            if val.startswith("postgres://"):
                val = val.replace("postgres://", "postgresql://", 1)
            return val
    
    # Check if explicit host is provided
    host = os.getenv("DB_HOST")
    if host and host != "localhost":
        return None  # Will use individual host params
    if host == "localhost":
        return "localhost"
    return None


def is_postgres_available():
    global _USE_POSTGRES
    if _USE_POSTGRES is not None:
        return _USE_POSTGRES

    if DB_TYPE == "sqlite":
        _USE_POSTGRES = False
        return False

    dsn = get_postgres_dsn()
    try:
        import psycopg2
        import psycopg2.extras
        if dsn and dsn != "localhost":
            conn = psycopg2.connect(dsn, connect_timeout=3)
        else:
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
        init_postgres_db()
        return True
    except Exception as e:
        if DB_TYPE == "postgres":
            raise
        _USE_POSTGRES = False
        return False


def init_postgres_db():
    """Ensure tables exist in PostgreSQL if connected to a fresh cloud DB."""
    try:
        import psycopg2
        dsn = get_postgres_dsn()
        if dsn and dsn != "localhost":
            conn = psycopg2.connect(dsn)
        else:
            conn = psycopg2.connect(
                host=os.getenv("DB_HOST", "localhost"),
                port=os.getenv("DB_PORT", "5432"),
                dbname=os.getenv("DB_NAME", "warehouse_db"),
                user=os.getenv("DB_USER", "postgres"),
                password=os.getenv("DB_PASSWORD", "")
            )
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM information_schema.tables WHERE table_name = 'products'")
        if cur.fetchone() is None:
            schema_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "schema.sql")
            if os.path.exists(schema_file):
                with open(schema_file, "r") as f:
                    cur.execute(f.read())
                conn.commit()
                print("✅ PostgreSQL schema initialized from schema.sql")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Notice: PostgreSQL schema check: {e}")


class SQLiteCursorWrapper:
    def __init__(self, raw_cursor, raw_conn=None):
        self._cur = raw_cursor
        self._conn = raw_conn
        self._emulated_row = None
        self._emulated_rows = None

    def execute(self, query, params=None):
        self._emulated_row = None
        self._emulated_rows = None

        # 1. Strip 'FOR UPDATE' for SQLite compatibility
        clean_query = re.sub(r'\s+FOR\s+UPDATE\b', '', query, flags=re.IGNORECASE).strip()
        
        # 2. Replace %s with ? for SQLite parameters
        clean_query = clean_query.replace('%s', '?')

        param_tuple = tuple(params) if params is not None else ()

        # Try native execution first (works if SQLite version >= 3.35 supports RETURNING)
        try:
            res = self._cur.execute(clean_query, param_tuple) if params is not None else self._cur.execute(clean_query)
            return res
        except sqlite3.IntegrityError as e:
            self._handle_integrity_error(e)
        except sqlite3.OperationalError as e:
            err_text = str(e).lower()
            # If SQLite fails because of RETURNING syntax error in older SQLite versions:
            if "returning" in err_text or "syntax error" in err_text:
                return self._emulate_returning(clean_query, param_tuple)
            raise

    def _handle_integrity_error(self, e):
        err_msg = str(e).lower()
        try:
            import psycopg2.errors
            if "unique" in err_msg:
                raise psycopg2.errors.UniqueViolation(str(e))
            elif "foreign key" in err_msg:
                raise psycopg2.errors.ForeignKeyViolation(str(e))
        except ImportError:
            pass
        raise e

    def _emulate_returning(self, query, params):
        """Fallback for older SQLite runtimes that do not support RETURNING syntax."""
        # Detect statement type
        upper_q = query.upper()
        returning_match = re.search(r'\s+RETURNING\s+(.+)$', query, flags=re.IGNORECASE)
        if not returning_match:
            # Not a RETURNING issue, re-raise
            return self._cur.execute(query, params)

        query_without_returning = query[:returning_match.start()].strip()

        # Handle INSERT ... RETURNING
        if upper_q.startswith("INSERT INTO"):
            table_match = re.search(r'INSERT\s+INTO\s+([a-zA-Z0-9_]+)', query, flags=re.IGNORECASE)
            table_name = table_match.group(1) if table_match else None

            self._cur.execute(query_without_returning, params)
            last_id = self._cur.lastrowid
            if table_name and last_id:
                temp_cur = self._conn.cursor() if self._conn else self._cur
                temp_cur.execute(f"SELECT * FROM {table_name} WHERE rowid = ?", (last_id,))
                row = temp_cur.fetchone()
                self._emulated_row = dict(row) if row else None
            return self._cur

        # Handle UPDATE ... WHERE ... RETURNING
        elif upper_q.startswith("UPDATE"):
            table_match = re.search(r'UPDATE\s+([a-zA-Z0-9_]+)', query, flags=re.IGNORECASE)
            table_name = table_match.group(1) if table_match else None
            where_match = re.search(r'WHERE\s+(.+)$', query_without_returning, flags=re.IGNORECASE)

            # We can execute update and then select
            self._cur.execute(query_without_returning, params)
            if table_name and where_match:
                # Find matching row from WHERE parameters (usually the last param is the ID)
                temp_cur = self._conn.cursor() if self._conn else self._cur
                where_clause = where_match.group(1)
                num_params_in_where = where_clause.count('?')
                where_params = params[-num_params_in_where:] if num_params_in_where > 0 else ()
                temp_cur.execute(f"SELECT * FROM {table_name} WHERE {where_clause}", where_params)
                row = temp_cur.fetchone()
                self._emulated_row = dict(row) if row else None
            return self._cur

        # Handle DELETE ... WHERE ... RETURNING
        elif upper_q.startswith("DELETE FROM"):
            table_match = re.search(r'DELETE\s+FROM\s+([a-zA-Z0-9_]+)', query, flags=re.IGNORECASE)
            table_name = table_match.group(1) if table_match else None
            where_match = re.search(r'WHERE\s+(.+)$', query_without_returning, flags=re.IGNORECASE)

            if table_name and where_match:
                temp_cur = self._conn.cursor() if self._conn else self._cur
                where_clause = where_match.group(1)
                temp_cur.execute(f"SELECT * FROM {table_name} WHERE {where_clause}", params)
                row = temp_cur.fetchone()
                self._emulated_row = dict(row) if row else None

            self._cur.execute(query_without_returning, params)
            return self._cur

        return self._cur.execute(query_without_returning, params)

    def fetchone(self):
        if self._emulated_row is not None:
            r = self._emulated_row
            self._emulated_row = None
            return r
        row = self._cur.fetchone()
        if row is None:
            return None
        return dict(row)

    def fetchall(self):
        if self._emulated_rows is not None:
            r = self._emulated_rows
            self._emulated_rows = None
            return r
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
        return SQLiteCursorWrapper(self._conn.cursor(), self._conn)

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


def init_sqlite_db(db_path):
    """Initializes SQLite tables and sample data if not already present."""
    # Ensure directory exists
    os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON;")
    cur = conn.cursor()

    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='products'")
    if cur.fetchone() is None:
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

        -- Sample Seed Data
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
        dsn = get_postgres_dsn()
        if dsn and dsn != "localhost":
            conn = psycopg2.connect(
                dsn,
                cursor_factory=psycopg2.extras.RealDictCursor,
            )
        else:
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
        # SQLite mode (with serverless /tmp auto-redirection)
        db_path = get_sqlite_db_path()
        init_sqlite_db(db_path)
        conn = sqlite3.connect(db_path)
        conn.row_factory = dict_factory
        conn.execute("PRAGMA foreign_keys = ON;")
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
        engine = "PostgreSQL" if is_postgres_available() else f"Embedded SQLite ({get_sqlite_db_path()})"
        print(f"✅ Database connected via {engine} at {result['now']}")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
