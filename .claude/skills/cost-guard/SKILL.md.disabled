---
name: cost-guard
description: LLM 调用成本估算与预算检查。当用户提到"成本"、"预算"、"熔断"、"多少钱"、"cost"或计划进行大量 LLM 调用时触发。
---

# 成本守卫

## 核心原则

**以 token 计数为准，成本只是粗略参考。** 实际价格以 DeepSeek 官方定价页为准。

## 月度预算

| 项目 | 预算 | 当前使用 |
|------|------|---------|
| API 总额 | 20美元/月 | 查询 tracker |
| 警告线 | 10美元 (50%) | — |
| 限制线 | 16美元 (80%) | 仅关键任务 |
| 阻断线 | 19美元 (95%) | 全阻断 |

## Token 估算参考

以下为各 task_type 的**预估 token 用量**，用于事前粗略估算：

| task_type | 预估 input | 预估 output | 说明 |
|-----------|-----------|------------|------|
| `pad_compute` | ~300 | ~150 | 轻量 |
| `action_infer` | ~800 | ~300 | 中等 |
| `rule_check` | ~400 | ~150 | 轻量 |
| `spatial_check` | ~300 | ~100 | 轻量 |
| `rerank` | ~1,500 | ~200 | 重输入 |
| `entity_extract` | ~800 | ~200 | 中等 |
| `scene_analysis` | ~1,500 | ~500 | 重量 |
| `foreshadow_detect` | ~1,200 | ~400 | 中等 |
| `causal_extract` | ~1,200 | ~400 | 中等 |
| `resolution_check` | ~1,000 | ~200 | 中等 |
| `event_predict` | ~1,200 | ~500 | 重量 |
| `style_check` | ~1,000 | ~300 | 中等 |
| `register_check` | ~1,000 | ~300 | 中等 |
| `theme_extract` | ~1,200 | ~400 | 中等 |

## 粗略估值公式

```
估值 = (预估_input_tokens × 0.000435 + 预估_output_tokens × 0.00087) / 1000
```

> 当前基于 DeepSeek V4-Pro 定价。实际价格以 [DeepSeek 官方](https://api-docs.deepseek.com/quick_start/pricing) 为准，用户自行核对。

## 批量操作估算

执行前先估算 token 总量：

```
场景: 全量分析 50 章
每章 scene_analysis: ~1,500 in + ~500 out
总 input:  50 × 1,500 = 75,000 tokens
总 output: 50 × 500   = 25,000 tokens
粗略估值: (75000 × 0.000435 + 25000 × 0.00087) / 1000 ≈ 0.054美元 ✅ 安全

场景: 全书审查 (Tier 4)
单次: ~50K in + ~15K out
粗略估值: ~0.035美元/次
月度剩余配额:足够数百次
```

## 降级策略

预算紧张时（>80%）：
1. 合并多次小调用为一次 `scene_analysis`
2. 关掉非关键的 `style_check` / `register_check`
3. 仅保留 CRITICAL_TASK_TYPES：`action_infer`, `rule_check`

## 检查命令

```bash
# 查看实际 token 用量和成本
python -c "from src.llm.cost_tracker import CostTracker; ct = CostTracker(); print(ct.get_status())"
```
