"""Model management endpoints for Ollama LLMs"""
import logging
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from src.api.dependencies import get_sql_generator, get_settings
from src.llm.sql_generator import SQLGenerator
from src.config.settings import Settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/models", tags=["Models"])


class ModelInfo(BaseModel):
    """Model information"""
    name: str
    size: str = "unknown"
    modified: str = "unknown"
    available: bool = True


class ModelListResponse(BaseModel):
    """Response for model list"""
    models: List[str]
    default_model: str
    count: int


class ModelDetailsResponse(BaseModel):
    """Detailed model information"""
    models: List[ModelInfo]
    default_model: str
    count: int
    ollama_url: str


@router.get("/", response_model=ModelListResponse)
async def list_models(
    sql_generator: SQLGenerator = Depends(get_sql_generator),
    settings: Settings = Depends(get_settings),
):
    """
    List all available Ollama models on the system

    Returns:
        List of model names available locally
    """
    try:
        # Initialize Ollama client if needed
        if not sql_generator.ollama.client:
            await sql_generator.initialize()

        # Get available models
        models = await sql_generator.ollama.list_models()

        return ModelListResponse(
            models=models,
            default_model=settings.OLLAMA_MODEL,
            count=len(models),
        )

    except Exception as e:
        logger.error(f"Error listing models: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list models: {str(e)}"
        )


@router.get("/details", response_model=ModelDetailsResponse)
async def get_model_details(
    sql_generator: SQLGenerator = Depends(get_sql_generator),
    settings: Settings = Depends(get_settings),
):
    """
    Get detailed information about available models

    Returns:
        Detailed model information including sizes
    """
    try:
        if not sql_generator.ollama.client:
            await sql_generator.initialize()

        # Get models using Ollama API
        response = await sql_generator.ollama.client.get("/api/tags")
        response.raise_for_status()
        data = response.json()

        # Parse model information
        model_infos = []
        for model in data.get("models", []):
            model_infos.append(ModelInfo(
                name=model.get("name", "unknown"),
                size=_format_size(model.get("size", 0)),
                modified=model.get("modified_at", "unknown"),
                available=True,
            ))

        return ModelDetailsResponse(
            models=model_infos,
            default_model=settings.OLLAMA_MODEL,
            count=len(model_infos),
            ollama_url=settings.OLLAMA_BASE_URL,
        )

    except Exception as e:
        logger.error(f"Error getting model details: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get model details: {str(e)}"
        )


@router.post("/pull/{model_name}", status_code=status.HTTP_200_OK)
async def pull_model(
    model_name: str,
    sql_generator: SQLGenerator = Depends(get_sql_generator),
):
    """
    Pull/download a model from Ollama library

    Args:
        model_name: Name of the model to pull (e.g., "llama3", "mistral")

    Returns:
        Success status
    """
    try:
        if not sql_generator.ollama.client:
            await sql_generator.initialize()

        logger.info(f"Pulling model: {model_name}")

        success = await sql_generator.ollama.pull_model(model_name)

        if success:
            return {
                "success": True,
                "message": f"Model '{model_name}' pulled successfully",
                "model": model_name,
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to pull model '{model_name}'"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error pulling model {model_name}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to pull model: {str(e)}"
        )


@router.get("/recommended", status_code=status.HTTP_200_OK)
async def get_recommended_models():
    """
    Get recommended models for SQL generation

    Returns:
        List of recommended models with descriptions
    """
    recommended = [
        {
            "name": "llama3",
            "size": "~4.7GB",
            "description": "Meta's Llama 3 - Great for SQL generation",
            "recommended": True,
            "command": "ollama pull llama3",
        },
        {
            "name": "codellama",
            "size": "~3.8GB",
            "description": "Code Llama - Optimized for code generation",
            "recommended": True,
            "command": "ollama pull codellama",
        },
        {
            "name": "mistral",
            "size": "~4.1GB",
            "description": "Mistral 7B - Fast and efficient",
            "recommended": True,
            "command": "ollama pull mistral",
        },
        {
            "name": "llama3:70b",
            "size": "~40GB",
            "description": "Llama 3 70B - Most accurate, requires GPU",
            "recommended": False,
            "command": "ollama pull llama3:70b",
        },
        {
            "name": "phi3",
            "size": "~2.3GB",
            "description": "Microsoft Phi-3 - Lightweight and fast",
            "recommended": True,
            "command": "ollama pull phi3",
        },
    ]

    return {
        "recommended_models": recommended,
        "note": "Pull models using: ollama pull <model-name>",
    }


@router.get("/test/{model_name}", status_code=status.HTTP_200_OK)
async def test_model(
    model_name: str,
    sql_generator: SQLGenerator = Depends(get_sql_generator),
):
    """
    Test a model with a simple SQL generation task

    Args:
        model_name: Model to test

    Returns:
        Test results
    """
    try:
        if not sql_generator.ollama.client:
            await sql_generator.initialize()

        # Simple test query
        test_prompt = "Generate SQL to select all users"

        response = await sql_generator.ollama.generate(
            prompt=test_prompt,
            model=model_name,
            temperature=0.1,
        )

        return {
            "model": model_name,
            "test_passed": len(response) > 0,
            "sample_output": response[:200] if response else "",
            "output_length": len(response),
        }

    except Exception as e:
        logger.error(f"Error testing model {model_name}: {e}")
        return {
            "model": model_name,
            "test_passed": False,
            "error": str(e),
        }


def _format_size(size_bytes: int) -> str:
    """Format size in bytes to human-readable string"""
    if size_bytes == 0:
        return "unknown"

    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(size_bytes)
    unit_index = 0

    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1

    return f"{size:.1f} {units[unit_index]}"
