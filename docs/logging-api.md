# 结构化运行日志接口说明（给 OASX 客户端）

> 适用对象：需要用 HTTP 读取 OAS 运行日志、统计和错误诊断的外部客户端（Flutter/OASX 等）。
> 对应代码：`module/server/log_run_router.py`、`module/log/`、`module/logger.py`。
> 文本日志接口（`/logs/{脚本}` 窗口、`/logs/{脚本}/stream` SSE）保持不变，本文件只描述新增接口。

---

## 1. 整体设计

一次任务的一次执行尝试记为一个 **run**。同一个任务失败后重试时：

- `attempt` 递增（1、2、3…）；
- `parent_run_id` 指向该任务第一轮执行的 `run_id`。

日志是双轨的：

| 轨道 | 位置 | 读者 |
| --- | --- | --- |
| 文本日志（不变） | `log/YYYY-MM-DD_<脚本名>.txt` | 人、旧接口 |
| 结构化日志（新增） | `log/runs/YYYY-MM-DD/<run_id>.jsonl` + `log/runs/index.jsonl` | OASX、统计、诊断 |
| 错误现场（扩展） | `log/error/<脚本名>_<毫秒时间戳>/`（新增 `diagnosis.json`） | 排错、AI |

保留策略（启动时 + 每天第一次任务时自动清理）：

| 内容 | 保留 |
| --- | --- |
| 文本日志 | 7 天 |
| `log/runs/<日期>/` | 3 天 |
| `log/runs/index.jsonl` | 7 天 |
| `log/error/<出错目录>/` | 3 天 |

---

## 2. 通用约定

### 2.1 地址

默认服务地址：`http://127.0.0.1:22288`，路径前缀统一为 `/logs`。

### 2.2 响应包络

除文件下载接口外，所有 JSON 接口都返回：

```json
{
  "code": "ok",
  "error": null,
  "data": { }
}
```

出错时：

```json
{
  "code": "LOG_RUN_NOT_FOUND",
  "error": "没有找到这次运行记录",
  "data": null
}
```

- `code`：`"ok"` 表示成功；其余是稳定错误码，可直接用于分支判断。
- `error`：面向用户的中文说明（可能为 `null`）。
- `data`：业务数据（失败时为 `null`）。
- 字段名统一 **snake_case**。

### 2.3 其他约定

- 所有 JSON 接口带 `Cache-Control: no-cache`。
- 正常情况下 3 秒内返回；数据来自本地文件，不依赖设备连接。
- `script_name` 路径段使用**配置名**；服务端会按文本日志同一规则标准化（第一个下划线之后视为运行时后缀，例如 `大号_日常` → `大号`）。
- 新接口与旧接口并存：旧接口返回裸对象，新接口返回上面的包络。

### 2.4 通用错误码

| code | HTTP | 含义 |
| --- | --- | --- |
| `LOG_RUN_NOT_FOUND` | 404 | 没有这个 run |
| `LOG_DIAGNOSIS_NOT_FOUND` | 404 | 这个 run 没有诊断包（未出错或已被清理） |
| `LOG_DIAGNOSIS_BROKEN` | 500 | 诊断包文件损坏，无法解析 |
| `LOG_FILE_NOT_FOUND` | 404 | 错误目录内文件不存在 |
| `LOG_RUN_ID_INVALID` | 400 | `run_id` 格式不对 |
| `LOG_DATE_INVALID` | 422 | `date` 不是 `YYYY-MM-DD` |
| `LOG_CURSOR_INVALID` | 400 | 分页 `cursor` 非法 |
| `LOG_LIMIT_INVALID` | 422 | `limit` 超出范围 |
| `LOG_PATH_INVALID` | 400 | 文件路径不合法 |
| `LOG_PATH_FORBIDDEN` | 403 | 该错误目录不属于这个脚本 |

---

## 3. 接口列表

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| GET | `/logs/{script_name}/runs` | 运行记录列表（新到旧，分页） |
| GET | `/logs/{script_name}/runs/{run_id}` | 单次运行详情（摘要 + 事件流） |
| GET | `/logs/{script_name}/stats24h` | 最近 24 小时统计 |
| GET | `/logs/{script_name}/diagnosis/{run_id}` | 读取诊断包 JSON |
| GET | `/logs/{script_name}/error/files` | 错误现场目录列表（带诊断标记） |
| GET | `/logs/{script_name}/error/file?path=...` | 读取错误目录内的文件（log.txt / diagnosis.json / PNG） |

---

### 3.1 运行记录列表

```
GET /logs/{script_name}/runs?date=2026-11-23&limit=50&cursor=0
```

| 参数 | 必填 | 说明 |
| --- | --- | --- |
| `date` | 否 | 按 `started_at` 的日期过滤，`YYYY-MM-DD` |
| `limit` | 否 | 每页数量，1~200，默认 50 |
| `cursor` | 否 | 上一页返回的 `next_cursor`（就是偏移量） |

响应 `data`：

```json
{
  "script_name": "oas",
  "date": "2026-11-23",
  "items": [
    {
      "run_id": "20261123-153012-a1b2c3",
      "config_name": "oas",
      "script_name": "oas",
      "task": "Exploration",
      "attempt": 1,
      "parent_run_id": null,
      "status": "failed",
      "started_at": "2026-11-23T15:30:12",
      "finished_at": "2026-11-23T15:33:40",
      "duration_seconds": 208.0,
      "error_code": "E_CLICK_GUARD_STUCK",
      "error_summary": "画面长时间没有变化，任务卡住了",
      "diagnosis_dir": "oas_1763883052123"
    }
  ],
  "next_cursor": null,
  "has_more": false
}
```

`status` 取值：

| 值 | 含义 |
| --- | --- |
| `running` | 运行中（进程异常退出时也可能停留在这里） |
| `success` | 正常结束 |
| `failed` | 失败结束 |
| `aborted` | 被下一次 run 顶掉（通常是进程重启） |

---

### 3.2 单次运行详情

```
GET /logs/{script_name}/runs/{run_id}
```

`data`：

```json
{
  "run": { "run_id": "...", "status": "failed", "error_code": "E_PAGE_UNKNOWN", "...": "同列表字段" },
  "events": [
    {"type": "start", "run_id": "...", "ts": "2026-11-23T15:30:12.100", "task": "Exploration", "attempt": 1},
    {"type": "event", "ts": "2026-11-23T15:30:20.300", "level": "info", "message": "Scheduler: Start task `Exploration`"},
    {"type": "event", "ts": "2026-11-23T15:33:39.900", "level": "error", "message": "无法识别当前游戏界面（GamePageUnknownError）: ...", "error_code": "E_PAGE_UNKNOWN"},
    {"type": "end", "ts": "2026-11-23T15:33:40.000", "status": "failed", "duration_seconds": 208.0, "error_code": "E_PAGE_UNKNOWN"}
  ]
}
```

事件说明：

- `type=start`：run 开始，带 `config_name / script_name / task / attempt / parent_run_id`。
- `type=event`：`level` 为 `info/warning/error/critical`。目前记录所有 WARNING 及以上文本日志，以及任务开始/结束等关键节点。
- `type=end`：run 结束，带 `status / duration_seconds / error_code`。

---

### 3.3 最近 24 小时统计

```
GET /logs/{script_name}/stats24h
```

`data`：

```json
{
  "script_name": "oas",
  "window_hours": 24,
  "window_start": "2026-11-22T16:00:00",
  "window_end": "2026-11-23T16:00:00",
  "total": 12,
  "success": 9,
  "failed": 2,
  "aborted": 1,
  "running": 0,
  "success_rate": 0.8182,
  "avg_duration_seconds": 356.4,
  "top_blockers": [
    {"key": "E_CLICK_GUARD_STUCK", "count": 1},
    {"key": "E_PAGE_UNKNOWN", "count": 1}
  ],
  "by_task": [
    {"task": "Exploration", "total": 8, "success": 6, "failed": 2}
  ],
  "recent": [ { "run_id": "...", "task": "Exploration", "status": "success", "...": "同列表字段" } ]
}
```

统计口径（重要）：

- 滚动窗口按 **run 的开始时间** 计算，不是结束时间。
- 成功率分母只算已结束的 run（`success + failed`）；`aborted` / `running` 不计入。
- 平均耗时只统计已结束且有耗时的 run。
- `top_blockers` 按失败 run 的 `error_code` 聚合；缺失时用 `failed_rule`，再缺失用 `E_UNKNOWN`，最多 3 项。

---

### 3.4 诊断包

```
GET /logs/{script_name}/diagnosis/{run_id}
```

`data` 是 `diagnosis.json` 的完整内容（单文件不超过 64KB）：

```json
{
  "schema_version": 1,
  "generated_at": "2026-11-23T15:33:40",
  "run": { "run_id": "...", "task": "Exploration", "attempt": 1, "status": "failed", "duration_seconds": 208.0 },
  "error": {
    "code": "E_CLICK_GUARD_STUCK",
    "summary": "画面长时间没有变化，任务卡住了",
    "suggestion": "查看截图确认卡在哪个界面；脚本会自动重启游戏，若反复出现请检查任务配置。",
    "exception_type": "GameStuckError",
    "stack": "Traceback ...",
    "failed_rule": null,
    "failed_page": null
  },
  "timeline": [
    {"ts": "2026-11-23T15:30:20.300", "level": "info", "message": "..."}
  ],
  "screenshots": ["2026-11-23_15-33-39-123456.png"],
  "config_snapshot": {
    "config_name": "oas",
    "script": { },
    "enabled_tasks": { "Exploration": { } }
  },
  "environment": {
    "machine": "DESKTOP-XXX",
    "platform": "Windows-10-...",
    "python": "3.10.11",
    "oas_version": "unknown",
    "resolution": {"width": 1280, "height": 720},
    "screenshot_method": "auto",
    "control_method": "minitouch",
    "serial": "127.0.0.1:16384",
    "package": "com.netease.onmyoji"
  },
  "recent_actions": [ ],
  "log_tail": ["最后若干行文本日志"],
  "warning": "诊断包为便于排查保留了明文配置与日志，请勿上传到公开网络。"
}
```

说明：

- `timeline` 最多 200 条；`log_tail` 最多 200 行。
- 超过 64KB 时会自动裁剪 `log_tail` → `timeline` → `stack` → `config_snapshot`，并在顶层加 `"truncation": {"truncated": true, "original_bytes": N}`。
- `config_snapshot` 按用户要求保留明文（自用环境，不做脱敏），客户端展示时请提醒用户不要公开分享。
- 没有诊断包的 run（没出错、或错误目录被清理）返回 `LOG_DIAGNOSIS_NOT_FOUND`。

截图获取：用下面 3.6 的文件接口，`path=<diagnosis_dir>/<screenshots 里的文件名>`。

---

### 3.5 错误现场目录列表

```
GET /logs/{script_name}/error/files?date=2026-11-23&limit=50&cursor=0
```

`data`：

```json
{
  "date": "2026-11-23",
  "script_name": "oas",
  "items": [
    {
      "id": "oas_1763883052123",
      "directory": "oas_1763883052123",
      "script_name": "oas",
      "timestamp_ms": 1763883052123,
      "time": "2026-11-23T15:30:52+08:00",
      "legacy": false,
      "log_size": 12345,
      "image_count": 5,
      "has_diagnosis": true
    }
  ],
  "next_cursor": null,
  "has_more": false
}
```

旧格式目录（只有时间戳）的 `script_name` 为 `null`、`legacy=true`，不能通过 3.6 接口按脚本读取。

---

### 3.6 读取错误目录内的文件

```
GET /logs/{script_name}/error/file?path=oas_1763883052123/diagnosis.json
```

- 只允许读取 `<error_id>/log.txt`、`<error_id>/diagnosis.json`、`<error_id>/*.png`。
- `<error_id>` 必须以 `<标准化脚本名>_` 开头，否则返回 `LOG_PATH_FORBIDDEN`。
- 返回原始文件（`application/json` / `text/plain` / `image/png`），不带包络。

---

## 4. 业务错误码（run.error_code）

| code | 中文结论 | 建议 |
| --- | --- | --- |
| `E_ENV_RESOLUTION` | 模拟器分辨率不符合要求（需要 1280x720） | 改成 1280x720（DPI 240）后重跑 |
| `E_DEVICE_OFFLINE` | 模拟器或设备没有连上 | 确认模拟器启动、端口未变，重新连接 |
| `E_ADB` | ADB 连接异常 | 重启模拟器 ADB 或重启模拟器 |
| `E_GAME_NOT_RUNNING` | 游戏客户端没有运行 | 确认游戏可正常启动；脚本会自动重启游戏 |
| `E_LOGIN` | 游戏停在登录界面或登录态失效 | 手动登录一次 |
| `E_PAGE_UNKNOWN` | 无法识别当前游戏界面 | 看诊断截图；维护公告则等待维护结束 |
| `E_RULE_NOT_FOUND` | 任务需要的界面或图片模板没找到 | 可能界面改版，需更新任务规则图片 |
| `E_CLICK_GUARD_STUCK` | 画面长时间没有变化，任务卡住了 | 看截图；反复出现请检查任务配置 |
| `E_CLICK_GUARD_TOO_MANY` | 点击次数异常偏多 | 看截图；界面改版时需更新规则 |
| `E_SERVER_MAINTENANCE` | 游戏服务器可能正在维护 | 等维护结束再运行 |
| `E_ACTIVITY_UI_CHANGED` | 活动界面改版，找不到入口 | 确认活动是否改版并更新适配 |
| `E_TASK_CONFIG` | 任务配置不正确，需要人工处理 | 按提示检查对应任务设置 |
| `E_UNKNOWN` | 未分类错误 | 看诊断包堆栈与日志尾部 |

---

## 5. 客户端接入建议（OASX）

1. 日志页顶部：调 `stats24h` 展示 24 小时总次数、成功率、平均耗时、卡点 Top3，建议 30~60 秒刷新一次。
2. 运行列表：调 `runs` 分页展示；点进某条再调 `runs/{run_id}` 看事件流。
3. 失败条目标红色，按钮「查看诊断」→ 调 `diagnosis/{run_id}`，按 `error.summary` 和 `error.suggestion` 展示中文结论，技术细节折叠。
4. 截图：先取 `screenshots[0]`，再拼 `error/file?path=<diagnosis_dir>/<文件名>`。
5. 错误历史：调 `error/files`，`has_diagnosis=true` 的条目可以直接跳诊断。
6. 不要缓存这些接口（服务端已带 no-cache），也不要并发轮询大量 `runs/{run_id}`。

---

## 6. 兼容与回归

- 旧文本日志接口完全不变：`GET /logs/{script}`、`GET /logs/{script}/stream`、`GET /logs/errors`、`GET /logs/errors/{error_id}`、截图接口。
- 新接口只读取本地文件，不影响脚本运行；没有 run 数据时返回空列表而不是报错。
- 自动化测试：`toolkit\python.exe -m pytest tests\test_log_runs.py -q`。
