# This Python file uses the following encoding: utf-8
"""结构化运行日志：run 上下文、JSONL 存储、错误码与诊断包。

文本日志（log/YYYY-MM-DD_<脚本>.txt）保持不变，本包只做加法：
- 每个任务的一次执行尝试记为一个 run，写 log/runs/YYYY-MM-DD/<run_id>.jsonl；
- 每个 run 的摘要写 log/runs/index.jsonl，供服务端做列表与统计；
- 出错时在 log/error/<脚本>_<时间>/diagnosis.json 生成中文诊断结论。
"""
