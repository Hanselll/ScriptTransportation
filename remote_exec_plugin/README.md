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

## 安装方法

> Python 3.10+

```bash
cd remote_exec_plugin
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## requirements 安装方式

```bash
pip install -r requirements.txt
```

## VMware 共享目录约定

固定挂载点：

```text
/mnt/hgfs/agent_dropzone
```

目录应包含：

```text
/mnt/hgfs/agent_dropzone/
├── outbox/
├── reports/
├── archive/
└── failed/
```

可通过 `workflow.deploy_and_run()` / `workflow.run_full_job()` 自动创建目录。

## 使用示例

### 1) 读取共享文件

```python
from tools import tool_read_shared_file

info = tool_read_shared_file("outbox/case1.sh")
print(info["file_name"], info["size"])
```

### 2) 上传并执行命令

```python
from tools import tool_upload_file, tool_run_remote_command

tool_upload_file(
    file_key="outbox/case1.sh",
    server_ip="10.217.8.238",
    username="root",
    password="your_password",
    remote_path="/tmp/testjobs/"
)

result = tool_run_remote_command(
    server_ip="10.217.8.238",
    username="root",
    password="your_password",
    command="bash /tmp/testjobs/case1.sh"
)
print(result)
```

### 3) 最小可运行闭环示例（run_full_job）

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

## `run_full_job()` 输出结构

```json
{
  "job_status": "success|failed",
  "file_key": "outbox/case1.sh",
  "server_ip": "10.217.8.238",
  "remote_path": "/tmp/testjobs/",
  "run_command": "bash /tmp/testjobs/case1.sh",
  "execution": {
    "exit_code": 0,
    "stdout": "...",
    "stderr": "..."
  },
  "report": {
    "local_report_dir": "/mnt/hgfs/agent_dropzone/reports/job_001",
    "artifacts": ["..."]
  },
  "analysis": {
    "job_status": "success|failed|unknown",
    "summary": "...",
    "key_metrics": {},
    "root_causes": []
  }
}
```

## 安全限制说明

- 仅允许连接 `ALLOWED_HOSTS` 中的远端地址
- 远端命令执行会进行危险关键词拦截
- 共享目录访问仅允许 `SHARED_ROOT` 下相对路径
- 防止路径穿越（`../`）
- 文件读取支持最大大小限制（默认 100MB）

## 报告分析支持格式

`report_parser.analyze_report()` 支持：

1. **JSON**：识别 `status/job_status/total/total_cases/passed/failed/summary`
2. **XML（JUnit 风格）**：识别 `tests/failures/errors/skipped`
3. **日志文本（.log/.txt）**：统计 `error/failed/exception/timeout` 行并提取关键原因

当无法识别格式或文件不存在时，会返回兜底结构，不会直接崩溃。
