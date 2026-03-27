"""FastAPI application factory and route definitions."""

import logging
import uuid
from typing import Any, Literal

from fastapi import APIRouter, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict
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

_default_session_manager = SessionManager()


class NL2SQLQueryRequest(BaseModel):
    """Request schema for NL→SQL execution (plan.md field names)."""

    host: str | None = None
    usuario: str
    contraseña: str
    puerto: int | None = None
    nombre_bd: str
    motor_bd: Literal["mysql", "sqlsrv", "mariadb", "sybase", "postgres", "sqlite"]
    consulta_nl: str
    session_id: str | None = None

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "host": "localhost",
                "usuario": "user",
                "contraseña": "secret",
                "puerto": 5432,
                "nombre_bd": "testdb",
                "motor_bd": "postgres",
                "consulta_nl": "Muestra todos los usuarios",
                "session_id": "my-session-42",
            }
        },
    )


class LegacyQueryRequest(BaseModel):
    """Legacy request schema kept for backward compatibility (/query)."""

    db_host: str | None = None
    db_user: str
    db_password: str
    db_port: int | None = None
    db_name: str
    db_model: Literal["mysql", "sqlsrv", "mariadb", "sybase", "postgres", "sqlite"]
    query_natural: str
    session_id: str | None = None

    model_config = ConfigDict(extra="forbid")


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
    details: list[dict[str, Any]] | None = None


def _run_query(
    *,
    session_manager: SessionManager,
    db_host: str | None,
    db_user: str,
    db_password: str,
    db_port: int | None,
    db_name: str,
    db_model: str,
    natural_query: str,
    session_id: str | None,
) -> dict[str, Any]:
    if db_model not in VALID_DB_MODELS:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Invalid db_model: {db_model!r}. "
                f"Must be one of: {', '.join(sorted(VALID_DB_MODELS))}."
            ),
        )

    if db_model != "sqlite" and not db_host:
        raise HTTPException(
            status_code=400,
            detail="Field 'host'/'db_host' is required when motor_bd/db_model is not sqlite.",
        )

    sid = session_id or str(uuid.uuid4())

    try:
        port = db_port or default_port(db_model)
        conn_url = build_connection_url(
            db_model=db_model,
            db_host=db_host or "",
            db_user=db_user,
            db_password=db_password,
            db_port=port,
            db_name=db_name,
        )
        engine = create_engine(conn_url)
        schema = get_schema(engine)
    except Exception as exc:  # noqa: BLE001
        logger.error("Database connection error: %s", exc)
        raise HTTPException(status_code=503, detail=f"Database connection error: {exc}") from exc

    try:
        refined = refine_query(
            session_id=sid,
            natural_query=natural_query,
            schema=schema,
            session_manager=session_manager,
        )
        sql = generate_sql(
            session_id=sid,
            refined_query=refined,
            schema=schema,
            db_model=db_model,
            session_manager=session_manager,
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("LLM error: %s", exc)
        raise HTTPException(status_code=503, detail=f"LLM processing error: {exc}") from exc

    try:
        result = execute_query(engine, sql)
    except Exception as exc:  # noqa: BLE001
        logger.error("SQL execution error: %s", exc)
        raise HTTPException(
            status_code=500,
            detail={"error": f"SQL execution error: {exc}", "sql": sql},
        ) from exc

    result["session_id"] = sid
    return result


def _build_nl2sql_router(session_manager: SessionManager) -> APIRouter:
    router = APIRouter(tags=["nl2sql"])

    @router.post(
        "/nl2sql/query",
        response_model=NL2SQLQueryResponse,
        responses={400: {"model": ErrorResponse}, 422: {"model": ErrorResponse}, 500: {"model": ErrorResponse}, 503: {"model": ErrorResponse}},
    )
    def nl2sql_query(payload: NL2SQLQueryRequest):
        return _run_query(
            session_manager=session_manager,
            db_host=payload.host,
            db_user=payload.usuario,
            db_password=payload.contraseña,
            db_port=payload.puerto,
            db_name=payload.nombre_bd,
            db_model=payload.motor_bd.lower(),
            natural_query=payload.consulta_nl,
            session_id=payload.session_id,
        )

    @router.post(
        "/query",
        response_model=NL2SQLQueryResponse,
        deprecated=True,
        responses={400: {"model": ErrorResponse}, 422: {"model": ErrorResponse}, 500: {"model": ErrorResponse}, 503: {"model": ErrorResponse}},
    )
    def legacy_query(payload: LegacyQueryRequest):
        return _run_query(
            session_manager=session_manager,
            db_host=payload.db_host,
            db_user=payload.db_user,
            db_password=payload.db_password,
            db_port=payload.db_port,
            db_name=payload.db_name,
            db_model=payload.db_model.lower(),
            natural_query=payload.query_natural,
            session_id=payload.session_id,
        )

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
        raise HTTPException(status_code=404, detail=f"Session {session_id!r} not found")

    return router


def create_app(session_manager: SessionManager | None = None) -> FastAPI:
    """Create and return the FastAPI application."""
    sm = session_manager or _default_session_manager
    app = FastAPI(title="Texto2Sql API")

    @app.exception_handler(HTTPException)
    async def _http_exception_handler(_: Request, exc: HTTPException):
        if isinstance(exc.detail, dict):
            payload = exc.detail
            if "error" not in payload:
                payload = {"error": str(exc.detail)}
        else:
            payload = {"error": str(exc.detail)}
        return JSONResponse(status_code=exc.status_code, content=payload)

    @app.exception_handler(RequestValidationError)
    async def _validation_exception_handler(_: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content={"error": "Validation error", "details": exc.errors()},
        )

    app.include_router(_build_nl2sql_router(sm))
    app.include_router(_build_core_router(sm))
    return app


app = create_app()
