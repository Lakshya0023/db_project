"""
Automated checks for the Query Lab (22 SELECT, 5 INSERT, 5 UPDATE).

Run against the SQLite fallback (uses a throw-away copy of warehouse.db):

    python test_query_lab.py

Run against PostgreSQL (the database must already contain schema.sql):

    DB_TYPE=postgres DATABASE_URL=postgresql://user:pass@localhost/warehouse_db python test_query_lab.py
"""
import os
import shutil
import tempfile
import unittest
from unittest import mock

import db.db as dbmod

_USING_SQLITE = os.getenv("DB_TYPE", "auto") == "sqlite" or not (
    os.getenv("DATABASE_URL") or os.getenv("DB_HOST"))

if _USING_SQLITE:
    os.environ["DB_TYPE"] = "sqlite"
    _tmp = tempfile.mkdtemp()
    _db_copy = os.path.join(_tmp, "warehouse.db")
    _bundle = os.path.join(os.path.dirname(os.path.abspath(__file__)), "warehouse.db")
    if os.path.exists(_bundle):
        shutil.copyfile(_bundle, _db_copy)
    dbmod.get_sqlite_db_path = lambda: _db_copy      # never touch the real file

from app import app  # noqa: E402  (import after the DB path is patched)

BASE = "/api/query-lab"


class QueryLabTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = app.test_client()
        r = cls.client.post(f"{BASE}/seed")
        assert r.status_code == 200, r.get_json()

    # ---- helpers ---------------------------------------------------------
    def get(self, path):
        return self.client.get(path)

    def post(self, path, payload=None):
        return self.client.post(path, json=payload or {})

    def id_of(self, table, id_col, where_col, value):
        rows = self.get(f"/api/{table}").get_json()
        return next(r[id_col] for r in rows if r[where_col] == value)

    # ---- catalogue -------------------------------------------------------
    def test_catalog_meets_requirements(self):
        counts = self.get(f"{BASE}/catalog").get_json()["counts"]
        self.assertGreaterEqual(counts["select"], 20)
        self.assertGreaterEqual(counts["insert"], 4)
        self.assertGreaterEqual(counts["update"], 4)

    def test_seed_is_idempotent(self):
        body = self.post(f"{BASE}/seed").get_json()
        self.assertFalse(body["seeded"])

    # ---- SELECT ----------------------------------------------------------
    def test_every_select_runs_and_returns_rows(self):
        catalog = self.get(f"{BASE}/catalog").get_json()["select"]
        for q in catalog:
            with self.subTest(query=q["id"], title=q["title"]):
                r = self.get(f"{BASE}/select/{q['id']}")
                self.assertEqual(r.status_code, 200, r.get_json())
                body = r.get_json()
                self.assertGreater(body["row_count"], 0, f"Q{q['id']} returned no rows")
                self.assertEqual(body["row_count"], len(body["rows"]))

    def test_select_parameters(self):
        r = self.get(f"{BASE}/select/1?min_price=2000").get_json()
        self.assertTrue(all(row["unit_price"] >= 2000 for row in r["rows"]))
        r = self.get(f"{BASE}/select/2?term=BEARING").get_json()
        self.assertTrue(any("Bearing" in row["name"] for row in r["rows"]))
        r = self.get(f"{BASE}/select/22?sku=SKU-2008").get_json()
        self.assertGreater(r["row_count"], 0)

    def test_select_is_injection_safe(self):
        r = self.get(f"{BASE}/select/2?term=x'; DROP TABLE products; --")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.get_json()["row_count"], 0)
        self.assertGreater(len(self.get("/api/products").get_json()), 0)

    def test_select_validation(self):
        self.assertEqual(self.get(f"{BASE}/select/9999").status_code, 404)
        self.assertEqual(self.get(f"{BASE}/select/1?min_price=abc").status_code, 400)

    # ---- INSERT ----------------------------------------------------------
    def test_i1_insert_supplier(self):
        r = self.post(f"{BASE}/dml/I1", {"name": "Test Supplier X", "address": ""})
        self.assertEqual(r.status_code, 200, r.get_json())
        self.assertEqual(r.get_json()["rows"][0]["name"], "Test Supplier X")
        self.assertIsNone(r.get_json()["rows"][0]["address"])          # blank optional -> NULL
        self.assertEqual(self.post(f"{BASE}/dml/I1", {"name": ""}).status_code, 400)

    def test_i2_product_with_opening_stock_and_rollback(self):
        sup = self.id_of("suppliers", "supplier_id", "name", "Acme Traders")
        wh = self.id_of("warehouses", "warehouse_id", "name", "North Depot")
        payload = {"sku": "TEST-I2-001", "name": "Test Item", "unit_price": 99.5,
                   "reorder_level": 3, "supplier_id": sup, "warehouse_id": wh, "opening_stock": 17}
        r = self.post(f"{BASE}/dml/I2", payload)
        self.assertEqual(r.status_code, 200, r.get_json())
        self.assertEqual(r.get_json()["rows"][0]["quantity"], 17)
        self.assertEqual(len(r.get_json()["statements"]), 2)
        self.assertEqual(self.post(f"{BASE}/dml/I2", payload).status_code, 409)   # duplicate SKU
        bad = dict(payload, sku="TEST-I2-002", warehouse_id=987654)               # FK failure on 2nd insert
        self.assertEqual(self.post(f"{BASE}/dml/I2", bad).status_code, 400)
        skus = [p["sku"] for p in self.get("/api/products").get_json()]
        self.assertNotIn("TEST-I2-002", skus, "first insert must be rolled back with the second")

    def test_i3_restock_po(self):
        sup = self.id_of("suppliers", "supplier_id", "name", "Apex Electricals")
        wh = self.id_of("warehouses", "warehouse_id", "name", "Central Warehouse")
        r = self.post(f"{BASE}/dml/I3", {"supplier_id": sup, "warehouse_id": wh, "multiplier": 2})
        self.assertEqual(r.status_code, 200, r.get_json())
        item = next(x for x in r.get_json()["rows"] if x["sku"] == "SKU-2001")
        self.assertEqual(item["quantity"], 12 * 2 - 6)         # reorder 12 x2 - stock 6
        # a supplier with no products -> clean refusal, and no empty PO left behind (rollback)
        new_sup = self.post(f"{BASE}/dml/I1", {"name": "No Products Ltd"}).get_json()["rows"][0]["supplier_id"]
        before = len(self.get("/api/purchase-orders").get_json())
        r2 = self.post(f"{BASE}/dml/I3", {"supplier_id": new_sup, "warehouse_id": wh, "multiplier": 2})
        self.assertEqual(r2.status_code, 422)
        self.assertEqual(before, len(self.get("/api/purchase-orders").get_json()))

    def test_i4_missing_shipments(self):
        r = self.post(f"{BASE}/dml/I4", {"carrier": "TestCarrier"})
        self.assertEqual(r.status_code, 200, r.get_json())
        self.assertGreaterEqual(len(r.get_json()["rows"]), 2)
        self.assertTrue(r.get_json()["rows"][0]["tracking_number"].startswith("TRK-"))
        self.assertEqual(self.post(f"{BASE}/dml/I4", {"carrier": "TestCarrier"}).status_code, 422)

    def test_i5_initialise_inventory(self):
        r = self.post(f"{BASE}/dml/I2", {"sku": "TEST-I5-P", "name": "I5 helper", "unit_price": 1,
                                         "reorder_level": 1, "opening_stock": 1,
                                         "supplier_id": self.id_of("suppliers", "supplier_id", "name", "Acme Traders"),
                                         "warehouse_id": self.id_of("warehouses", "warehouse_id", "name", "Central Warehouse")})
        self.assertEqual(r.status_code, 200)
        wh = self.id_of("warehouses", "warehouse_id", "name", "South Annex")
        r = self.post(f"{BASE}/dml/I5", {"warehouse_id": wh})
        self.assertEqual(r.status_code, 200, r.get_json())
        total_products = len(self.get("/api/products").get_json())
        self.assertEqual(len(r.get_json()["rows"]), total_products)     # one row per product now
        self.assertEqual(self.post(f"{BASE}/dml/I5", {"warehouse_id": wh}).status_code, 422)

    # ---- UPDATE ----------------------------------------------------------
    def test_u1_revise_prices(self):
        sup = self.id_of("suppliers", "supplier_id", "name", "SteelCraft Industries")
        before = {p["sku"]: float(p["unit_price"]) for p in self.get("/api/products").get_json()
                  if p["supplier_id"] == sup}
        r = self.post(f"{BASE}/dml/U1", {"supplier_id": sup, "percent": 10})
        self.assertEqual(r.status_code, 200, r.get_json())
        for row in r.get_json()["rows"]:
            self.assertAlmostEqual(row["unit_price"], round(before[row["sku"]] * 1.10, 2), places=2)
        self.assertEqual(self.post(f"{BASE}/dml/U1", {"supplier_id": sup, "percent": -95}).status_code, 400)

    def test_u2_reorder_fast_movers(self):
        r = self.post(f"{BASE}/dml/U2", {"min_units": 50, "increase": 5})
        self.assertEqual(r.status_code, 200, r.get_json())
        self.assertIn("higher reorder level", r.get_json()["message"])

    def test_u3_transfer_stock(self):
        pid = self.id_of("products", "product_id", "sku", "SKU-2010")
        a = self.id_of("warehouses", "warehouse_id", "name", "Central Warehouse")
        b = self.id_of("warehouses", "warehouse_id", "name", "South Annex")   # no SKU-2010 row yet
        r = self.post(f"{BASE}/dml/U3", {"product_id": pid, "from_warehouse_id": a,
                                         "to_warehouse_id": b, "quantity": 20})
        self.assertEqual(r.status_code, 200, r.get_json())
        qty = {row["warehouse"]: row["quantity"] for row in r.get_json()["rows"]}
        self.assertEqual(qty["South Annex"], 20)
        self.assertEqual(qty["Central Warehouse"], 200)
        too_much = self.post(f"{BASE}/dml/U3", {"product_id": pid, "from_warehouse_id": a,
                                                "to_warehouse_id": b, "quantity": 99999})
        self.assertEqual(too_much.status_code, 409)
        same = self.post(f"{BASE}/dml/U3", {"product_id": pid, "from_warehouse_id": a,
                                            "to_warehouse_id": a, "quantity": 1})
        self.assertEqual(same.status_code, 400)

    def test_u4_cancel_stale_pos(self):
        r = self.post(f"{BASE}/dml/U4", {"days": 30})
        self.assertEqual(r.status_code, 200, r.get_json())
        self.assertGreaterEqual(len(r.get_json()["rows"]), 1)
        self.assertEqual(self.post(f"{BASE}/dml/U4", {"days": 30}).status_code, 422)

    def test_u5_switch_carrier(self):
        # make sure at least one 'preparing' shipment uses BlueDart (seed has one)
        r = self.post(f"{BASE}/dml/U5", {"old_carrier": "BlueDart", "new_carrier": "Delhivery"})
        self.assertEqual(r.status_code, 200, r.get_json())
        self.assertTrue(all(row["carrier"] == "Delhivery" for row in r.get_json()["rows"]))
        self.assertEqual(self.post(f"{BASE}/dml/U5", {"old_carrier": "X", "new_carrier": "x"}).status_code, 400)

    def test_unknown_operation(self):
        self.assertEqual(self.post(f"{BASE}/dml/Z9").status_code, 404)


if __name__ == "__main__":
    unittest.main(verbosity=2)
