"""Runtime capability diagnostics routes."""

from __future__ import annotations

from flask import Blueprint, jsonify, request

from app.services.runtime_capability_service import build_runtime_capabilities


runtime_bp = Blueprint("runtime", __name__)


def _bool_arg(name: str, default: bool = True) -> bool:
    value = request.args.get(name)
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


@runtime_bp.route("/capabilities", methods=["GET"])
def runtime_capabilities():
    """Return safe diagnostics for the actual running backend process."""
    return jsonify(build_runtime_capabilities(run_solver_probe=_bool_arg("solver_probe", True)))
