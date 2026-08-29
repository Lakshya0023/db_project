from flask import Blueprint, request, jsonify
from controllers import warehouses_controller as wc

warehouses_bp = Blueprint("warehouses", __name__)


@warehouses_bp.route("", methods=["GET"])
def get_all():
    body, status = wc.get_all_warehouses()
    return jsonify(body), status


@warehouses_bp.route("/<int:warehouse_id>", methods=["GET"])
def get_one(warehouse_id):
    body, status = wc.get_warehouse_by_id(warehouse_id)
    return jsonify(body), status


@warehouses_bp.route("/<int:warehouse_id>/stock", methods=["GET"])
def get_stock(warehouse_id):
    body, status = wc.get_warehouse_stock(warehouse_id)
    return jsonify(body), status


@warehouses_bp.route("", methods=["POST"])
def create():
    data = request.get_json(force=True, silent=True) or {}
    body, status = wc.create_warehouse(data)
    return jsonify(body), status


@warehouses_bp.route("/<int:warehouse_id>", methods=["PUT"])
def update(warehouse_id):
    data = request.get_json(force=True, silent=True) or {}
    body, status = wc.update_warehouse(warehouse_id, data)
    return jsonify(body), status


@warehouses_bp.route("/<int:warehouse_id>", methods=["DELETE"])
def delete(warehouse_id):
    body, status = wc.delete_warehouse(warehouse_id)
    return jsonify(body), status
