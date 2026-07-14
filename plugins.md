# 协作插件开发与使用说明

## 1. 方案说明

项目支持把协作者的新功能放在根目录 `plugins/<插件ID>/` 中。核心系统只保留统一加载器、插件清单接口和通用页面宿主；新增、升级或删除普通插件时，不需要继续修改 `backend/app`、`frontend/src` 等核心业务源码。

插件可以同时提供：

- 独立 FastAPI 路由，最终地址固定为 `/api/v1/plugins/<插件ID>/...`；
- 独立 HTML/CSS/JavaScript 页面，显示在系统左侧导航中，并由 iframe 隔离样式；
- 仅后端 API 插件，此时不声明页面和导航即可。

插件 Python 代码会运行在后端进程内，拥有与主程序相同的系统权限。因此插件不是安全沙箱，只能启用已经审查、可信且版本固定的协作者代码。

## 2. 目录结构

```text
plugins/
└─ example_hello/
   ├─ plugin.json       # 必需：身份、版本、入口、导航与角色声明
   ├─ plugin.py         # 必需：后端入口，提供 setup(context)
   ├─ ui/               # 可选：独立前端页面
   │  └─ index.html
   ├─ tests/            # 推荐：插件自己的自动化测试
   └─ README.md         # 推荐：插件功能、权限和配置说明
```

插件 ID 只能使用小写字母、数字和下划线，必须以字母开头，并且目录名必须与 `plugin.json` 中的 `id` 完全一致。

## 3. 创建插件

复制 `plugins/example_hello`，例如创建 `plugins/attendance_helper`，然后修改 `plugin.json`：

```json
{
  "id": "attendance_helper",
  "name": "课堂考勤助手",
  "version": "1.0.0",
  "api_version": "1.0",
  "entrypoint": "plugin.py",
  "description": "提供课程考勤记录和汇总。",
  "navigation_label": "考勤助手",
  "navigation_roles": ["admin", "teacher"],
  "ui_directory": "ui"
}
```

`plugin.py` 必须返回 `PluginContribution`：

```python
from fastapi import APIRouter, Depends

from app.api.dependencies import require_roles
from app.modules.models import User
from app.plugins.contracts import PluginContext, PluginContribution


def setup(context: PluginContext) -> PluginContribution:
    router = APIRouter()

    @router.get("/summary")
    def summary(user: User = Depends(require_roles("teacher", "admin"))):
        return {"plugin": context.plugin_id, "teacher": user.display_name}

    return PluginContribution(router=router)
```

该接口最终访问地址是：

```text
GET /api/v1/plugins/attendance_helper/summary
```

插件必须继续使用主项目的 `current_user`、`require_roles`、课程可见性检查和 SQLAlchemy Session，不得自行绕过权限、拼接自由 SQL或连接 SQLite。

## 4. 添加插件页面

在 `plugin.json` 中声明 `ui_directory`，并在该目录提供 `index.html`。页面由主系统通过以下地址托管：

```text
/plugin-assets/<插件ID>/index.html
```

同时设置 `navigation_label` 和 `navigation_roles` 后，登录用户会在左侧任务栏看到插件入口。页面和主站同源，可以读取 `localStorage` 中的 `access_token`，调用 API 时仍须显式发送：

```javascript
fetch('/api/v1/plugins/attendance_helper/summary', {
  headers: {Authorization: `Bearer ${localStorage.getItem('access_token')}`}
})
```

插件页面在 iframe 中运行，不会覆盖主站 CSS。不要使用远程脚本、`eval`、内联密钥或不可信 HTML；需要复杂 Vue 页面时，建议在插件目录独立构建后，只提交构建所需源码与锁文件，生成物是否入库由团队约定。

## 5. 启用与停用

只有 `ENABLED_PLUGINS` 白名单中的插件会加载。多个 ID 使用英文逗号分隔：

```dotenv
ENABLED_PLUGINS=example_hello,attendance_helper
```

修改后重启后端。停用插件时从列表移除对应 ID并重启，不需要删除代码。若白名单中的插件缺少清单、入口无效或目录名不一致，后端会在启动时明确失败，避免静默运行残缺插件。

生产环境建议默认设置为空，再逐个审查和启用：

```dotenv
ENABLED_PLUGINS=
```

## 6. 数据库与迁移约束

插件若只读取现有数据，可以复用主项目 ORM。若确实需要新表或字段，必须提交到主项目的正式 Alembic 迁移链并经过负责人审核；插件不得在启动时执行 `CREATE TABLE`、调用 `create_all` 或私自维护第二套数据库迁移。

删除或停用插件不会自动删除数据。涉及插件数据删除时必须先备份，并使用经过审核的正式迁移或维护脚本。

## 7. 测试与提交

提交插件前至少执行：

```powershell
conda activate llm_learn
python -m pytest -q
cd frontend
..\bin\pnpm.cmd test
..\bin\pnpm.cmd run build
```

检查清单：

1. 插件未启用时，主系统仍能正常启动。
2. 普通学生不能访问教师插件接口或看到教师导航。
3. 插件所有写操作均校验资源权限并使用事务。
4. 清单版本采用 `主版本.次版本.修订号`。
5. 新依赖有锁定版本，不提交密码、私钥、PDF、模型和运行数据。
6. 同步插件 README、测试，以及受影响的项目文档。

## 8. 已提供示例

仓库已包含 `plugins/example_hello`。默认开发配置启用它，教师或管理员登录后可从左侧“协作插件”进入页面并调用示例接口。确认机制后，可以保留它作为模板，也可以从 `ENABLED_PLUGINS` 中移除。
