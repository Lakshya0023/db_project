# Warehouse & Supply Chain Management System (Flask + Modern Web UI)

A full-stack, enterprise-grade Supply Chain & Warehouse Management System with a PostgreSQL database, Flask REST API backend, and modern single-page dashboard frontend.

## 1. Install PostgreSQL and create the database
```bash
createdb warehouse_db
```

## 2. Load the schema + sample data
```bash
psql -d warehouse_db -f schema.sql
```

## 3. Create a virtual environment and install dependencies
```bash
python3 -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## 4. Configure environment variables
```bash
cp .env.example .env
# then edit .env with your real DB_USER / DB_PASSWORD
```

## 5. Run the Server (Backend + Frontend together)
```bash
python app.py
```
- **Web UI Dashboard**: Open [http://localhost:5000](http://localhost:5000) in any web browser.
- **API Health Check**: [http://localhost:5000/api/health](http://localhost:5000/api/health)

---

## 6. Web UI Dashboard Modules
1. **📊 Dashboard**: Real-time KPI summary, critical low-stock alert banner, warehouse stock distribution chart, and quick shortcuts.
2. **📦 Inventory Matrix**: Live multi-warehouse stock level matrix, status indicators, and 1-click **Quick Stock Adjust** modal (safe transaction-locked increments/decrements).
3. **🏷️ Products Catalog**: Product SKU registry, unit pricing, reorder thresholds, supplier tags, and create/edit/delete modals.
4. **🏢 Warehouses**: Storage facility capacity utilization, location maps, and itemized warehouse stock inspector.
5. **🚚 Suppliers**: Vendor directory, contact details, and vendor catalog inspector.
6. **📥 Purchase Orders**: Inbound stock orders, line item calculations, and 1-click **Receive Stock** action (auto-increments warehouse inventory).
7. **📤 Sales Orders**: Customer sales orders, line item calculations, and 1-click **Fulfill Order** action (verifies availability, decrements inventory, generates shipment).
8. **🚢 Shipments**: Logistics pipeline (Preparing -> Shipped -> Delivered) with carrier assignment and live tracking numbers.

---

## 7. REST API Reference


### Products
| Method | Endpoint                          | Description                    |
|--------|------------------------------------|---------------------------------|
| GET    | /api/products                      | List all products               |
| GET    | /api/products/<id>                 | Get one product                 |
| POST   | /api/products                      | Create a product                |
| PUT    | /api/products/<id>                 | Update a product                |
| DELETE | /api/products/<id>                 | Delete a product                |
| GET    | /api/products/reports/low-stock    | Products at/below reorder level |

### Suppliers
| Method | Endpoint                        | Description                        |
|--------|-----------------------------------|-------------------------------------|
| GET    | /api/suppliers                    | List all suppliers                  |
| GET    | /api/suppliers/<id>                | Get one supplier                    |
| GET    | /api/suppliers/<id>/products       | Products supplied by this supplier  |
| POST   | /api/suppliers                    | Create a supplier                   |
| PUT    | /api/suppliers/<id>                | Update a supplier                   |
| DELETE | /api/suppliers/<id>                | Delete a supplier                   |

Example create product request body:
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

### Warehouses
| Method | Endpoint                        | Description                        |
|--------|-------------------------------------|---------------------------------|
| GET    | /api/warehouses                    | List all warehouses                |
| GET    | /api/warehouses/<id>                | Get one warehouse                  |
| GET    | /api/warehouses/<id>/stock          | All inventory held at this warehouse |
| POST   | /api/warehouses                    | Create a warehouse                 |
| PUT    | /api/warehouses/<id>                | Update a warehouse                 |
| DELETE | /api/warehouses/<id>                | Delete a warehouse                 |

### Inventory
| Method | Endpoint              | Description                                              |
|--------|-------------------------|------------------------------------------------------------|
| GET    | /api/inventory          | List all inventory records (joined with product + warehouse) |
| GET    | /api/inventory/<id>      | Get one inventory record                                   |
| POST   | /api/inventory           | Create a new (product, warehouse) stock record              |
| DELETE | /api/inventory/<id>      | Delete an inventory record                                  |
| PATCH  | /api/inventory/adjust    | Safely increment/decrement stock (transaction-locked)       |

Example adjust request body (stock out, e.g. fulfilling a sale):
```json
{
  "product_id": 3,
  "warehouse_id": 2,
  "change": -2
}
```
Example adjust request body (stock in, e.g. receiving from a supplier):
```json
{
  "product_id": 3,
  "warehouse_id": 2,
  "change": 50
}
```
`adjust_stock` uses `SELECT ... FOR UPDATE` to lock the row during the
transaction, so two simultaneous requests can't both read the same starting
quantity and cause a lost update — and it rejects any change that would push
quantity below zero.

### Purchase Orders
| Method | Endpoint                          | Description                                             |
|--------|--------------------------------------|-----------------------------------------------------------|
| GET    | /api/purchase-orders                | List all purchase orders                                   |
| GET    | /api/purchase-orders/<id>            | Get one PO with its line items                              |
| POST   | /api/purchase-orders                | Create a PO with line items (header + items in one transaction) |
| PUT    | /api/purchase-orders/<id>            | Update status to 'pending' or 'cancelled'                   |
| DELETE | /api/purchase-orders/<id>            | Delete a purchase order                                     |
| POST   | /api/purchase-orders/<id>/receive    | Mark received + add stock into inventory (transactional)    |

Example create request body:
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
`POST /api/purchase-orders/<id>/receive` takes no body. It locks the PO and
every affected inventory row with `SELECT ... FOR UPDATE`, adds each line
item's quantity into inventory (creating the inventory row if the product
has never been stocked at that warehouse before), flips the PO's status to
`received`, and commits everything together. If the PO isn't `pending`
(already received or cancelled), it's rejected with a 400 and nothing is
changed — this prevents double-crediting stock if the endpoint is called
twice by accident.

### Sales Orders
| Method | Endpoint                        | Description                                                |
|--------|-------------------------------------|--------------------------------------------------------------|
| GET    | /api/sales-orders                  | List all sales orders                                        |
| GET    | /api/sales-orders/<id>              | Get one order with its items and shipment (if any)            |
| POST   | /api/sales-orders                  | Create an order with line items (does not touch stock yet)    |
| DELETE | /api/sales-orders/<id>              | Delete a sales order                                          |
| POST   | /api/sales-orders/<id>/cancel       | Cancel a pending order                                        |
| POST   | /api/sales-orders/<id>/fulfill      | Check stock, decrement inventory, create shipment (transactional) |

Example create request body:
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

`POST /api/sales-orders/<id>/fulfill` is the most important endpoint in the
whole system to understand for your demo/report. In one transaction it:
1. Locks the order row; rejects if the order isn't `pending`.
2. Locks every affected inventory row with `SELECT ... FOR UPDATE`.
3. **Checks stock for every line item first**, before changing anything. If
   even one item is short, the entire transaction rolls back and a `409`
   is returned listing exactly which items were short and by how much —
   this avoids partially fulfilling an order (e.g. shipping 2 of 3 items
   and leaving the third backordered with no record of it).
4. Only if everything is available does it decrement inventory for every item.
5. Creates a `shipments` row with status `preparing`.
6. Marks the order `fulfilled`.

### Shipments
| Method | Endpoint                        | Description                                  |
|--------|-------------------------------------|-------------------------------------------------|
| GET    | /api/shipments                     | List all shipments                               |
| GET    | /api/shipments/<id>                 | Get one shipment                                 |
| POST   | /api/shipments/<id>/ship            | Mark shipment 'shipped' (optionally set carrier/tracking) |
| POST   | /api/shipments/<id>/deliver         | Mark shipment 'delivered'                        |

Shipments follow a strict status progression: `preparing` → `shipped` →
`delivered`. Each transition is only allowed from the correct prior state
(e.g. you can't mark something `delivered` before it's been `shipped`),
which is enforced in the controller, not just the DB `CHECK` constraint.

Example ship request body (optional fields):
```json
{
  "carrier": "BlueDart",
  "tracking_number": "BD1234567890"
}
```

## 7. Project structure
```
warehouse-backend-flask/
├── app.py                          # entry point, registers blueprints
├── db/
│   └── db.py                       # psycopg2 connection helper
├── controllers/
│   ├── products_controller.py      # DB logic for products
│   ├── suppliers_controller.py     # DB logic for suppliers
│   ├── warehouses_controller.py    # DB logic for warehouses
│   ├── inventory_controller.py     # DB logic for inventory (incl. adjust_stock)
│   ├── purchase_orders_controller.py  # DB logic for POs (incl. receive_purchase_order)
│   ├── sales_orders_controller.py     # DB logic for sales orders (incl. fulfill_sales_order)
│   └── shipments_controller.py        # DB logic for shipments (ship/deliver transitions)
├── routes/
│   ├── products.py                 # Flask blueprint for /api/products
│   ├── suppliers.py                # Flask blueprint for /api/suppliers
│   ├── warehouses.py               # Flask blueprint for /api/warehouses
│   ├── inventory.py                # Flask blueprint for /api/inventory
│   ├── purchase_orders.py          # Flask blueprint for /api/purchase-orders
│   ├── sales_orders.py             # Flask blueprint for /api/sales-orders
│   └── shipments.py                # Flask blueprint for /api/shipments
├── schema.sql
├── requirements.txt
└── .env.example
```

## 8. Next module to build
Only `auth` remains — signup/login using `bcrypt` (hash passwords) and
`PyJWT` (issue a JWT on login, verify it in a decorator for protected routes).
Follow the same pattern: `controllers/auth_controller.py` + `routes/auth.py`,
then register it in `app.py`.

## 9. Build order so far
1. ~~warehouses~~ ✅
2. ~~inventory~~ ✅
3. ~~purchase_orders~~ ✅
4. ~~sales_orders + shipments~~ ✅
5. auth (last)
