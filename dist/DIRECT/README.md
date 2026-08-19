# DIRECT 规则集

## 基本信息
- **策略名称**: DIRECT
- **规则总数**: 123826 条
- **规则来源**: direct, China, ChinaMax, geosite-cn, geoip-cn

## 导入方式

### Surge (使用 .list)
- Raw 链接: https://raw.githubusercontent.com/SoultionLss/MyRules/Rules/dist/DIRECT/DIRECT.list
- CDN 加速: https://cdn.jsdelivr.net/gh/SoultionLss/MyRules@Rules/dist/DIRECT/DIRECT.list

### Clash (使用 .yaml)
- Raw 链接: https://raw.githubusercontent.com/SoultionLss/MyRules/Rules/dist/DIRECT/DIRECT.yaml
- CDN 加速: https://cdn.jsdelivr.net/gh/SoultionLss/MyRules@Rules/dist/DIRECT/DIRECT.yaml

> 注：Egern 用户也可使用 .yaml，但需自行调整格式（将 payload: 改为 rules:）。

## 使用示例

Surge:
在 [Rule] 部分添加：
RULE-SET, https://cdn.jsdelivr.net/gh/SoultionLss/MyRules@Rules/dist/DIRECT/DIRECT.list, DIRECT

Clash:
在 rules 部分添加：
- RULE-SET, https://cdn.jsdelivr.net/gh/SoultionLss/MyRules@Rules/dist/DIRECT/DIRECT.yaml, DIRECT

Egern:
（需将 YAML 中的 payload: 手动改为 rules:）
- rule_set:
    match: https://cdn.jsdelivr.net/gh/SoultionLss/MyRules@Rules/dist/DIRECT/DIRECT.yaml
    policy: DIRECT

## 更新频率
本规则集每日自动更新（北京时间 20:00），确保与上游保持同步。
