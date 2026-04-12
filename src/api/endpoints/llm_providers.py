"""LLM Provider management API endpoints (Phase 15).

Provides CRUD for provider configurations, connection testing,
model listing, and per-task routing configuration.
"""
import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_db
from src.api.dependencies.common import get_settings
from src.auth.audit import log_action
from src.auth.dependencies import require_admin
from src.auth.models import User
from src.config.settings import Settings
from src.services.provider_config_service import ProviderConfigService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/llm-providers", tags=["LLM Providers"])


# --- Request/Response Models ---


class ProviderConfigRequest(BaseModel):
    enabled: bool = False
    data_locality: str = "local"
    api_key: Optional[str] = None
    endpoint: Optional[str] = None
    default_model: Optional[str] = None
    extra_config: Optional[dict] = None


class TaskRoutingRequest(BaseModel):
    task_type: str
    primary_provider: str
    primary_model: Optional[str] = None
    fallback_chain: Optional[list[dict]] = None


class ProviderTestResponse(BaseModel):
    provider: str
    healthy: bool
    message: str
    data_locality: str


class ProviderModelInfo(BaseModel):
    name: str
    size: Optional[str] = None
    modified_at: Optional[str] = None


# --- Dependency ---


def _get_config_service(settings: Settings = Depends(get_settings)) -> ProviderConfigService:
    return ProviderConfigService(settings)


# --- Provider Config Endpoints ---


@router.get("/", summary="List all provider configurations")
async def list_providers(
    db: AsyncSession = Depends(get_db),
    service: ProviderConfigService = Depends(_get_config_service),
) -> list[dict[str, Any]]:
    """List all configured LLM providers with masked API keys."""
    configs = await service.list_configs(db)

    # Augment with registry health info
    try:
        from src.llm.providers.registry import get_provider_registry
        registry = get_provider_registry()
        available = set(registry.list_available())
        allowed = set(registry.list_allowed())
    except Exception:
        available = set()
        allowed = set()

    for cfg in configs:
        name = cfg["provider_name"]
        cfg["registered"] = name in available
        cfg["allowed_by_security"] = name in allowed

    return configs


@router.get("/registry", summary="List providers from active registry")
async def list_registry_providers() -> dict[str, Any]:
    """List all providers currently registered in the runtime registry."""
    from src.llm.providers.registry import get_provider_registry
    registry = get_provider_registry()

    providers = []
    for name, provider in registry.get_all().items():
        providers.append({
            "name": name,
            "data_locality": provider.data_locality.value,
            "default_model": provider.default_model,
            "allowed": name in registry.list_allowed(),
        })

    return {
        "security_level": registry.security_level,
        "providers": providers,
    }


@router.get("/{provider_name}", summary="Get provider configuration")
async def get_provider(
    provider_name: str,
    db: AsyncSession = Depends(get_db),
    service: ProviderConfigService = Depends(_get_config_service),
) -> dict[str, Any]:
    config = await service.get_config(db, provider_name)
    if config is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Provider {provider_name!r} not configured",
        )
    return config


@router.put("/{provider_name}/config", summary="Create or update provider config")
async def upsert_provider(
    provider_name: str,
    body: ProviderConfigRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
    service: ProviderConfigService = Depends(_get_config_service),
) -> dict[str, Any]:
    config = await service.upsert_config(
        db,
        provider_name=provider_name,
        enabled=body.enabled,
        data_locality=body.data_locality,
        api_key=body.api_key,
        endpoint=body.endpoint,
        default_model=body.default_model,
        extra_config=body.extra_config,
    )
    await log_action(
        db, action="provider_config_update", resource_type="llm_provider",
        resource_id=provider_name, user_id=current_user.id,
        username=current_user.username,
        details={"enabled": body.enabled, "data_locality": body.data_locality,
                 "has_api_key": body.api_key is not None},
    )
    await db.commit()
    logger.info(f"Provider config updated: {provider_name}")
    return config


@router.delete("/{provider_name}/config", summary="Delete provider config")
async def delete_provider(
    provider_name: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
    service: ProviderConfigService = Depends(_get_config_service),
) -> dict[str, str]:
    deleted = await service.delete_config(db, provider_name)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Provider {provider_name!r} not configured",
        )
    await log_action(
        db, action="provider_config_delete", resource_type="llm_provider",
        resource_id=provider_name, user_id=current_user.id,
        username=current_user.username,
    )
    await db.commit()
    logger.info(f"Provider config deleted: {provider_name}")
    return {"status": "deleted", "provider": provider_name}


@router.post("/{provider_name}/test", summary="Test provider connectivity")
async def test_provider(
    provider_name: str,
    current_user: User = Depends(require_admin),
) -> ProviderTestResponse:
    """Test connectivity to a provider using a synthetic prompt.

    Uses a safe, non-data-bearing prompt so no schema or query data is sent.
    """
    from src.llm.providers.registry import (
        get_provider_registry,
        DataSecurityError,
        ProviderNotFoundError,
    )

    registry = get_provider_registry()

    try:
        provider = registry.get(provider_name)
    except ProviderNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Provider {provider_name!r} is not registered in the runtime",
        )
    except DataSecurityError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )

    health = await provider.health_check()
    return ProviderTestResponse(
        provider=provider_name,
        healthy=health.healthy,
        message=health.message or ("Connected" if health.healthy else "Unreachable"),
        data_locality=provider.data_locality.value,
    )


@router.get("/{provider_name}/models", summary="List available models")
async def list_provider_models(provider_name: str) -> list[ProviderModelInfo]:
    """List models available from a provider."""
    from src.llm.providers.registry import (
        get_provider_registry,
        DataSecurityError,
        ProviderNotFoundError,
    )

    registry = get_provider_registry()

    try:
        provider = registry.get(provider_name)
    except ProviderNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Provider {provider_name!r} is not registered",
        )
    except DataSecurityError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )

    try:
        models = await provider.list_models()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to list models from {provider_name}: {e}",
        )

    return [
        ProviderModelInfo(
            name=m.get("name", m.get("id", "unknown")),
            size=m.get("size"),
            modified_at=m.get("modified_at"),
        )
        for m in models
    ]


# --- Task Routing Endpoints ---


@router.get("/routing/tasks", summary="Get all task routing rules")
async def list_routing(
    db: AsyncSession = Depends(get_db),
    service: ProviderConfigService = Depends(_get_config_service),
) -> list[dict[str, Any]]:
    return await service.list_routing(db)


@router.put("/routing/tasks", summary="Create or update a task routing rule")
async def upsert_routing(
    body: TaskRoutingRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
    service: ProviderConfigService = Depends(_get_config_service),
) -> dict[str, Any]:
    route = await service.upsert_routing(
        db,
        task_type=body.task_type,
        primary_provider=body.primary_provider,
        primary_model=body.primary_model,
        fallback_chain=body.fallback_chain,
    )
    await log_action(
        db, action="routing_update", resource_type="llm_routing",
        resource_id=body.task_type, user_id=current_user.id,
        username=current_user.username,
        details={"primary_provider": body.primary_provider,
                 "primary_model": body.primary_model},
    )
    await db.commit()
    logger.info(f"Task routing updated: {body.task_type} -> {body.primary_provider}")
    return route


@router.delete("/routing/tasks/{task_type}", summary="Delete a task routing rule")
async def delete_routing(
    task_type: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
    service: ProviderConfigService = Depends(_get_config_service),
) -> dict[str, str]:
    deleted = await service.delete_routing(db, task_type)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No routing rule for task {task_type!r}",
        )
    await log_action(
        db, action="routing_delete", resource_type="llm_routing",
        resource_id=task_type, user_id=current_user.id,
        username=current_user.username,
    )
    await db.commit()
    return {"status": "deleted", "task_type": task_type}


# --- Health Check ---


@router.get("/health/all", summary="Health check all registered providers")
async def health_check_all() -> list[dict[str, Any]]:
    """Run health checks on all registered providers."""
    from src.llm.providers.registry import get_provider_registry

    registry = get_provider_registry()
    results = await registry.health_check_all()
    return [
        {
            "provider": r.provider,
            "healthy": r.healthy,
            "data_locality": r.data_locality,
            "message": r.message,
        }
        for r in results
    ]
