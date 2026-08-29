from flask import Blueprint, request, jsonify
from controllers import inventory_controller as ic

inventory_bp = Blueprint("inventory", __name__)


@inventory_bp.route("", methods=["GET"])
def get_all():
    body, status = ic.get_all_inventory()
    return jsonify(body), status


@inventory_bp.route("/<int:inventory_id>", methods=["GET"])
def get_one(inventory_id):
    body, status = ic.get_inventory_by_id(inventory_id)
    return jsonify(body), status


@inventory_bp.route("", methods=["POST"])
def create():
    data = request.get_json(force=True, silent=True) or {}
    body, status = ic.create_inventory_record(data)
    return jsonify(body), status


@inventory_bp.route("/<int:inventory_id>", methods=["DELETE"])
def delete(inventory_id):
    body, status = ic.delete_inventory_record(inventory_id)
    return jsonify(body), status


# Business logic endpoint: safe, transaction-locked stock increment/decrement
@inventory_bp.route("/adjust", methods=["PATCH"])
def adjust():
    data = request.get_json(force=True, silent=True) or {}
    body, status = ic.adjust_stock(data)
    return jsonify(body), status
