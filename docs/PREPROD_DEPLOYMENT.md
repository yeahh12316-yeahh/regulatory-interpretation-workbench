# 准生产部署 runbook

第 15 项的目标是形成可重复启动的准生产环境，不把本地前端或 GitHub Pages 误称为后端公网生产环境。

## 首次配置

```bash
cp .env.preprod.example .env.preprod
```

编辑 `.env.preprod`，必须替换 `JWT_SECRET`、`POSTGRES_PASSWORD`，并填写 Nova 平台实际发放的 `LLM_API_KEY`。`LLM_MODEL` 只有在 Nova 平台确认模型标识完全一致时才使用 `DeepSeek-V4-Flash`。

API Key 只放在本机或部署平台的 Secret 中，不放入 GitHub、前端环境变量、截图或聊天记录。此前已经出现在会话中的密钥应撤销并重新生成。

## 启动和检查

```bash
make preprod-config
make preprod-up
curl -fsS http://127.0.0.1:8000/health
curl -fsS http://127.0.0.1:8000/ready
curl -fsS http://127.0.0.1:8000/metrics | head
```

服务包括 Web、API、PostgreSQL、Redis、Celery Worker、MinIO、Prometheus 和 PostgreSQL 定时备份容器。数据库、Redis 和 MinIO 默认只绑定本机；公网暴露应由有 TLS 和访问控制的反向代理承接。

## 运维检查

```bash
make preprod-logs
docker compose -f docker-compose.yml -f docker-compose.preprod.yml --env-file .env.preprod exec postgres-backup ls -lh /backups
```

备份文件和 SHA-256 校验文件保存在 `postgres_backups` 卷中。正式上线前必须在隔离数据库完成一次恢复演练；有云主机、域名、TLS、镜像仓库和持久化卷后，才能继续做公网部署。
