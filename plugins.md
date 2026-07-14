# `p` 目录协作功能模块集成说明

## 1. 这不是“可选插件市场”

本项目所说的协作插件，是源码级组合模块：协作者把一项完整能力放在根目录 `p/<模块名>/` 中，项目负责人只在主项目的一个明确适配点 import 并调用它。模块启用后就是系统现有业务的一部分，不在左侧显示单独插件入口，也不允许运行时随意勾选、启停。

这种方式的目的：

- 协作者主要修改自己在 `p/` 下的代码，减少对核心业务文件的冲突；
- 核心项目仍负责身份、课程权限、事务、数据库迁移和最终页面；
- 外部功能通过少量稳定接口组合进知识库、作业、报告等现有模块；
- Git 合并时可以清楚区分“协作者实现”和“主项目接线代码”。

它不是安全沙箱。`p/` 中的 Python 代码会随主项目运行，合并前必须审查。

## 2. 当前真实示例：知识库网页爬虫

网页搜索和正文抓取实现已移动到：

```text
p/
└─ course_web_crawler/
   ├─ __init__.py
   └─ crawler.py
```

知识库服务只保留一处组合调用，并通过现有的兼容适配层保证从项目根目录或 `backend` 目录启动时都能找到 `p`：

```python
from app.integrations.web import WebArticleCrawler
```

随后在 `WebImportService` 中调用：

```python
results = await WebArticleCrawler().search(keyword, limit)
article = await WebArticleCrawler().fetch(url)
```

抓取后的数据仍由主项目负责：课程负责人权限、临时预览、确认入库、MySQL 事务、文档去重、分块、Embedding、Milvus 索引和删除。协作者的爬虫模块不直接写数据库，因此职责边界清晰。

`backend/app/integrations/web/crawler.py` 是稳定的组合适配层：它定位项目根目录并从 `p.course_web_crawler` 导出约定接口。业务代码统一依赖该适配层，协作者模块仍可独立更新，同时不会受启动工作目录影响。

## 3. 推荐目录结构

```text
p/
├─ __init__.py
├─ course_web_crawler/       # 已集成示例
│  ├─ __init__.py
│  ├─ crawler.py
│  └─ tests/                 # 可选的模块内部测试
└─ your_feature/
   ├─ __init__.py            # 只导出稳定公共接口
   ├─ service.py             # 协作者实现
   ├─ types.py               # 输入输出类型或 Pydantic Schema
   ├─ README.md              # 使用、限制和依赖
   └─ tests/
```

模块名使用小写字母、数字和下划线，不要与 `backend/app` 中现有包同名。

## 4. 稳定接口原则

主项目不应直接调用协作模块几十个内部函数。`p/<模块>/__init__.py` 应只导出少量稳定接口，例如：

```python
from p.assignment_exporter.service import AssignmentExporter

__all__ = ["AssignmentExporter"]
```

输入输出优先使用 dataclass 或 Pydantic：

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class ExportRequest:
    title: str
    questions: list[dict]

class AssignmentExporter:
    def export_markdown(self, request: ExportRequest) -> str:
        ...
```

核心代码只增加一次 import 和一次 service 调用。权限检查、ORM 查询、事务提交和 API 返回仍放在主项目中。

## 5. 集成新功能的步骤

以协作者 A 提供 `p/image_ocr` 为例：

1. A 只在 `p/image_ocr/` 编写 OCR 和测试。
2. A 在 `__init__.py` 导出稳定的 `ImageOCR.extract(data)`。
3. 项目负责人审查依赖、文件访问、网络请求和异常处理。
4. 在主项目对应 service 中加入：

   ```python
   from p.image_ocr import ImageOCR
   ```

5. 主项目在原有上传权限与事务范围内调用它。
6. 若需要页面，在现有业务页面加入按钮或表单，不创建独立“插件页面”。
7. 同步测试、README、`PROJECT_STATUS.md` 和受影响的 `docs/*.md`。

## 6. 核心项目与 `p` 模块的职责

| 内容 | `p` 协作模块 | 核心项目 |
| --- | --- | --- |
| 算法、解析器、第三方服务适配 | 是 | 只调用公共接口 |
| 登录、角色与课程权限 | 否 | 是 |
| SQLAlchemy Session 与事务 | 原则上否 | 是 |
| Alembic 迁移 | 不单独维护 | 进入主迁移链 |
| 页面入口与业务流程 | 提供数据能力 | 集成到现有页面 |
| 输入输出 Schema | 是 | 再做权限和业务校验 |
| 独立测试 | 是 | 另做集成与回归测试 |

## 7. 数据库和安全限制

- 不允许在 `p/` 模块中连接 SQLite 或创建第二套业务数据库。
- 不允许模块启动时执行 `create_all` 或任意 DDL。
- 需要新表或字段时，由项目负责人加入正式 Alembic 迁移。
- 不允许绕过 `current_user`、`require_roles`、课程成员或负责人检查。
- 不允许硬编码密码、Token、绝对机器路径或私钥。
- 网络模块必须设置超时、响应大小限制，并防止 SSRF；爬虫还必须遵守 robots.txt。
- 模块异常应转换为主项目可理解的错误，不能静默吞掉数据损坏。

## 8. 依赖管理

协作者若需要新依赖，应先在模块 README 说明用途、版本、许可证和体积，再由项目负责人统一加入 `pyproject.toml` 和锁文件。不要让 `p/` 模块在运行时自动执行 `pip install`、下载模型或启动 Docker。

## 9. 测试要求

每个模块至少包含：

- 公共接口输入输出测试；
- 异常、空输入和边界测试；
- 权限与事务由核心集成测试覆盖；
- 旧兼容导出仍可工作的回归测试（如果存在）。

项目总体验证：

```powershell
conda activate llm_learn
cd D:\class\Season4_5\hdsx-d\Code1
python -m pytest -q
cd frontend
..\bin\pnpm.cmd test
..\bin\pnpm.cmd run build
```

## 10. Git 协作建议

协作者分支尽量只包含：

```text
p/<自己的模块>/
模块测试
模块 README
确实需要的依赖声明
```

由项目负责人在后续提交中完成核心接线和页面集成。这样合并冲突集中在少量适配代码，而协作者的大部分实现始终留在独立目录中。
