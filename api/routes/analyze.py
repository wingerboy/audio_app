import logging
from flask import Blueprint, request, jsonify, current_app
from api.auth import login_required, get_current_user

logger = logging.getLogger(__name__)

bp = Blueprint('analyze_bp', __name__, url_prefix='/api/analyze') 