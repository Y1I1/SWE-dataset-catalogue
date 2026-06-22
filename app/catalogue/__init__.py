from flask import Blueprint

catalogue_bp = Blueprint("catalogue", __name__, url_prefix="/catalogue")

from app.catalogue import routes  # noqa: E402, F401
