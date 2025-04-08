import os
import json
import logging
from flask import Blueprint, request, jsonify, current_app
from api.auth import login_required, get_current_user
from src.utils.logging_config import LoggingConfig

# 设置日志
logger = LoggingConfig.setup_logging(log_level=logging.INFO)

bp = Blueprint('analyze_bp', __name__, url_prefix='/api/analyze') 