"""
Connection Pool Management API Endpoints

Provides endpoints for monitoring and managing connection pools:
- GET /api/pools/stats - Overall pool statistics
- GET /api/pools/stats/{connection_id} - Per-connection statistics
- DELETE /api/pools/{connection_id} - Manual pool eviction
"""

import logging
from typing import Dict, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from src.core.connection_pool_manager import get_pool_manager_async, ConnectionPoolManager
from src.config.settings import Settings

logger = logging.getLogger(__name__)
router = APIRouter(tags=["pools"])


# Response models
class PoolStatsResponse(BaseModel):
    """Response model for pool statistics"""
    total_pools: int
    global_metrics: Dict
    pools: list
    pooling_enabled: bool


class PoolEvictionResponse(BaseModel):
    """Response model for pool eviction"""
    success: bool
    message: str
    pools_evicted: int


async def get_pool_manager_dependency() -> Optional[ConnectionPoolManager]:
    """Dependency to get pool manager instance"""
    settings = Settings()
    if not settings.ENABLE_CONNECTION_POOLING:
        return None
    return await get_pool_manager_async(settings)


@router.get("/pools/stats", response_model=PoolStatsResponse)
async def get_pool_stats(
    pool_manager: Optional[ConnectionPoolManager] = Depends(get_pool_manager_dependency)
):
    """
    Get overall connection pool statistics

    Returns:
        - Total number of pools
        - Global metrics (total active/idle connections, avg utilization)
        - Per-pool metrics
    """
    if pool_manager is None:
        return PoolStatsResponse(
            total_pools=0,
            global_metrics={
                "total_active_connections": 0,
                "total_idle_connections": 0,
                "avg_utilization_percent": 0.0,
            },
            pools=[],
            pooling_enabled=False,
        )

    try:
        metrics = pool_manager.get_all_metrics()
        return PoolStatsResponse(
            total_pools=metrics["total_pools"],
            global_metrics=metrics["global_metrics"],
            pools=metrics["pools"],
            pooling_enabled=True,
        )
    except Exception as e:
        logger.error(f"Error getting pool stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get pool stats: {str(e)}")


@router.get("/pools/stats/{connection_id}")
async def get_connection_pool_stats(
    connection_id: int,
    pool_manager: Optional[ConnectionPoolManager] = Depends(get_pool_manager_dependency)
):
    """
    Get statistics for a specific database connection's pools

    Args:
        connection_id: Database connection ID

    Returns:
        Pool metrics for the specified connection (all database types)
    """
    if pool_manager is None:
        raise HTTPException(
            status_code=503,
            detail="Connection pooling is disabled. Enable ENABLE_CONNECTION_POOLING to use this feature."
        )

    try:
        all_metrics = pool_manager.get_all_metrics()

        # Filter pools for this connection
        connection_pools = [
            pool for pool in all_metrics["pools"]
            if pool["connection_id"] == connection_id
        ]

        if not connection_pools:
            raise HTTPException(
                status_code=404,
                detail=f"No pools found for connection {connection_id}"
            )

        return {
            "connection_id": connection_id,
            "pools": connection_pools,
            "total_pools": len(connection_pools),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting stats for connection {connection_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get connection pool stats: {str(e)}")


@router.delete("/pools/{connection_id}", response_model=PoolEvictionResponse)
async def evict_connection_pools(
    connection_id: int,
    database_type: Optional[str] = None,
    pool_manager: Optional[ConnectionPoolManager] = Depends(get_pool_manager_dependency)
):
    """
    Manually evict pool(s) for a database connection

    This forces pool recreation on next use. Useful for:
    - Testing pool lifecycle
    - Recovering from connection issues
    - Applying configuration changes

    Args:
        connection_id: Database connection ID
        database_type: Optional database type filter (postgresql, mysql, sqlite, duckdb)

    Returns:
        Success status and number of pools evicted
    """
    if pool_manager is None:
        raise HTTPException(
            status_code=503,
            detail="Connection pooling is disabled. Enable ENABLE_CONNECTION_POOLING to use this feature."
        )

    try:
        # Get current pool count for this connection
        all_metrics = pool_manager.get_all_metrics()
        pools_before = len([
            pool for pool in all_metrics["pools"]
            if pool["connection_id"] == connection_id and (
                database_type is None or pool["database_type"] == database_type
            )
        ])

        if pools_before == 0:
            return PoolEvictionResponse(
                success=True,
                message=f"No pools found for connection {connection_id}",
                pools_evicted=0,
            )

        # Evict pools
        await pool_manager.evict_pool(connection_id, database_type)

        # Build response message
        if database_type:
            message = f"Evicted {database_type} pool for connection {connection_id}"
        else:
            message = f"Evicted all pools for connection {connection_id}"

        logger.info(message)

        return PoolEvictionResponse(
            success=True,
            message=message,
            pools_evicted=pools_before,
        )

    except Exception as e:
        logger.error(f"Error evicting pools for connection {connection_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to evict pools: {str(e)}")


@router.get("/pools/health")
async def get_pool_health(
    pool_manager: Optional[ConnectionPoolManager] = Depends(get_pool_manager_dependency)
):
    """
    Get connection pool health status

    Returns:
        Overall health status and any warnings/issues
    """
    if pool_manager is None:
        return {
            "pooling_enabled": False,
            "status": "disabled",
            "message": "Connection pooling is disabled",
        }

    try:
        metrics = pool_manager.get_all_metrics()

        # Check for health issues
        warnings = []
        unhealthy_pools = []
        high_utilization_pools = []

        for pool in metrics["pools"]:
            pool_metrics = pool["metrics"]

            # Check health status
            if pool_metrics["health_status"] == "unhealthy":
                unhealthy_pools.append({
                    "connection_id": pool["connection_id"],
                    "database_type": pool["database_type"],
                    "failed_checkouts": pool_metrics["failed_checkouts"],
                })

            # Check utilization
            if pool_metrics["utilization_percent"] > 80:
                high_utilization_pools.append({
                    "connection_id": pool["connection_id"],
                    "database_type": pool["database_type"],
                    "utilization": pool_metrics["utilization_percent"],
                })

        # Build warnings
        if unhealthy_pools:
            warnings.append(f"{len(unhealthy_pools)} unhealthy pool(s)")
        if high_utilization_pools:
            warnings.append(f"{len(high_utilization_pools)} pool(s) with high utilization (>80%)")

        # Determine overall status
        if unhealthy_pools:
            status = "unhealthy"
        elif high_utilization_pools:
            status = "degraded"
        else:
            status = "healthy"

        return {
            "pooling_enabled": True,
            "status": status,
            "total_pools": metrics["total_pools"],
            "warnings": warnings,
            "unhealthy_pools": unhealthy_pools,
            "high_utilization_pools": high_utilization_pools,
            "global_metrics": metrics["global_metrics"],
        }

    except Exception as e:
        logger.error(f"Error checking pool health: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to check pool health: {str(e)}")
