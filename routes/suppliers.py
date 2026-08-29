from flask import Blueprint, request, jsonify
from controllers import suppliers_controller as sc

suppliers_bp = Blueprint("suppliers", __name__)


@suppliers_bp.route("", methods=["GET"])
def get_all():
    body, status = sc.get_all_suppliers()
    return jsonify(body), status


@suppliers_bp.route("/<int:supplier_id>", methods=["GET"])
def get_one(supplier_id):
    body, status = sc.get_supplier_by_id(supplier_id)
    return jsonify(body), status


@suppliers_bp.route("/<int:supplier_id>/products", methods=["GET"])
def get_products(supplier_id):
    body, status = sc.get_supplier_products(supplier_id)
    return jsonify(body), status


@suppliers_bp.route("", methods=["POST"])
def create():
    data = request.get_json(force=True, silent=True) or {}
    body, status = sc.create_supplier(data)
    return jsonify(body), status


@suppliers_bp.route("/<int:supplier_id>", methods=["PUT"])
def update(supplier_id):
    data = request.get_json(force=True, silent=True) or {}
    body, status = sc.update_supplier(supplier_id, data)
    return jsonify(body), status


@suppliers_bp.route("/<int:supplier_id>", methods=["DELETE"])
def delete(supplier_id):
    body, status = sc.delete_supplier(supplier_id)
    return jsonify(body), status
