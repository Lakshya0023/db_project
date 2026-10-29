# 📦 Warehouse & Supply Chain Management System

A full-stack Warehouse & Supply Chain Management System built as a database coursework project. It combines a **Flask REST API**, a **relational database**, and a **modern single-page dashboard UI** to manage products, suppliers, warehouses, inventory, purchase orders, sales orders, and shipments.

🔗 **Live Demo:** [dbproject-ten.vercel.app](https://dbproject-ten.vercel.app)

---

## ✨ Features

- **Real-time dashboard** with KPIs, low-stock alerts, and warehouse stock distribution
- **Multi-warehouse inventory** tracking with safe, transaction-locked stock adjustments
- **Purchase order workflow** – create POs and receive stock with one click
- **Sales order workflow** – create orders and fulfill them with automatic stock verification
- **Shipment tracking** – `Preparing → Shipped → Delivered` with carrier and tracking numbers
- **Data integrity** – row-level locking (`SELECT ... FOR UPDATE`), atomic transactions, and `CHECK` constraints
- **RESTful API** with a modular controller/route architecture

---

## 🛠️ Tech Stack

| Layer      | Technology                         |
|------------|------------------------------------|
| Backend    | Python, Flask (Blueprints)         |
| Database   | PostgreSQL (`psycopg2`)            |
| Frontend   | HTML, CSS, JavaScript (SPA dashboard) |
| Deployment | Vercel                             |

---

## 🖥️ Web UI Modules

| Module | Description |
|--------|-------------|
| 📊 **Dashboard** | Real-time KPI summary, critical low-stock alert banner, warehouse stock distribution chart, and quick shortcuts |
| 📦 **Inventory Matrix** | Live multi-warehouse stock matrix, status indicators, and a 1-click **Quick Stock Adjust** modal (transaction-locked increments/decrements) |
| 🏷️ **Products Catalog** | SKU registry, unit pricing, reorder thresholds, supplier tags, and create/edit/delete modals |
| 🏢 **Warehouses** | Capacity utilization, locations, and an itemized warehouse stock inspector |
| 🚚 **Suppliers** | Vendor directory, contact details, and vendor catalog inspector |
| 📥 **Purchase Orders** | Inbound orders, line-item calculations, and 1-click **Receive Stock** (auto-increments inventory) |
| 📤 **Sales Orders** | Customer orders, line-item calculations, and 1-click **Fulfill Order** (verifies availability, decrements inventory, creates shipment) |
| 🚢 **Shipments** | Logistics pipeline (Preparing → Shipped → Delivered) with carrier assignment and tracking numbers |

---

## 🚀 Getting Started

### Prerequisites

- Python 3.8+
- PostgreSQL
- `pip`

### 1. Install PostgreSQL and create the database

```bash
createdb warehouse_db
```

### 2. Load the schema + sample data

```bash
psql -d warehouse_db -f schema.sql
```

### 3. Create a virtual environment and install dependencies

```bash
python3 -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 4. Configure environment variables

```bash
cp .env.example .env
# then edit .env with your real DB_USER / DB_PASSWORD
```

### 5. Run the server (backend + frontend together)

```bash
python app.py
```

- **Web UI Dashboard:** <http://localhost:5000>
- **API Health Check:** <http://localhost:5000/api/health>

---

## 📚 REST API Reference

> Replace `<id>` with the numeric ID of the record.

### Products

| Method | Endpoint                          | Description                     |
|--------|-----------------------------------|---------------------------------|
| GET    | `/api/products`                   | List all products               |
| GET    | `/api/products/<id>`              | Get one product                 |
| POST   | `/api/products`                   | Create a product                |
| PUT    | `/api/products/<id>`              | Update a product                |
| DELETE | `/api/products/<id>`              | Delete a product               |
| GET    | `/api/products/reports/low-stock` | Products at/below reorder level |

Example create request:

```json
{
  "sku": "SKU-1004",
  "name": "Copper Wire Roll",
  "description": "50m roll, 2mm gauge",
  "unit_price": 620.00,
  "reorder_level": 12,
  "supplier_id": 1
}
```

### Suppliers

| Method | Endpoint                         | Description                        |
|--------|----------------------------------|------------------------------------|
| GET    | `/api/suppliers`                 | List all suppliers                 |
| GET    | `/api/suppliers/<id>`            | Get one supplier                   |
| GET    | `/api/suppliers/<id>/products`   | Products supplied by this supplier |
| POST   | `/api/suppliers`                 | Create a supplier                  |
| PUT    | `/api/suppliers/<id>`            | Update a supplier                  |
| DELETE | `/api/suppliers/<id>`            | Delete a supplier                  |

### Warehouses

| Method | Endpoint                       | Description                          |
|--------|--------------------------------|--------------------------------------|
| GET    | `/api/warehouses`              | List all warehouses                  |
| GET    | `/api/warehouses/<id>`         | Get one warehouse                    |
| GET    | `/api/warehouses/<id>/stock`   | All inventory held at this warehouse |
| POST   | `/api/warehouses`              | Create a warehouse                   |
| PUT    | `/api/warehouses/<id>`         | Update a warehouse                   |
| DELETE | `/api/warehouses/<id>`         | Delete a warehouse                   |

### Inventory

| Method | Endpoint                 | Description                                                  |
|--------|--------------------------|--------------------------------------------------------------|
| GET    | `/api/inventory`         | List all inventory records (joined with product + warehouse) |
| GET    | `/api/inventory/<id>`    | Get one inventory record                                     |
| POST   | `/api/inventory`         | Create a new (product, warehouse) stock record               |
| DELETE | `/api/inventory/<id>`    | Delete an inventory record                                   |
| PATCH  | `/api/inventory/adjust`  | Safely increment/decrement stock (transaction-locked)        |

Example adjust request (stock out, e.g. fulfilling a sale):

```json
{
  "product_id": 3,
  "warehouse_id": 2,
  "change": -2
}
```

Example adjust request (stock in, e.g. receiving from a supplier):

```json
{
  "product_id": 3,
  "warehouse_id": 2,
  "change": 50
}
```

> `adjust_stock` uses `SELECT ... FOR UPDATE` to lock the row during the transaction, so two simultaneous requests can't read the same starting quantity and cause a lost update. It also rejects any change that would push quantity below zero.

### Purchase Orders

| Method | Endpoint                               | Description                                                     |
|--------|----------------------------------------|-----------------------------------------------------------------|
| GET    | `/api/purchase-orders`                 | List all purchase orders                                        |
| GET    | `/api/purchase-orders/<id>`            | Get one PO with its line items                                  |
| POST   | `/api/purchase-orders`                 | Create a PO with line items (header + items in one transaction) |
| PUT    | `/api/purchase-orders/<id>`            | Update status to `pending` or `cancelled`                       |
| DELETE | `/api/purchase-orders/<id>`            | Delete a purchase order                                         |
| POST   | `/api/purchase-orders/<id>/receive`    | Mark received + add stock into inventory (transactional)        |

Example create request:

```json
{
  "supplier_id": 1,
  "warehouse_id": 1,
  "items": [
    {"product_id": 1, "quantity": 50, "unit_cost": 200.00},
    {"product_id": 2, "quantity": 30, "unit_cost": 400.00}
  ]
}
```

> `POST /api/purchase-orders/<id>/receive` takes no body. It locks the PO and every affected inventory row with `SELECT ... FOR UPDATE`, adds each line item's quantity into inventory (creating the inventory row if the product has never been stocked at that warehouse), flips the PO status to `received`, and commits everything together. If the PO isn't `pending` (already received or cancelled), it is rejected with a `400` and nothing changes — preventing double-crediting of stock.

### Sales Orders

| Method | Endpoint                             | Description                                                       |
|--------|--------------------------------------|-------------------------------------------------------------------|
| GET    | `/api/sales-orders`                  | List all sales orders                                             |
| GET    | `/api/sales-orders/<id>`             | Get one order with its items and shipment (if any)                |
| POST   | `/api/sales-orders`                  | Create an order with line items (does not touch stock yet)        |
| DELETE | `/api/sales-orders/<id>`             | Delete a sales order                                              |
| POST   | `/api/sales-orders/<id>/cancel`      | Cancel a pending order                                            |
| POST   | `/api/sales-orders/<id>/fulfill`     | Check stock, decrement inventory, create shipment (transactional) |

Example create request:

```json
{
  "customer_name": "Jane Doe",
  "warehouse_id": 1,
  "items": [
    {"product_id": 1, "quantity": 5, "unit_price": 300.00},
    {"product_id": 2, "quantity": 2, "unit_price": 550.00}
  ]
}
```

**How `POST /api/sales-orders/<id>/fulfill` works** (the core transactional workflow):

1. Locks the order row; rejects if the order isn't `pending`.
2. Locks every affected inventory row with `SELECT ... FOR UPDATE`.
3. **Checks stock for every line item first**, before changing anything. If even one item is short, the entire transaction rolls back and a `409` is returned listing exactly which items are short and by how much — avoiding partial fulfillment.
4. Only if everything is available, decrements inventory for every item.
5. Creates a `shipments` row with status `preparing`.
6. Marks the order `fulfilled`.

### Shipments

| Method | Endpoint                          | Description                                               |
|--------|-----------------------------------|-----------------------------------------------------------|
| GET    | `/api/shipments`                  | List all shipments                                        |
| GET    | `/api/shipments/<id>`             | Get one shipment                                          |
| POST   | `/api/shipments/<id>/ship`        | Mark shipment `shipped` (optionally set carrier/tracking) |
| POST   | `/api/shipments/<id>/deliver`     | Mark shipment `delivered`                                 |

Shipments follow a strict status progression: `preparing` → `shipped` → `delivered`. Each transition is only allowed from the correct prior state (e.g. a shipment can't be marked `delivered` before it's `shipped`), enforced in the controller as well as by the database `CHECK` constraint.

Example ship request (optional fields):

```json
{
  "carrier": "BlueDart",
  "tracking_number": "BD1234567890"
}
```

---

## 🧪 Query Lab (SQL showcase)

The **Query Lab** tab (sidebar → *Database → Query Lab*) demonstrates the SQL behind the project:

| Type | Count | Highlights |
|------|-------|-----------|
| `SELECT` | **22** | joins up to 4 tables, `GROUP BY` / `HAVING`, scalar / `IN` / `NOT EXISTS` subqueries, derived tables, `UNION ALL`, `CASE`, `LIKE`, `LIMIT` |
| `INSERT` | **5** | `INSERT … VALUES`, multi-table transactional insert, `INSERT … SELECT` (bulk), `NOT EXISTS` guard |
| `UPDATE` | **5** | bulk price revision, `UPDATE … WHERE IN (subquery)`, transactional stock transfer, date-based status change |

Each card shows the exact SQL, lets you choose parameters, runs it, and displays the result. INSERT/UPDATE
operations run in a transaction and roll back on any error. Full SQL listing: **[QUERIES.md](QUERIES.md)**.

```bash
python seed_demo_data.py        # optional: load demo data (or click "Load demo data" in the UI)
python test_query_lab.py        # 17 automated checks (SQLite by default)
```

API: `GET /api/query-lab/catalog` · `GET /api/query-lab/select/<1-22>?param=value` · `POST /api/query-lab/dml/<I1-I5|U1-U5>` · `POST /api/query-lab/seed`

---

## 📁 Project Structure

```
db_project/
├── app.py                              # Entry point, registers blueprints
├── db/
│   ├── db.py                           # Database connection helper (PostgreSQL / SQLite)
│   └── seed.py                         # Idempotent demo-data loader
├── controllers/
│   ├── products_controller.py          # DB logic for products
│   ├── suppliers_controller.py         # DB logic for suppliers
│   ├── warehouses_controller.py        # DB logic for warehouses
│   ├── inventory_controller.py         # DB logic for inventory (incl. adjust_stock)
│   ├── purchase_orders_controller.py   # DB logic for POs (incl. receive_purchase_order)
│   ├── sales_orders_controller.py      # DB logic for sales orders (incl. fulfill_sales_order)
│   ├── shipments_controller.py         # DB logic for shipments (ship/deliver transitions)
│   └── query_lab_controller.py         # 22 SELECT + 5 INSERT + 5 UPDATE showcase queries
├── routes/
│   ├── products.py                     # Blueprint for /api/products
│   ├── suppliers.py                    # Blueprint for /api/suppliers
│   ├── warehouses.py                   # Blueprint for /api/warehouses
│   ├── inventory.py                    # Blueprint for /api/inventory
│   ├── purchase_orders.py              # Blueprint for /api/purchase-orders
│   ├── sales_orders.py                 # Blueprint for /api/sales-orders
│   ├── shipments.py                    # Blueprint for /api/shipments
│   └── query_lab.py                    # Blueprint for /api/query-lab
├── templates/                          # HTML templates (dashboard UI)
├── static/                             # CSS, JavaScript, and assets
├── schema.sql                          # Database schema + sample data
├── QUERIES.md                          # Full listing of the Query Lab SQL
├── seed_demo_data.py                   # CLI: load demo data
├── test_query_lab.py                   # Automated tests for the Query Lab
├── requirements.txt                    # Python dependencies
├── vercel.json                         # Vercel deployment config
├── .env.example                        # Sample environment variables
└── .gitignore
```

---

## 🧠 Key Database Concepts Demonstrated

- **Normalized relational schema** with primary/foreign keys and `CHECK` constraints
- **ACID transactions** across multi-table operations (PO receive, sales fulfill)
- **Pessimistic row-level locking** (`SELECT ... FOR UPDATE`) to prevent lost updates and race conditions
- **All-or-nothing validation** – stock is verified for every line item before any change is made
- **State machines** for order and shipment lifecycles
- **Joins and aggregates** for dashboard KPIs and reports
- **Subqueries, set operations, `INSERT … SELECT`, bulk `UPDATE`** – see the Query Lab above
- **Parameterised queries** (no SQL injection) and transactional rollback on failure

---

## 🗺️ Roadmap

- [x] Warehouses
- [x] Inventory
- [x] Purchase Orders
- [x] Sales Orders + Shipments
- [x] Web UI Dashboard
- [ ] Authentication – signup/login with `bcrypt` (password hashing) and `PyJWT` (JWT-protected routes)

---

## 👤 Author

**Lakshya** — [@Lakshya0023](https://github.com/Lakshya0023)

---

## 📄 License

This project was created for educational / coursework purposes.
