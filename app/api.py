"""FastAPI application factory and route definitions."""

import logging
import os
import uuid
from typing import Any, Literal

from fastapi import APIRouter, FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import create_engine

from app.db.connector import (
    VALID_DB_MODELS,
    build_connection_url,
    default_port,
    execute_query,
    get_schema,
)
from app.db.sql_guard import SQLValidationError, validate_sql_query
from app.llm.converter import generate_sql, refine_query
from app.llm.session_manager import SessionManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_default_session_manager = SessionManager()

DEFAULT_MAX_ROWS = int(os.getenv("NL2SQL_MAX_ROWS", "1000"))
DEFAULT_QUERY_TIMEOUT_MS = int(os.getenv("NL2SQL_QUERY_TIMEOUT_MS", "15000"))


class NL2SQLQueryRequest(BaseModel):
    """Request schema for NL→SQL execution."""

    host: str | None = None
    usuario: str
    contraseña: str
    puerto: int | None = None
    nombre_bd: str
    motor_bd: Literal["mysql", "sqlsrv", "mariadb", "sybase", "postgres", "sqlite"]
    consulta_nl: str
    session_id: str | None = None

    model_config = ConfigDict(
        populate_by_name=True,
        extra="forbid",
        json_schema_extra={"example": {
            "host": "localhost",
            "usuario": "user",
            "contraseña": "secret",
            "puerto": 5432,
            "nombre_bd": "testdb",
            "motor_bd": "postgres",
            "consulta_nl": "Muestra todos los usuarios",
            "session_id": "my-session-42",
        }},
    )


class QueryColumn(BaseModel):
    name: str
    type: str


class NL2SQLQueryResponse(BaseModel):
    columns: list[QueryColumn]
    rows: list[list[Any]]
    session_id: str


class DeleteSessionResponse(BaseModel):
    message: str


class ErrorResponse(BaseModel):
    error: str
    sql: str | None = None


def _build_nl2sql_router(session_manager: SessionManager) -> APIRouter:
    router = APIRouter(prefix="/nl2sql", tags=["nl2sql"])

    @router.post(
        "/query",
        response_model=NL2SQLQueryResponse,
        responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}, 503: {"model": ErrorResponse}},
    )
    def nl2sql_query(payload: NL2SQLQueryRequest):
        db_model = payload.motor_bd.lower()
        if db_model not in VALID_DB_MODELS:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": (
                        f"Invalid motor_bd: {payload.motor_bd!r}. "
                        f"Must be one of: {', '.join(sorted(VALID_DB_MODELS))}."
                    )
                },
            )

        session_id = payload.session_id or str(uuid.uuid4())

        try:
            port = payload.puerto or default_port(db_model)
            conn_url = build_connection_url(
                db_model=db_model,
                db_host=payload.host or "",
                db_user=payload.usuario,
                db_password=payload.contraseña,
                db_port=port,
                db_name=payload.nombre_bd,
            )
            engine = create_engine(conn_url)
            schema = get_schema(engine)
        except Exception as exc:  # noqa: BLE001
            logger.error("Database connection error: %s", exc)
            raise HTTPException(status_code=503, detail={"error": f"Database connection error: {exc}"}) from exc

        try:
            refined = refine_query(
                session_id=session_id,
                natural_query=payload.consulta_nl,
                schema=schema,
                session_manager=session_manager,
            )
            sql = generate_sql(
                session_id=session_id,
                refined_query=refined,
                schema=schema,
                db_model=db_model,
                session_manager=session_manager,
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("LLM error: %s", exc)
            raise HTTPException(status_code=503, detail={"error": f"LLM processing error: {exc}"}) from exc

        try:
            validate_sql_query(sql)
            result = execute_query(
                engine,
                sql,
                db_model=db_model,
                max_rows=DEFAULT_MAX_ROWS,
                timeout_ms=DEFAULT_QUERY_TIMEOUT_MS,
            )
        except SQLValidationError as exc:
            logger.warning("SQL policy validation error: %s", exc)
            raise HTTPException(
                status_code=400,
                detail={"error": str(exc), "sql": sql},
            ) from exc
        except Exception as exc:  # noqa: BLE001
            logger.error("SQL execution error: %s", exc)
            raise HTTPException(
                status_code=500,
                detail={"error": f"SQL execution error: {exc}", "sql": sql},
            ) from exc

        result["session_id"] = session_id
        return result

    return router


def _build_core_router(session_manager: SessionManager) -> APIRouter:
    router = APIRouter(tags=["core"])

    @router.get("/health")
    def health():
        return {"status": "ok"}

    @router.delete(
        "/session/{session_id}",
        response_model=DeleteSessionResponse,
        responses={404: {"model": ErrorResponse}},
    )
    def delete_session(session_id: str):
        removed = session_manager.clear_session(session_id)
        if removed:
            return {"message": f"Session {session_id!r} cleared"}
        raise HTTPException(status_code=404, detail={"error": f"Session {session_id!r} not found"})

    return router


def create_app(session_manager: SessionManager | None = None) -> FastAPI:
    """Create and return the FastAPI application."""
    sm = session_manager or _default_session_manager
    app = FastAPI(title="Texto2Sql API")
    app.include_router(_build_nl2sql_router(sm))
    app.include_router(_build_core_router(sm))
    return app


app = create_app()
