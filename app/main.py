"""Flask application factory and route definitions."""

import logging
import uuid

from flask import Flask, jsonify, request
from sqlalchemy import create_engine

from app.db.connector import (
    VALID_DB_MODELS,
    build_connection_url,
    default_port,
    execute_query,
    get_schema,
)
from app.llm.converter import generate_sql, refine_query
from app.llm.session_manager import SessionManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Module-level singleton used when no custom manager is injected
_default_session_manager = SessionManager()

_REQUIRED_FIELDS = (
    "db_host",
    "db_user",
    "db_password",
    "db_name",
    "db_model",
    "query_natural",
)


def create_app(session_manager: SessionManager | None = None) -> Flask:
    """Create and return the Flask application.

    Parameters
    ----------
    session_manager:
        Optional ``SessionManager`` instance (useful for testing).
        Defaults to the module-level singleton.
    """
    app = Flask(__name__)
    sm = session_manager or _default_session_manager

    # ------------------------------------------------------------------ #
    # Routes                                                               #
    # ------------------------------------------------------------------ #

    @app.route("/query", methods=["POST"])
    def query():
        """Translate a natural-language query to SQL, execute it, return JSON.

        Request body (JSON)
        -------------------
        db_host        : str   – database host
        db_user        : str   – database user
        db_password    : str   – database password
        db_port        : int   – (optional) database port
        db_name        : str   – database / schema name
        db_model       : str   – engine: mysql | sqlsrv | mariadb | sybase |
                                          postgres | sqlite
        query_natural  : str   – question in natural language
        session_id     : str   – (optional) conversation session identifier

        Response body (JSON)
        --------------------
        columns   : list of {name, type}
        rows      : list of value lists
        session_id: str
        """
        data = request.get_json(silent=True)
        if not data:
            return jsonify({"error": "Request body must be valid JSON"}), 400

        missing = [f for f in _REQUIRED_FIELDS if not data.get(f)]
        if missing:
            return (
                jsonify({"error": f"Missing required fields: {', '.join(missing)}"}),
                400,
            )

        db_model = data["db_model"].lower()
        if db_model not in VALID_DB_MODELS:
            return (
                jsonify(
                    {
                        "error": (
                            f"Invalid db_model: {data['db_model']!r}. "
                            f"Must be one of: {', '.join(sorted(VALID_DB_MODELS))}."
                        )
                    }
                ),
                400,
            )

        session_id: str = data.get("session_id") or str(uuid.uuid4())

        # ---- Build engine & extract schema --------------------------------
        try:
            port = int(data.get("db_port") or default_port(db_model))
            conn_url = build_connection_url(
                db_model=db_model,
                db_host=data["db_host"],
                db_user=data["db_user"],
                db_password=data["db_password"],
                db_port=port,
                db_name=data["db_name"],
            )
            engine = create_engine(conn_url)
            schema = get_schema(engine)
        except Exception as exc:  # noqa: BLE001
            logger.error("Database connection error: %s", exc)
            return jsonify({"error": f"Database connection error: {exc}"}), 503

        # ---- LLM pipeline -------------------------------------------------
        try:
            refined = refine_query(
                session_id=session_id,
                natural_query=data["query_natural"],
                schema=schema,
                session_manager=sm,
            )
            sql = generate_sql(
                session_id=session_id,
                refined_query=refined,
                schema=schema,
                db_model=db_model,
                session_manager=sm,
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("LLM error: %s", exc)
            return jsonify({"error": f"LLM processing error: {exc}"}), 503

        # ---- Execute SQL --------------------------------------------------
        try:
            result = execute_query(engine, sql)
        except Exception as exc:  # noqa: BLE001
            logger.error("SQL execution error: %s", exc)
            return (
                jsonify({"error": f"SQL execution error: {exc}", "sql": sql}),
                500,
            )

        result["session_id"] = session_id
        return jsonify(result), 200

    # ------------------------------------------------------------------ #

    @app.route("/session/<session_id>", methods=["DELETE"])
    def delete_session(session_id: str):
        """Clear the conversation history for *session_id*."""
        removed = sm.clear_session(session_id)
        if removed:
            return jsonify({"message": f"Session {session_id!r} cleared"}), 200
        return jsonify({"error": f"Session {session_id!r} not found"}), 404

    # ------------------------------------------------------------------ #

    @app.route("/health", methods=["GET"])
    def health():
        """Liveness probe."""
        return jsonify({"status": "ok"}), 200

    return app
