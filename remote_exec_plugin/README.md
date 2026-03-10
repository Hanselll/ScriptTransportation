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
    "remote_path": "/home/gsta/chaosmesh_workflow_runner_v16/chaos_runner/cases",
    "ssh_port": 50163
  }'
```
注意：JSON 里字段之间必须有逗号，比如 `"ssh_port": 50163,` 后面要带逗号。


如果 `/tool/upload_file` 提示 `Local file not found`，通常说明该路径在 **API server 所在机器** 不存在。

可直接改用 `upload_file_content` 通过 HTTP 上传文件内容（不依赖 API server 本地文件）：

```bash
FILE=/mnt/hgfs/ScriptTransportation/cases/modular_partition_ddb_with_upc_upu_upclb_kill.yaml
B64=$(base64 -w 0 "$FILE")

curl -s http://127.0.0.1:8080/tool/upload_file_content \
  -H 'Content-Type: application/json' \
  --data-binary @- <<JSON
{
  "file_name": "modular_partition_ddb_with_upc_upu_upclb_kill.yaml",
  "content_base64": "'$B64'",
  "server_ip": "10.230.246.195",
  "username": "gsta",
  "password": "gsta123",
  "remote_path": "/home/gsta/chaosmesh_workflow_runner_v16/chaos_runner/cases/",
  "ssh_port": 50163
}
JSON
```


如果你直接用 `-d "{...}"`，内部双引号很容易被 shell 吃掉，导致 `Request body is not valid JSON`。
推荐用上面的 heredoc 写法，或把整段 JSON 放到文件再 `--data-binary @payload.json`。


如果返回 `Incorrect padding`，表示你传入的 `content_base64` 不是合法的 base64 文本（例如直接写了 `"base64"` 占位符）。
请先生成真实 base64，再调用接口。


如果你的 SSH 不是 22 端口（例如 `50163`），请在请求里增加 `"ssh_port": 50163`。

本项目已使用 `ssh/scp -F /dev/null`，会忽略本机 `/etc/ssh/ssh_config`，避免 `Unsupported option "gssapiauthentication"` 这类本机 SSH 配置兼容问题。

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

- 远端地址限制已取消（按当前需求不启用 ALLOWED_HOSTS 限制）
- 远端命令执行会进行危险关键词拦截
- 共享目录读取接口仍使用 `SHARED_ROOT` 约定；上传接口支持直接传本地路径
- 防止路径穿越（`../`）
- 文件读取支持最大大小限制（默认 100MB）

## 报告分析支持格式

- JSON：识别 `status/job_status/total/total_cases/passed/failed/summary`
- XML（JUnit 风格）：识别 `tests/failures/errors/skipped`
- 日志文本（.log/.txt）：统计 `error/failed/exception/timeout` 关键行
