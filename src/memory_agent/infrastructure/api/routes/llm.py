"""LLM provider management routes."""

from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from memory_agent.core.interfaces import LLMProviderType, ModelInfo
from memory_agent.infrastructure.llm.service import llm_service

router = APIRouter()


class ProviderInfo(BaseModel):
    """LLM provider information."""
    
    provider: str
    models: List[Dict]
    default_model: Optional[str]
    temperature: float
    max_tokens: int


class SetProviderRequest(BaseModel):
    """Request to set LLM provider."""
    
    provider: str = Field(..., description="Provider type (ollama, openai, anthropic)")
    config: Optional[Dict] = Field(None, description="Provider-specific configuration")


class SetProviderResponse(BaseModel):
    """Response after setting provider."""
    
    provider: str
    model_count: int
    default_model: Optional[str]


class ModelListResponse(BaseModel):
    """List of available models."""
    
    provider: str
    models: List[ModelInfo]


class TestCompletionRequest(BaseModel):
    """Request to test completion."""
    
    prompt: str = Field(..., description="Test prompt")
    model: Optional[str] = Field(None, description="Model to use")
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(None, ge=1, le=100000)


class TestCompletionResponse(BaseModel):
    """Test completion response."""
    
    response: str
    model: str
    provider: str
    tokens_used: int


@router.get(
    "/providers",
    response_model=List[str],
    status_code=status.HTTP_200_OK,
)
async def list_providers() -> List[str]:
    """List available LLM providers."""
    providers = await llm_service.get_available_providers()
    return [p.value for p in providers]


@router.get(
    "/current",
    response_model=ProviderInfo,
    status_code=status.HTTP_200_OK,
)
async def get_current_provider() -> ProviderInfo:
    """Get current LLM provider information."""
    try:
        info = await llm_service.get_provider_info()
        return ProviderInfo(**info)
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_424_FAILED_DEPENDENCY,
            detail=str(e),
        )


@router.post(
    "/provider",
    response_model=SetProviderResponse,
    status_code=status.HTTP_200_OK,
)
async def set_provider(request: SetProviderRequest) -> SetProviderResponse:
    """Set the active LLM provider."""
    try:
        # Convert string to enum
        provider_type = LLMProviderType[request.provider.upper()]
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid provider: {request.provider}",
        )
    
    try:
        # Set provider
        await llm_service.set_provider(provider_type, request.config)
        
        # Get info about the new provider
        info = await llm_service.get_provider_info()
        
        return SetProviderResponse(
            provider=info["provider"],
            model_count=len(info["models"]),
            default_model=info["default_model"],
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to set provider: {str(e)}",
        )


@router.get(
    "/models",
    response_model=ModelListResponse,
    status_code=status.HTTP_200_OK,
)
async def list_models(provider: Optional[str] = None) -> ModelListResponse:
    """List available models for a provider."""
    try:
        # Get provider type if specified
        provider_type = None
        if provider:
            try:
                provider_type = LLMProviderType[provider.upper()]
            except KeyError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid provider: {provider}",
                )
        
        # Get models
        models = await llm_service.get_available_models(provider_type)
        
        # Get current provider if not specified
        if not provider:
            info = await llm_service.get_provider_info()
            provider = info["provider"]
        
        return ModelListResponse(
            provider=provider,
            models=models,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list models: {str(e)}",
        )


@router.post(
    "/test",
    response_model=TestCompletionResponse,
    status_code=status.HTTP_200_OK,
)
async def test_completion(request: TestCompletionRequest) -> TestCompletionResponse:
    """Test LLM completion with current provider."""
    from memory_agent.core.entities import Message
    from memory_agent.core.interfaces import CompletionOptions, MessageRole
    
    try:
        # Create test message
        messages = [
            Message(
                role=MessageRole.USER,
                content=request.prompt,
            )
        ]
        
        # Create options
        options = CompletionOptions(
            model=request.model,
            temperature=request.temperature,
            max_tokens=request.max_tokens or 100,
        )
        
        # Generate completion
        response = await llm_service.complete(messages, options)
        
        # Get provider info
        info = await llm_service.get_provider_info()
        
        return TestCompletionResponse(
            response=response.content,
            model=response.model,
            provider=info["provider"],
            tokens_used=response.usage.total_tokens,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Completion failed: {str(e)}",
        )


@router.get(
    "/models/{model_id}/validate",
    response_model=Dict[str, bool],
    status_code=status.HTTP_200_OK,
)
async def validate_model(model_id: str, provider: Optional[str] = None) -> Dict[str, bool]:
    """Validate if a model is available."""
    try:
        # Get provider type if specified
        provider_type = None
        if provider:
            try:
                provider_type = LLMProviderType[provider.upper()]
            except KeyError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid provider: {provider}",
                )
        
        # Validate model
        is_valid = await llm_service.validate_model(model_id, provider_type)
        
        return {"valid": is_valid, "model_id": model_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Validation failed: {str(e)}",
        )