# 本地验证报告

验证日期：2026-10-30  
环境：Windows，Python 3.12，pytest 9.1.1

## 自动化回归

命令：

```powershell
python -m pytest -q
```

结果：`122 passed in 1.04s`

覆盖模块：

- 对局及回合状态机
- 购买、退款和奖励幂等
- 技能次数、冷却、伤害与护甲边界
- 购买、结算和重连事件契约
- 断线重连及服务端权威恢复
- 0/50/200/500ms延迟、丢包、重复包、乱序组合
- JSONL解析、错误上下文提取和CSV输出
- 10万条模拟事件规模检查

## 规模检查

本机单次结果：

```json
{
  "synthetic_records": 100000,
  "injected_errors": 10,
  "extracted_errors": 10,
  "elapsed_seconds": 0.7321783999796025,
  "peak_memory_mb": 0.016815185546875,
  "context_radius": 2
}
```

耗时和内存结果受机器、Python版本和运行环境影响，只用于本地回归对比，不作为通用性能承诺。可稳定复述的是：10万条模拟事件中注入10条ERROR，分析工具完整提取10条。
