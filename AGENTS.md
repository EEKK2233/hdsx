# Agent 开发约束

1. 修改前阅读根目录 `../44.md`、本文件、相关模块和测试。
2. Python 命令统一在 `llm_learn` 环境运行。
3. 业务数据库只能使用 MySQL；Milvus 仅保存向量。
4. 依赖方向固定为 API -> Service -> Repository -> ORM。
5. 新表或字段必须带 Alembic 迁移；禁止以 `create_all` 代替正式迁移。
6. 新 Agent、Tool 和 Prompt 必须有版本化输入输出 Schema 与测试。
7. 不得硬编码密码、JWT 密钥或机器绝对路径；使用环境变量。
8. 不得让模型执行自由 SQL；写操作必须通过 service 权限和事务校验。
9. 需要下载、安装或修改现有 Docker 服务时，先报告并获得用户授权。
10. 每次交付需运行相关测试，并同步 README、OpenAPI 或设计文档。

