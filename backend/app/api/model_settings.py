from fastapi import APIRouter, Depends

from app.api.dependencies import require_roles
from app.api.schemas import ModelSettingsUpdate
from app.core.exceptions import AppError
from app.integrations.model_runtime import get_model_runtime
from app.modules.models import User
from plugins.model_providers import ProviderError

router = APIRouter(prefix="/admin/model-settings", tags=["model-settings"])


def _candidate(data: ModelSettingsUpdate):
    values = data.model_dump(exclude={"clear_llm_api_key", "clear_embedding_api_key"})
    config = get_model_runtime().merged(values)
    if data.clear_llm_api_key:
        config.llm_api_key = ""
    if data.clear_embedding_api_key:
        config.embedding_api_key = ""
    return config


@router.get("")
def read_model_settings(user: User = Depends(require_roles("admin"))):
    return get_model_runtime().config().public_dict()


@router.post("/test")
async def test_model_settings(data: ModelSettingsUpdate, user: User = Depends(require_roles("admin"))):
    runtime = get_model_runtime()
    config = _candidate(data)
    try:
        llm = await runtime.llm(config).health()
        embedding = await runtime.embedding(config).health()
    except ProviderError as exc:
        raise AppError("MODEL_CONNECTION_FAILED", str(exc), 422) from exc
    actual_dimension = embedding.get("dimension")
    if actual_dimension and int(actual_dimension) != config.embedding_dimension:
        raise AppError(
            "EMBEDDING_DIMENSION_MISMATCH",
            f"连接成功，但模型实际输出 {actual_dimension} 维，与填写的 {config.embedding_dimension} 维不一致",
            422,
        )
    return {"ok": True, "llm": llm, "embedding": embedding}


@router.put("")
def update_model_settings(data: ModelSettingsUpdate, user: User = Depends(require_roles("admin"))):
    runtime = get_model_runtime()
    config = _candidate(data)
    runtime.save(config)
    return config.public_dict()
