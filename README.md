# 竞技游戏核心模块测试与自动化

[![automated-tests](https://github.com/KristenYue/valorant-core-qa/actions/workflows/tests.yml/badge.svg)](https://github.com/KristenYue/valorant-core-qa/actions/workflows/tests.yml)

这是一个基于竞技射击游戏公开流程建立的测试模型，覆盖对局状态、局内经济、技能伤害、接口契约、网络故障、断线重连和日志分析。项目不连接《无畏契约》客户端或非公开服务，也不复刻官方服务端实现；价格、上限等规则均由测试配置提供。

## 测试范围

| 模块 | 主要风险 | 验证方式 |
|---|---|---|
| 对局与回合状态 | 非法跳转、卡在中间态、重复结算 | 状态迁移与事件幂等测试 |
| 经济系统 | 负余额、重复扣款、失败请求产生副作用 | 边界值、等价类和事务一致性检查 |
| 技能与伤害 | 护甲边界错误、重复伤害、死亡后施法 | 参数化边界与状态检查 |
| 事件契约 | 字段缺失、类型变化、版本不兼容 | Schema与兼容性校验 |
| 网络与重连 | 延迟、丢包、重复包、乱序、旧状态覆盖 | 确定性故障注入与服务端快照恢复 |
| 日志分析 | 错误缺少上下文、大文件占用过多内存 | JSONL流式解析和上下文提取 |

当前测试套件包含122个pytest参数化场景。网络矩阵覆盖0/50/200/500ms延迟，以及丢包、重复包和乱序组合。规模检查使用10万条合成事件，其中注入10条ERROR并验证全部提取；这些数据不来自真实玩家或生产环境。

## 设计约束

- 余额始终处于配置的合法范围内。
- 失败购买不得修改余额、库存或交易记录。
- 相同`request_id`不得造成重复扣款或重复奖励。
- 相同`round_event_id`不得重复改变比分。
- 非法状态跳转必须被拒绝。
- 重连后使用服务端权威状态，不接受客户端旧快照覆盖。

## 目录

```text
src/valorant_qa/       领域模型、故障通道与日志分析
tests/                 pytest测试
test_data/             合成JSONL日志
docs/test_plan.md      风险、策略与准入标准
docs/test_cases.md     核心用例与测试方法
docs/state_machine.md  对局与回合状态图
docs/verification_report.md  本地验证记录
```

## 运行测试

```powershell
python -m pip install -e ".[dev]"
python -m pytest -v
```

分析示例日志：

```powershell
python -m valorant_qa.log_analyzer test_data/sample_match.jsonl reports/errors.csv --radius 2
```

运行10万条合成事件规模检查：

```powershell
python -m valorant_qa.scale_analysis --records 100000 --output reports/scale_report.json
```

## 已知限制

- 网络故障通道是可重复的离线模型，不等同于真实网络设备或线上压测。
- 领域方法用于模拟接口契约，不代表任何厂商的内部API。
- 规模检查用于验证处理正确性和回归趋势，不提供跨机器通用的性能结论。
