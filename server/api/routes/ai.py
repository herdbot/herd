"""AI integration API routes."""

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import structlog

logger = structlog.get_logger()

router = APIRouter()


class InterpretRequest(BaseModel):
    """Request for AI interpretation."""

    data: dict[str, Any]
    prompt: str
    provider: str | None = None


class InterpretResponse(BaseModel):
    """Response from AI interpretation."""

    interpretation: str
    provider: str
    model: str
    tokens_used: int | None = None


class PlanRequest(BaseModel):
    """Request for AI action planning."""

    goal: str
    context: dict[str, Any] = {}
    constraints: list[str] = []
    provider: str | None = None


class PlanResponse(BaseModel):
    """Response with AI-generated action plan."""

    goal: str
    steps: list[dict[str, Any]]
    provider: str
    model: str
    confidence: float | None = None


class ChatRequest(BaseModel):
    """Request for AI chat."""

    message: str
    history: list[dict[str, str]] = []
    system_prompt: str | None = None
    provider: str | None = None


class ChatResponse(BaseModel):
    """Response from AI chat."""

    response: str
    provider: str
    model: str


@router.post("/interpret", response_model=InterpretResponse)
async def interpret_data(request: InterpretRequest) -> InterpretResponse:
    """Send data to AI for interpretation.

    Useful for understanding sensor data, detecting anomalies,
    or classifying situations.
    """
    try:
        from server.ai.manager import get_ai_manager

        manager = get_ai_manager()
        result = await manager.interpret(
            data=request.data,
            prompt=request.prompt,
            provider=request.provider,
        )

        return InterpretResponse(
            interpretation=result["interpretation"],
            provider=result["provider"],
            model=result["model"],
            tokens_used=result.get("tokens_used"),
        )
    except ImportError:
        # AI module not fully configured
        raise HTTPException(
            status_code=503,
            detail="AI service not available. Configure API keys in settings.",
        )
    except Exception as e:
        logger.error("ai_interpret_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/plan", response_model=PlanResponse)
async def generate_plan(request: PlanRequest) -> PlanResponse:
    """Generate an action plan from a high-level goal.

    The AI will break down the goal into executable steps
    that can be sent as commands to devices.
    """
    try:
        from server.ai.manager import get_ai_manager

        manager = get_ai_manager()
        result = await manager.plan(
            goal=request.goal,
            context=request.context,
            constraints=request.constraints,
            provider=request.provider,
        )

        return PlanResponse(
            goal=request.goal,
            steps=result["steps"],
            provider=result["provider"],
            model=result["model"],
            confidence=result.get("confidence"),
        )
    except ImportError:
        raise HTTPException(
            status_code=503,
            detail="AI service not available. Configure API keys in settings.",
        )
    except Exception as e:
        logger.error("ai_plan_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """Conversational interface with AI.

    Supports multi-turn conversations with history.
    """
    try:
        from server.ai.manager import get_ai_manager

        manager = get_ai_manager()
        result = await manager.chat(
            message=request.message,
            history=request.history,
            system_prompt=request.system_prompt,
            provider=request.provider,
        )

        return ChatResponse(
            response=result["response"],
            provider=result["provider"],
            model=result["model"],
        )
    except ImportError:
        raise HTTPException(
            status_code=503,
            detail="AI service not available. Configure API keys in settings.",
        )
    except Exception as e:
        logger.error("ai_chat_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/providers")
async def list_providers() -> dict[str, Any]:
    """List available AI providers and their status."""
    from server.core import get_settings

    settings = get_settings()

    providers = {
        "openai": {
            "configured": settings.openai_api_key is not None,
            "default": settings.default_ai_provider == "openai",
        },
        "anthropic": {
            "configured": settings.anthropic_api_key is not None,
            "default": settings.default_ai_provider == "anthropic",
        },
    }

    return {
        "providers": providers,
        "default": settings.default_ai_provider,
    }
