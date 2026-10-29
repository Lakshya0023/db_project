import os
from flask import Flask, jsonify, render_template, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv

from db.db import test_connection
from routes.products import products_bp
from routes.suppliers import suppliers_bp
from routes.warehouses import warehouses_bp
from routes.inventory import inventory_bp
from routes.purchase_orders import purchase_orders_bp
from routes.sales_orders import sales_orders_bp
from routes.shipments import shipments_bp
from routes.query_lab import query_lab_bp

load_dotenv()

app = Flask(__name__, static_folder="static", template_folder="templates")
CORS(app)

# Frontend UI routes
@app.route("/")
@app.route("/dashboard")
def index():
    return render_template("index.html")

# API Health check
@app.route("/api/health")
@app.route("/health")
def health():
    return jsonify({
        "status": "healthy",
        "message": "Warehouse Management System API is running",
        "version": "1.0.0"
    })


# Register blueprints (route prefixes)
app.register_blueprint(products_bp, url_prefix="/api/products")
app.register_blueprint(suppliers_bp, url_prefix="/api/suppliers")
app.register_blueprint(warehouses_bp, url_prefix="/api/warehouses")
app.register_blueprint(inventory_bp, url_prefix="/api/inventory")
app.register_blueprint(purchase_orders_bp, url_prefix="/api/purchase-orders")
app.register_blueprint(sales_orders_bp, url_prefix="/api/sales-orders")
app.register_blueprint(shipments_bp, url_prefix="/api/shipments")
app.register_blueprint(query_lab_bp, url_prefix="/api/query-lab")


# 404 handler for API and web
@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Route not found"}), 404


# Global error handler
@app.errorhandler(500)
def server_error(e):
    return jsonify({"error": "Something went wrong on the server"}), 500


if __name__ == "__main__":
    test_connection()
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)

