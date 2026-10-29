from flask import Blueprint, request, jsonify
from controllers import query_lab_controller as qc

query_lab_bp = Blueprint("query_lab", __name__)


@query_lab_bp.route("/catalog", methods=["GET"])
def catalog():
    body, status = qc.get_catalog()
    return jsonify(body), status


@query_lab_bp.route("/select/<int:query_id>", methods=["GET"])
def run_select(query_id):
    body, status = qc.run_select(query_id, request.args)
    return jsonify(body), status


@query_lab_bp.route("/dml/<dml_id>", methods=["POST"])
def run_dml(dml_id):
    data = request.get_json(force=True, silent=True) or {}
    body, status = qc.run_dml(dml_id, data)
    return jsonify(body), status


@query_lab_bp.route("/seed", methods=["POST"])
def seed():
    body, status = qc.load_demo_data()
    return jsonify(body), status
