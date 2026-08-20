# REJECT 规则集（Egern 平台）

## 基本信息
- **策略名称**: REJECT
- **规则总数**: 770 条
- **规则来源条目总数**: 1 条
- **规则来源**: ios_rule_script@master/rule/Surge/Advertising/Advertising.list

## 文件说明
- `REJECT.yaml` → Egern 专用规则文件

## 导入链接

### Raw 链接
https://raw.githubusercontent.com/SoultionLss/MyRules/Rules/dist/Egern/Rules/REJECT/REJECT.yaml

### CDN 加速
https://cdn.jsdelivr.net/gh/SoultionLss/MyRules@Rules/dist/Egern/Rules/REJECT/REJECT.yaml

## 使用示例

### Egern
- rule_set:
    match: https://cdn.jsdelivr.net/gh/SoultionLss/MyRules@Rules/dist/Egern/Rules/REJECT/REJECT.yaml
    policy: REJECT

## 更新频率
本规则集每日自动更新（北京时间 20:00），确保与上游保持同步。
