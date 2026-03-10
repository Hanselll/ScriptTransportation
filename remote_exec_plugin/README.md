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
