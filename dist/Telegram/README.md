# Telegram 规则集

## 基本信息
- **策略名称**: Telegram
- **规则总数**: 46 条
- **规则来源**: Telegram

## 导入方式

### Surge (使用 .list)
- Raw 链接: https://raw.githubusercontent.com/SoultionLss/MyRules/Rules/dist/Telegram/Telegram.list
- CDN 加速: https://cdn.jsdelivr.net/gh/SoultionLss/MyRules@Rules/dist/Telegram/Telegram.list

### Clash (使用 .yaml)
- Raw 链接: https://raw.githubusercontent.com/SoultionLss/MyRules/Rules/dist/Telegram/Telegram.yaml
- CDN 加速: https://cdn.jsdelivr.net/gh/SoultionLss/MyRules@Rules/dist/Telegram/Telegram.yaml

> 注：Egern 用户也可使用 .yaml，但需自行调整格式（将 payload: 改为 rules:）。

## 使用示例

Surge:
在 [Rule] 部分添加：
RULE-SET, https://cdn.jsdelivr.net/gh/SoultionLss/MyRules@Rules/dist/Telegram/Telegram.list, Telegram

Clash:
在 rules 部分添加：
- RULE-SET, https://cdn.jsdelivr.net/gh/SoultionLss/MyRules@Rules/dist/Telegram/Telegram.yaml, Telegram

Egern:
（需将 YAML 中的 payload: 手动改为 rules:）
- rule_set:
    match: https://cdn.jsdelivr.net/gh/SoultionLss/MyRules@Rules/dist/Telegram/Telegram.yaml
    policy: Telegram

## 更新频率
本规则集每日自动更新（北京时间 20:00），确保与上游保持同步。
