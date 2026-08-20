# Global 规则集

## 基本信息
- **策略名称**: Global
- **规则总数**: 164 条
- **规则来源**: Loyalsoldier/surge-rules

## 文件说明
- `Global.list`  → Surge / Loon / Egern 通用（后缀匹配，每行 .domain）
- `Global.yaml`  → Clash RULE-SET 格式（payload: 列表）
- `Global_domain.txt` → v2ray 纯域名列表（每行一个域名）

## 导入链接

### Surge / Loon / Egern（使用 .list）
Raw 链接: https://raw.githubusercontent.com/SoultionLss/MyRules/Rules/dist/Global/Global.list
CDN 加速: https://cdn.jsdelivr.net/gh/SoultionLss/MyRules@Rules/dist/Global/Global.list

### Clash（使用 .yaml）
Raw 链接: https://raw.githubusercontent.com/SoultionLss/MyRules/Rules/dist/Global/Global.yaml
CDN 加速: https://cdn.jsdelivr.net/gh/SoultionLss/MyRules@Rules/dist/Global/Global.yaml

### v2ray（使用 _domain.txt）
Raw 链接: https://raw.githubusercontent.com/SoultionLss/MyRules/Rules/dist/Global/Global_domain.txt
CDN 加速: https://cdn.jsdelivr.net/gh/SoultionLss/MyRules@Rules/dist/Global/Global_domain.txt

## 使用示例

Surge / Loon / Egern:
在 [Rule] 部分添加：
RULE-SET, https://cdn.jsdelivr.net/gh/SoultionLss/MyRules@Rules/dist/Global/Global.list, Global

Clash:
在 rules 部分添加：
- RULE-SET, https://cdn.jsdelivr.net/gh/SoultionLss/MyRules@Rules/dist/Global/Global.yaml, Global

v2ray:
在配置文件中的 "domain" 或 "domains" 字段引用该 txt 文件，或将其内容合并。

## 更新频率
本规则集每日自动更新（北京时间 20:00），确保与上游保持同步。
