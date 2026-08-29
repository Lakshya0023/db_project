from flask import Blueprint, request, jsonify
from controllers import purchase_orders_controller as poc

purchase_orders_bp = Blueprint("purchase_orders", __name__)


@purchase_orders_bp.route("", methods=["GET"])
def get_all():
    body, status = poc.get_all_purchase_orders()
    return jsonify(body), status


@purchase_orders_bp.route("/<int:po_id>", methods=["GET"])
def get_one(po_id):
    body, status = poc.get_purchase_order_by_id(po_id)
    return jsonify(body), status


@purchase_orders_bp.route("", methods=["POST"])
def create():
    data = request.get_json(force=True, silent=True) or {}
    body, status = poc.create_purchase_order(data)
    return jsonify(body), status


@purchase_orders_bp.route("/<int:po_id>", methods=["PUT"])
def update_status(po_id):
    data = request.get_json(force=True, silent=True) or {}
    body, status = poc.update_purchase_order_status(po_id, data)
    return jsonify(body), status


@purchase_orders_bp.route("/<int:po_id>", methods=["DELETE"])
def delete(po_id):
    body, status = poc.delete_purchase_order(po_id)
    return jsonify(body), status


# Business logic endpoint: mark PO received + add stock into inventory (transactional)
@purchase_orders_bp.route("/<int:po_id>/receive", methods=["POST"])
def receive(po_id):
    body, status = poc.receive_purchase_order(po_id)
    return jsonify(body), status
