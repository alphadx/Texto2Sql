"""FastAPI application factory and route definitions."""

import logging
import os
import time
import uuid
from typing import Any, Literal

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict
from sqlalchemy import create_engine

from app.audit.logger import build_audit_logger_from_env
from app.db.connector import (
    VALID_DB_MODELS,
    build_connection_url,
    default_port,
    execute_query,
    get_schema,
)
from app.db.sql_guard import SQLValidationError, validate_sql_query
from app.llm.converter import generate_sql, refine_query
from app.llm.providers import LLMProviderError
from app.llm.settings import (
    load_llm_startup_settings_from_env,
    validate_llm_startup_settings,
)
from app.llm.session_manager import SessionManager, build_session_manager_from_env
from app.observability import MetricsRegistry
from app.security import (
    AuthSettings,
    decode_access_token,
    load_auth_settings_from_env,
    require_admin_access,
    require_scopes,
    validate_security_settings,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DEFAULT_MAX_ROWS = int(os.getenv("MAX_RESULT_ROWS", "1000"))
DEFAULT_QUERY_TIMEOUT_MS = int(os.getenv("QUERY_TIMEOUT_MS", "900000"))

_default_session_manager = build_session_manager_from_env()
_audit_logger = build_audit_logger_from_env()
_metrics = MetricsRegistry()


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
    llm_provider: str | None = None
    llm_model: str | None = None
    llm_api_key: str | None = None
    llm_base_url: str | None = None

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
            "llm_provider": "openai",
            "llm_model": "gpt-4.1-mini",
            "llm_api_key": "sk-demo",
            "llm_base_url": "https://api.openai.com/v1",
        }},
    )


class QueryColumn(BaseModel):
    name: str
    type: str


class NL2SQLQueryResponse(BaseModel):
    columns: list[QueryColumn]
    rows: list[list[Any]]
    session_id: str
    sql: str | None = None
    texto_formal: str | None = None


class DeleteSessionResponse(BaseModel):
    message: str


class ErrorResponse(BaseModel):
    error: str
    sql: str | None = None




def _install_auth_context_middleware(app: FastAPI) -> None:
    @app.middleware("http")
    async def auth_context_middleware(request: Request, call_next):
        request.state.auth_context = None
        settings: AuthSettings = request.app.state.auth_settings
        if settings.required:
            authorization = request.headers.get("authorization", "")
            if authorization.lower().startswith("bearer "):
                token = authorization[7:].strip()
                try:
                    request.state.auth_context = decode_access_token(token, settings)
                except Exception:  # noqa: BLE001
                    request.state.auth_context = None
        return await call_next(request)


def _build_nl2sql_router(session_manager: SessionManager) -> APIRouter:
    router = APIRouter(prefix="/nl2sql", tags=["nl2sql"])

    @router.post(
        "/query",
        response_model=NL2SQLQueryResponse,
        responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}, 503: {"model": ErrorResponse}},
    )
    def nl2sql_query(
        payload: NL2SQLQueryRequest,
        _auth=Depends(require_scopes("query:execute")),
    ):
        request_start = time.perf_counter()
        stage_start = request_start
        schema_ms = 0.0
        llm_ms = 0.0
        sql_ms = 0.0
        status_code = 200
        error_type = None
        error_message = None
        sql = None
        refined = None

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
        db_model = payload.motor_bd.lower()

        try:
            if db_model not in VALID_DB_MODELS:
                error_type = "invalid_db_model"
                error_message = (
                    f"Invalid motor_bd: {payload.motor_bd!r}. "
                    f"Must be one of: {', '.join(sorted(VALID_DB_MODELS))}."
                )
                status_code = 400
                raise HTTPException(status_code=400, detail={"error": error_message})

            try:
                raw_port = payload.puerto
                if raw_port in (None, ""):
                    port = default_port(db_model)
                else:
                    try:
                        port = int(raw_port)
                    except (TypeError, ValueError) as exc:
                        raise HTTPException(status_code=400, detail={"error": f"Invalid puerto: {raw_port!r}"}) from exc

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
                error_type = "db_connection_error"
                error_message = str(exc)
                status_code = 503
                raise HTTPException(status_code=503, detail={"error": f"Database connection error: {exc}"}) from exc
            finally:
                schema_ms = (time.perf_counter() - stage_start) * 1000
                stage_start = time.perf_counter()

            llm_options = {
                "provider": payload.llm_provider,
                "model": payload.llm_model,
                "api_key": payload.llm_api_key,
                "base_url": payload.llm_base_url,
            }

            try:
                refined = refine_query(
                    session_id=session_id,
                    natural_query=payload.consulta_nl,
                    schema=schema,
                    session_manager=session_manager,
                    llm_options=llm_options,
                )
                sql = generate_sql(
                    session_id=session_id,
                    refined_query=refined,
                    schema=schema,
                    db_model=db_model,
                    session_manager=session_manager,
                    llm_options=llm_options,
                )
            except LLMProviderError as exc:
                logger.error("LLM provider error: %s", exc)
                provider = exc.provider or "unknown"
                if "circuit breaker is open" in str(exc).lower():
                    error_type = f"llm_circuit_open_{provider}"
                else:
                    error_type = f"llm_provider_error_{provider}"
                error_message = str(exc)
                status_code = exc.status_code or 503
                raise HTTPException(
                    status_code=status_code,
                    detail={
                        "error": f"LLM provider error ({provider}): {exc.message}",
                        "provider": provider,
                        "retryable": exc.retryable,
                    },
                ) from exc
            except ValueError as exc:
                logger.error("LLM config validation error: %s", exc)
                error_type = "llm_config_validation_error"
                error_message = str(exc)
                status_code = 400
                raise HTTPException(
                    status_code=400,
                    detail={"error": f"LLM config validation error: {exc}"},
                ) from exc
            except Exception as exc:  # noqa: BLE001
                logger.error("LLM error: %s", exc)
                error_type = "llm_processing_error"
                error_message = str(exc)
                status_code = 503
                raise HTTPException(status_code=503, detail={"error": f"LLM processing error: {exc}"}) from exc
            finally:
                llm_ms = (time.perf_counter() - stage_start) * 1000
                stage_start = time.perf_counter()

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
                error_type = "sql_validation_error"
                error_message = str(exc)
                status_code = 400
                raise HTTPException(
                    status_code=400,
                    detail={"error": str(exc), "sql": sql},
                ) from exc
            except Exception as exc:  # noqa: BLE001
                logger.error("SQL execution error: %s", exc)
                error_type = "sql_execution_error"
                error_message = str(exc)
                status_code = 500
                raise HTTPException(
                    status_code=500,
                    detail={"error": f"SQL execution error: {exc}", "sql": sql},
                ) from exc
            finally:
                sql_ms = (time.perf_counter() - stage_start) * 1000

            result["session_id"] = session_id
            result["sql"] = sql
            result["texto_formal"] = refined
            return result
        finally:
            total_ms = (time.perf_counter() - request_start) * 1000
            _metrics.observe_request(total_ms, error_type=error_type)
            _audit_logger.persist({
                "event": "nl2sql_request",
                "session_id": session_id,
                "engine": db_model,
                "status_code": status_code,
                "durations_ms": {
                    "total": round(total_ms, 3),
                    "schema": round(schema_ms, 3),
                    "llm": round(llm_ms, 3),
                    "sql": round(sql_ms, 3),
                },
                "sql": sql,
                "error_type": error_type,
                "error_message": error_message,
            })

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
    def delete_session(
        session_id: str,
        _auth=Depends(require_admin_access(admin_scopes={"audit:admin"}, admin_roles={"admin"})),
    ):
        removed = session_manager.clear_session(session_id)
        if removed:
            return {"message": f"Session {session_id!r} cleared"}
        raise HTTPException(status_code=404, detail={"error": f"Session {session_id!r} not found"})

    @router.get("/metrics")
    def metrics():
        payload = _metrics.to_prometheus_text()
        return Response(content=payload, media_type="text/plain; version=0.0.4")

    return router


def create_app(session_manager: SessionManager | None = None) -> FastAPI:
    """Create and return the FastAPI application."""
    sm = session_manager or _default_session_manager
    auth_settings = load_auth_settings_from_env()
    validate_security_settings(auth_settings)
    validate_llm_startup_settings(load_llm_startup_settings_from_env())

    app = FastAPI(title="Texto2Sql API")
    app.state.auth_settings = auth_settings
    _install_auth_context_middleware(app)
    app.include_router(_build_nl2sql_router(sm))
    app.include_router(_build_core_router(sm))
    return app


app = create_app()
