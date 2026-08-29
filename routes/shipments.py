from flask import Blueprint, request, jsonify
from controllers import shipments_controller as shc

shipments_bp = Blueprint("shipments", __name__)


@shipments_bp.route("", methods=["GET"])
def get_all():
    body, status = shc.get_all_shipments()
    return jsonify(body), status


@shipments_bp.route("/<int:shipment_id>", methods=["GET"])
def get_one(shipment_id):
    body, status = shc.get_shipment_by_id(shipment_id)
    return jsonify(body), status


@shipments_bp.route("/<int:shipment_id>/ship", methods=["POST"])
def ship(shipment_id):
    data = request.get_json(force=True, silent=True) or {}
    body, status = shc.mark_shipped(shipment_id, data)
    return jsonify(body), status


@shipments_bp.route("/<int:shipment_id>/deliver", methods=["POST"])
def deliver(shipment_id):
    body, status = shc.mark_delivered(shipment_id)
    return jsonify(body), status
