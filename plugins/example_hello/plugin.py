from fastapi import APIRouter, Depends

from app.api.dependencies import require_roles
from app.modules.models import User
from app.plugins.contracts import PluginContext, PluginContribution


def setup(context: PluginContext) -> PluginContribution:
    router = APIRouter()

    @router.get("/hello")
    def hello(user: User = Depends(require_roles("admin", "teacher"))):
        return {"plugin_id": context.plugin_id, "message": f"你好，{user.display_name}！插件接口工作正常。"}

    return PluginContribution(router=router)
