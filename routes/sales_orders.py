from flask import Blueprint, request, jsonify
from controllers import sales_orders_controller as soc

sales_orders_bp = Blueprint("sales_orders", __name__)


@sales_orders_bp.route("", methods=["GET"])
def get_all():
    body, status = soc.get_all_sales_orders()
    return jsonify(body), status


@sales_orders_bp.route("/<int:so_id>", methods=["GET"])
def get_one(so_id):
    body, status = soc.get_sales_order_by_id(so_id)
    return jsonify(body), status


@sales_orders_bp.route("", methods=["POST"])
def create():
    data = request.get_json(force=True, silent=True) or {}
    body, status = soc.create_sales_order(data)
    return jsonify(body), status


@sales_orders_bp.route("/<int:so_id>", methods=["DELETE"])
def delete(so_id):
    body, status = soc.delete_sales_order(so_id)
    return jsonify(body), status


@sales_orders_bp.route("/<int:so_id>/cancel", methods=["POST"])
def cancel(so_id):
    body, status = soc.cancel_sales_order(so_id)
    return jsonify(body), status


# Business logic endpoint: check stock, decrement inventory, create shipment (transactional)
@sales_orders_bp.route("/<int:so_id>/fulfill", methods=["POST"])
def fulfill(so_id):
    body, status = soc.fulfill_sales_order(so_id)
    return jsonify(body), status
