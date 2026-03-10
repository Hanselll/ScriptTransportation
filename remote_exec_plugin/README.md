# remote_exec_plugin

一个轻量、可复用的 Python 智能体插件工程，用于在 Linux 虚拟机中完成以下闭环：

1. 从 VMware 共享目录读取宿主机文件
2. 上传到远端 Linux 服务器
3. 远端执行命令
4. 拉回远端报告到共享目录
5. 本地分析报告
6. 输出结构化结果

## 目录结构

```text
remote_exec_plugin/
├── api_server.py
├── config.py
├── shared_storage.py
├── sftp_transfer.py
├── ssh_executor.py
├── report_fetcher.py
├── report_parser.py
├── workflow.py
├── tools.py
├── utils.py
├── requirements.txt
└── README.md
```

## 环境要求

- Python 3.6+
- 系统命令：`ssh`、`scp`、`sshpass`、`tar`
- 不依赖第三方 Python 库

## 运行方式（无需安装额外 Python 包）

你可以直接使用系统自带 Python 运行，不需要创建 venv，也不需要安装任何第三方包：

```bash
cd remote_exec_plugin
python3 -m compileall .
```

## 常驻 API Server 运行方式

### 前台运行

```bash
cd remote_exec_plugin
python3 api_server.py --host 0.0.0.0 --port 8080
```

### 后台常驻运行（推荐）

```bash
cd remote_exec_plugin
nohup python3 api_server.py --host 0.0.0.0 --port 8080 > api_server.log 2>&1 &
echo $! > api_server.pid
```

停止服务：

```bash
kill "$(cat api_server.pid)"
```

### 可用接口

- `GET /health`：健康检查
- `GET /tools`：查看支持的工具接口
- `GET /config`：查看当前服务生效的 shared_root / allowed_hosts
- `POST /tool/read_shared_file`
- `POST /tool/upload_file`
- `POST /tool/upload_file_content`（客户端直接上传 base64 文件内容，不依赖 API 服务器本地文件）
- `POST /tool/run_remote_command`
- `POST /tool/fetch_report`
- `POST /tool/analyze_report`
- `POST /tool/run_full_job`

### HTTP 调用示例

```bash
curl -s http://127.0.0.1:8080/health
```

```bash
curl -s http://127.0.0.1:8080/tool/run_full_job \
  -H 'Content-Type: application/json' \
  -d '{
    "file_key": "outbox/case1.sh",
    "server_ip": "10.217.8.238",
    "username": "root",
    "password": "your_password",
    "remote_path": "/tmp/testjobs/",
    "run_command": "bash /tmp/testjobs/case1.sh",
    "remote_report_path": "/tmp/testjobs/output/",
    "local_report_key": "reports/job_001"
  }'
```


只上传文件示例：

```bash
curl -s http://127.0.0.1:8080/tool/upload_file \
  -H 'Content-Type: application/json' \
  -d '{
    "file_key": "cases/modular_partition_ddb_with_upc_upu_upclb_kill.yaml",
    "server_ip": "10.230.246.195",
    "username": "gsta",
    "password": "gsta123",
    "remote_path": "/home/gsta/chaosmesh_workflow_runner_v16/chaos_runner/cases"
  }'
```



如果 `/tool/upload_file` 提示 `Local file not found`，通常说明：

1. 该路径在 **API server 所在机器** 不存在（curl 发起端和 API server 不是同一台机器时最常见）
2. 或者 API server 进程看不到该挂载目录

可以先检查服务端看到的配置：

```bash
curl -s http://127.0.0.1:8080/config
```

然后使用 `upload_file_content` 直接通过 HTTP 上传文件内容：

```bash
FILE=/mnt/hgfs/ScriptTransportation/cases/modular_partition_ddb_with_upc_upu_upclb_kill.yaml
B64=$(base64 -w 0 "$FILE")

curl -s http://127.0.0.1:8080/tool/upload_file_content \
  -H 'Content-Type: application/json' \
  -d "{
    "file_name": "modular_partition_ddb_with_upc_upu_upclb_kill.yaml",
    "content_base64": "${B64}",
    "server_ip": "10.230.246.195",
    "username": "gsta",
    "password": "gsta123",
    "remote_path": "/home/gsta/chaosmesh_workflow_runner_v16/chaos_runner/cases/"
  }"
```

## 运行时配置（环境变量）

为了适配不同服务器目录和白名单，可以在启动 API 前设置：

- `REMOTE_EXEC_SHARED_ROOT`：共享根目录（默认 `/mnt/hgfs/agent_dropzone`）
- `REMOTE_EXEC_ALLOWED_HOSTS`：允许访问主机列表，逗号分隔（支持 `*` 允许所有主机）

示例：

```bash
export REMOTE_EXEC_SHARED_ROOT=/mnt/hgfs/ScriptTransportation
export REMOTE_EXEC_ALLOWED_HOSTS=10.230.246.195,10.217.8.238,10.217.8.239
python3 api_server.py --host 0.0.0.0 --port 58080
```

> 注意：如果你传的是绝对路径 `file_key`，它也必须位于 `REMOTE_EXEC_SHARED_ROOT` 之下。


排错说明（你这次报错对应）：

- 如果返回 `Server x.x.x.x is not in ALLOWED_HOSTS.`，请确认 `REMOTE_EXEC_ALLOWED_HOSTS` 包含该 IP。
- 当前版本会在每次请求时读取该环境变量，所以修改后**无需重启 API 进程**。

示例（允许你的目标机）：

```bash
export REMOTE_EXEC_ALLOWED_HOSTS=10.230.246.195,10.217.8.238,10.217.8.239
```

## VMware 共享目录约定

固定挂载点：`/mnt/hgfs/agent_dropzone`

```text
/mnt/hgfs/agent_dropzone/
├── outbox/
├── reports/
├── archive/
└── failed/
```

## Python 最小可运行示例

```python
from tools import tool_run_full_job

result = tool_run_full_job(
    file_key="outbox/case1.sh",
    server_ip="10.217.8.238",
    username="root",
    password="your_password",
    remote_path="/tmp/testjobs/",
    run_command="bash /tmp/testjobs/case1.sh",
    remote_report_path="/tmp/testjobs/output/",
    local_report_key="reports/job_001"
)

print(result)
```

## 安全限制说明

- 仅允许连接 `ALLOWED_HOSTS` 中的远端地址
- 远端命令执行会进行危险关键词拦截
- 共享目录访问仅允许 `SHARED_ROOT` 下相对路径
- 防止路径穿越（`../`）
- 文件读取支持最大大小限制（默认 100MB）

## 报告分析支持格式

- JSON：识别 `status/job_status/total/total_cases/passed/failed/summary`
- XML（JUnit 风格）：识别 `tests/failures/errors/skipped`
- 日志文本（.log/.txt）：统计 `error/failed/exception/timeout` 关键行
