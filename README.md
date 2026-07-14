# AI 教育智能备课与个性化学习辅导智能体

当前版本进一步提供可恢复的答疑会话与备课历史、多角色注册和家长多学生绑定、基于知识库的作业材料生成、薄弱知识画像、课堂高频问题、教师修正 AI 回答、站内通知及家长友好学习报告。教师可查看全部课程信息，但教学操作严格限制在其负责课程。

作业中心现支持严格契约解析 AI 材料、多选与判断题完整选项、已添加题目再次编辑、空标准答案由课程知识库自动补充，以及学生多次提交后逐次立即批改并显示标准答案。批改、材料生成和学习报告均使用 JSON Schema、Pydantic 校验和确定性兜底，模型格式异常不会再直接造成 5xx。

智能备课按完整教案、课堂讲稿、PPT 提纲和课堂练习分别生成可阅读的 Markdown 文本，支持历史预览与 Markdown 下载。全局顶部导航会显示当前位置，并固定提供退出登录入口；作业返回按钮采用醒目样式。作业材料生成使用 Ollama JSON Schema、容错归一化和文本降级，避免模型格式波动导致整批失败。

备课检索采用“整句命中优先、混合检索与 BGE 相关性阈值兜底”，无相关证据时拒绝生成，避免无论主题都引用同一份 Vue 等资料。作业材料生成可同时选择最多 10 份 ready 参考文件，并按文件均衡抽取上下文。

后端已按 `44.md` 补齐并接入 `agents`、`common`、`prompts`、`skills`、`tools`、`mcp` 与分层 RAG 结构。六类 Skill 使用版本化 Prompt；五个只读 Tool 和一个网页预览 Tool 通过白名单注册并复用课程权限；内部 MCP 网关支持版本协商、`ping`、`tools/list`、`tools/call`，远端 MCP 默认关闭并受主机白名单限制。管理员可从“Agent 能力”页面检查当前实际注册的版本、变量、工具和 MCP 状态。

知识库支持参考 `../course_spider/course_spider.py` 的网络资料获取流程：课程负责人可以按主题搜索或粘贴网页 URL，查看系统提取的正文预览，明确确认后才写入知识库、分块并向量化。待确认草稿 24 小时过期；系统遵守 robots.txt，并阻止内网地址、非 80/443 端口、异常重定向、非文本响应和超大页面。确认后的网页资料与本地文件一样参与备课、出题、答疑和标准答案生成，并保留原始来源链接。

华迪实训小组项目。

协作者可以在根目录 `plugins/<插件ID>/` 中独立增加受控 API 和页面，启用白名单由 `ENABLED_PLUGINS` 配置；完整开发、安全和测试说明见 [`plugins.md`](plugins.md)。插件页面会按角色动态加入左侧导航，普通插件的新增与升级不再需要修改核心路由源码。

智能备课 Markdown 使用独立渲染预览页。生成完成或从历史点击预览时进入“工作台 > 智能备课 > 文件名”；只有从收藏页点击预览时，导航才显示“工作台 > 智能备课 > 收藏 > 文件名”。原始 Markdown 仍可直接下载。

本目录是依据仓库根目录 `11.md` 与 `44.md` 实现的项目 MVP。后端采用 FastAPI + MySQL + Milvus，前端采用 Vue 3；本地模型使用 Ollama 的 `qwen2.5:latest` 与 `embeddinggemma:latest`。

## 环境

- Conda：`llm_learn`（Python 3.11）
- MySQL：官方 `mysql:8.4` Docker 容器 `edu-mysql`，数据位于 `D:\Docker\mysql`
- Milvus：现有 Docker 服务，默认端口 19530
- Ollama：默认 `http://localhost:11434`

## 快速开始

1. 复制 `.env.example` 为 `.env`，填写 MySQL 账号。
2. 启动已配置的 `edu-mysql` 容器；首次自行部署时可执行 `database/init_mysql.sql`。
3. 激活环境：`conda activate llm_learn`。
4. 执行迁移：`cd backend && alembic upgrade head`。
5. 启动后端：`powershell -ExecutionPolicy Bypass -File .\start_backend.ps1`。脚本将 reload 范围限制在 `backend`，避免扫描前端依赖目录。
6. 启动前端：`powershell -ExecutionPolicy Bypass -File .\start_frontend.ps1`。

当前数据库迁移版本为 `0009_submission_attempts`。升级后可使用网页确认入库以及作业多次提交记录。

作业中心、课堂运营、学情分析和教师学习报告采用“先选课程、再进入课程功能”的路由；面包屑会继续显示课程和具体作业。课程必填信息可维护，课程/作业可归档删除，知识库文档可单独删除。智能备课收藏页提供预览、下载、取消收藏和删除。桌面端左侧任务栏固定在视口中。

也可以手动启动后端：

```powershell
uvicorn app.main:app --reload --reload-dir backend --app-dir backend
```

### 前端运行环境修复

本机 Windows Installer 策略可能阻止系统级 Node 安装，因此项目使用便携 Node.js 24 LTS，位于 `.runtime/node-v24.18.0-win-x64`。启动脚本会自动设置临时 PATH 和项目级 Corepack 缓存，不要求全局 `node`、`npm` 或 `pnpm`。

可以在 `Code1` 目录直接验证：

```powershell
.\bin\node.cmd --version
.\bin\npm.cmd --version
.\bin\pnpm.cmd --version
```

不要再执行 `npm install -g pnpm`；直接运行 `start_frontend.ps1` 即可。

## 单端口部署运行

完成配置和数据库迁移后，可以由 FastAPI 同源托管 Vue 生产包：

```powershell
powershell -ExecutionPolicy Bypass -File .\start_production.ps1
```

访问 `http://127.0.0.1:8000`。该模式不启用 reload，也不需要单独运行 Vite。公网部署时仍应在前方配置 Nginx/Caddy HTTPS、防火墙、正式随机密钥、备份和域名。

后端文档：http://127.0.0.1:8000/docs

## 演示范围

已实现身份与课程、文档入库、Milvus 向量召回、MySQL 关键词召回、RRF 融合、BGE 重排、备课、作业批改、教师复核、问答、掌握度、学习路径、家长授权和报告发布，并提供自动化与真实端到端测试。外部服务不可用时会返回明确错误，不会静默切换到 SQLite 或伪造模型结果。

Agent 采用确定性编排：业务服务先通过受控查询获得证据，再由对应 Domain Agent 运行指定 Skill 和 Prompt。模型本身不能选择任意工具、执行 SQL 或绕过课程权限。新增能力应同时增加 Skill manifest、`SKILL.md`、版本化 Prompt、Schema 和测试。

## 项目文档

六份交付文档位于 `docs/`：软件需求规约、项目开发计划、数据库设计说明书、系统架构设计说明书、测试用例、用户使用手册。
