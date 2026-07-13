# 项目续接状态

## 2026-07-13 教学闭环产品化更新

已完成页面状态记忆、备课历史、多角色注册与家长多学生隔离、课程权限、知识库材料生成、薄弱画像、课堂高频问题、教师答疑修正、站内通知、家长友好报告和聊天式答疑界面。真实 MySQL 已升级到 `0007_classroom_ops`；后端测试 9 项通过，Vue TypeScript 检查与生产构建通过。备课检索已增加课程资料回退，新建课程后各业务页面重新激活时会刷新课程，注册 422 会显示具体字段原因。

更新时间：2026-07-11（Asia/Shanghai）

启动环境修复：2026-07-13

- Uvicorn reload 已限制为 `backend`，不会再扫描 `frontend/node_modules`。
- 新增 `start_backend.ps1`，自动选择 `llm_learn` Python 并使用 `python -m uvicorn`。
- Windows Installer 策略阻止系统 Node 修复，因此已配置项目便携 Node.js 24.18.0。
- 项目便携 npm 版本 11.16.0、pnpm 版本 11.7.0。
- 新增 `start_frontend.ps1` 和 `bin/node.cmd`、`bin/npm.cmd`、`bin/pnpm.cmd`。
- 后端 reload 启动和前端 Vite 开发服务器均已实际验证成功。

产品化功能迭代：2026-07-13

- 知识库支持最多 20 个文件批量上传和逐文件结果。
- 使用内容 SHA-256 查重；MySQL `0003_document_dedup` 提供并发唯一约束。
- 知识库显示当前文件、分类、分块、状态和上传时间。
- 导航、路由、总览和操作按教师/学生/家长/管理员角色区分。
- 总览功能卡片可以直接跳转到对应页面。
- 作业中心已拆分教师创建/发布/提交队列/批改复核与学生列表/详情/填写/结果。
- 作业列表显示标题、课程、分值、题数、提交数、截止时间和个人状态。
- 学生作业接口不返回标准答案和 rubric。
- 新增课程学生列表，报告和学情页面不再要求教师手填学生 ID。
- 新增 `start_production.ps1`，FastAPI 可同源托管 Vue 生产包。
- 后端测试 9 项通过，Vue 生产构建通过，真实产品功能脚本验证通过。

账号与课程成员迭代：2026-07-13

- 新增学生公开注册、个人资料修改和当前密码校验后的改密功能。
- 新增课程多负责人 `course_managers`，历史 owner 已自动迁移。
- 新增课程成员 `course_members` 和学生加入申请/负责人审批流程。
- 新增 CSV 批量导入学生，支持创建新学生和加入已有学生。
- 学生只能看到和访问正式加入课程的知识库、作业和答疑。
- 作业中心按课程分组；课堂答疑使用课程名称选择器。
- 新增账号设置、注册、课程发现、审批、导入和负责人管理界面。
- Alembic 已升级到 `0004_course_membership`。
- 真实验证结果：审批前访问 403、审批后 200、多负责人 2、批量导入成功。

## 当前阶段

总体任务状态：**项目 MVP 已完成并通过真实服务端到端验证**。

## 已完成

- 已读取并遵循仓库根目录 `11.md` 与 `44.md`。
- 已确认 Python 环境固定使用 Conda `llm_learn`（Python 3.11.15）。
- 已在 `llm_learn` 安装：Alembic、PyMySQL、pytest。
- 已确认 Ollama 可访问：
  - `qwen2.5:latest`
  - `embeddinggemma:latest`，向量维度 768
- 已确认本地 Qwen2-0.5B 与 BGE reranker 路径存在。
- 已完成 FastAPI + MySQL + SQLAlchemy + Alembic 后端骨架。
- 已完成用户/JWT/RBAC、课程、章节、知识点、文档上传和分块。
- 已完成 TXT/MD/PDF/DOCX 解析入口、关键词检索、引用式问答。
- 已完成 Ollama 备课、客观题判分、主观题辅助评分、教师复核接口。
- 已完成掌握度查询和报告生成接口。
- 已完成 Vue 3 页面：登录、总览、课程、知识库、备课、作业、答疑、学情、报告。
- 已固定前端依赖版本并生成 `pnpm-lock.yaml`。
- 已完成 MySQL 初始化 SQL、Alembic 基线迁移、环境检查和演示数据脚本。
- 已完成六份中文 Markdown 文档，位于 `docs/`。

## 已通过验证

- 后端：`5 passed in 2.06s`。
- 前端：TypeScript 检查通过。
- 前端 Vite 生产构建通过：103 modules transformed，产物位于 `frontend/dist/`。

## 当前环境与验证结果

- MySQL 使用官方 `mysql:8.4` 容器 `edu-mysql`，实际版本 8.4.10，数据位于 `D:\Docker\mysql`。
- Alembic 已升级到 `0002_learning_family`，真实 MySQL 已创建全部当前数据表。
- Milvus `edu_chunks_dev` 已创建并完成真实向量写入/召回。
- 已实现 RRF 融合与本地 BGE CPU 重排序。
- 已完成真实 MySQL + Milvus + Ollama + BGE 的端到端教学闭环测试。
- 掌握度、学习路径、家长授权、报告发布均已验证落库。
- SSE、Celery/Redis、完整班级管理 UI 属于后续工程增强，不阻塞 MVP。

## 重启后的第一步

1. 读取本文件、`AGENTS.md`、根目录 `44.md`。
2. 执行：

```powershell
conda activate llm_learn
cd D:\class\Season4_5\hdsx-d\Code1
python scripts\check_environment.py
```

3. 若服务未启动，启动 Docker Desktop、Ollama，并执行 `docker start edu-mysql`；Milvus 使用已有容器。
4. 运行 `alembic upgrade head` 检查迁移，再运行测试。
5. 启动后端与前端继续功能增强。

## 计划状态

- [x] 环境和 Code1 审计
- [x] 项目骨架、配置、MySQL 数据层和 FastAPI 核心模块
- [x] 核心业务/RAG/Agent MVP
- [x] Vue 前端与 API 接入
- [x] 真实 MySQL/Milvus、迁移、演示数据和端到端验证收尾
- [x] 六份中文项目文档
