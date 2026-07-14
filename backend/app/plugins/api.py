from fastapi import APIRouter, Depends

from app.api.dependencies import current_user
from app.modules.models import User
from app.plugins.loader import get_plugin_registry

router = APIRouter(tags=["plugins"])


@router.get("/plugins")
def list_plugins(user: User = Depends(current_user)):
    values = []
    for plugin in get_plugin_registry().list():
        manifest = plugin.manifest
        if manifest.navigation_roles and user.role not in manifest.navigation_roles:
            continue
        values.append({
            "id": manifest.id, "name": manifest.name, "version": manifest.version,
            "description": manifest.description, "navigation_label": manifest.navigation_label,
            "navigation_roles": manifest.navigation_roles, "has_ui": plugin.ui_path is not None,
            "ui_url": f"/plugin-assets/{manifest.id}/index.html" if plugin.ui_path else None,
        })
    return values
