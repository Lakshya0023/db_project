from flask import Blueprint, request, jsonify
from controllers import products_controller as pc

products_bp = Blueprint("products", __name__)


# IMPORTANT: specific routes must be registered before the dynamic '<id>' route
@products_bp.route("/reports/low-stock", methods=["GET"])
def low_stock():
    body, status = pc.get_low_stock_products()
    return jsonify(body), status


@products_bp.route("", methods=["GET"])
def get_all():
    body, status = pc.get_all_products()
    return jsonify(body), status


@products_bp.route("/<int:product_id>", methods=["GET"])
def get_one(product_id):
    body, status = pc.get_product_by_id(product_id)
    return jsonify(body), status


@products_bp.route("", methods=["POST"])
def create():
    data = request.get_json(force=True, silent=True) or {}
    body, status = pc.create_product(data)
    return jsonify(body), status


@products_bp.route("/<int:product_id>", methods=["PUT"])
def update(product_id):
    data = request.get_json(force=True, silent=True) or {}
    body, status = pc.update_product(product_id, data)
    return jsonify(body), status


@products_bp.route("/<int:product_id>", methods=["DELETE"])
def delete(product_id):
    body, status = pc.delete_product(product_id)
    return jsonify(body), status
