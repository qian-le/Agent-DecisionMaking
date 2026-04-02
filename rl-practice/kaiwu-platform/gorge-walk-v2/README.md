# Gorge Walk V2 - Q-Learning Optimization

峡谷漫步Q-Learning优化版

## 优化内容

- 状态空间：400万 → 704
- 探索率衰减：每步重置 → 每回合衰减
- 奖励塑形：递增宝箱奖励 + 靠近终点奖励
- Q表初始化：1 → 0

## 文件结构

```
agent_q_learning/
├── agent.py          # 智能体实现
├── conf/
│   └── conf.py      # 配置文件
├── algorithm/
│   └── algorithm.py # Q-Learning算法
├── feature/
│   └── definition.py # 奖励塑形
└── workflow/
    └── train_workflow.py # 训练流程
```