# 解释描述文件（EXPLANATION）

本文件说明整套机制的设计意图、各来源仓库的解析、格式差异，以及伪代码（PSEUDOCODE.md）如何使用。

## 1. 这个项目解决什么问题

上游规则源分散在多个仓库，格式各异，且各自维护自己的规则。
本仓库通过 GitHub Actions 定时拉取、合并、去重，产出一个"一个仓库、按平台分类、开箱即用"的规则合集。

- 用户只需订阅本仓库的 raw 链接，无需关心上游仓库更新
- 生成任一平台合集后自动级联生成其余平台，减少重复维护
- 全程在 GitHub 网页端操作，无需本地安装任何工具

## 2. 各来源仓库解析

### 2.1 通用聚合源（被多个平台引用）

| 仓库 | 特点 | 适用于 |
| --- | --- | --- |
| blackmatrix7/ios_rule_script | 规则最全，按客户端分目录（Clash / Surge / Loon / QuantumultX / Shadowrocket） | Egern、Surge、Shadowrocket、Loon、Quantumult X |
| xkww3n/Rules | 多格式规则集，含 sing-box、Egern 分类 | Egern、Surge、sing-box |
| QuixoticHeart/rule-set | 主打 Clash 规则集 | Egern |

### 2.2 平台专属源

| 仓库 | 特点 | 适用于 |
| --- | --- | --- |
| Loyalsoldier/clash-rules | 官方推荐的 Clash 规则，GeoIP / GeoSite + 规则集 | Clash / Clash Meta |
| DustinWin/ruleset_geodata | 覆盖 Clash / sing-box 的规则集与 geodata | Clash、sing-box |
| ACL4SSR | 老牌全量规则库，含大量现成分组 | Clash / Clash Meta |
| Hackl0us/SS-Rule-Snippet | Surge 风格规则片段合集 | Surge |
| GMOogway/shadowrocket-rules | Shadowrocket 专属规则 | Shadowrocket |
| fmz200/wool_scripts | Loon / Quantumult X 分类规则 | Loon、Quantumult X |

## 3. 格式差异说明

| 格式 | 典型内容 | 平台 |
| --- | --- | --- |
| Clash YAML | `payload:` 下的规则行，或 geosite / geoip 引用 | Clash、Egern（部分） |
| Surge / 通用 List | `DOMAIN-SUFFIX,example.com` / `RULE-SET,xxx.list` | Surge、Egern、Shadowrocket、Loon |
| Quantumult X | `[filter_remote]` + `hostname = ` | Quantumult X |
| JSON / srs | sing-box 的 ruleset 格式 | sing-box |

> 合并时按目标平台统一格式：Clash 平台输出 YAML，Surge 系平台输出 List，Quantumult X 输出 conf，sing-box 输出 JSON/srs。

## 4. 目录与文件职责

| 文件 | 职责 |
| --- | --- |
| README.md | 项目总览、来源表、使用方式 |
| EXPLANATION.md | 本文件，解释设计 |
| PSEUDOCODE.md | **生成逻辑唯一真源**，新增规则在此补充 |
| .github/workflows/sync.yml | 触发与执行编排 |
| scripts/merge.py | 伪代码的最终实现（随伪代码同步完善） |
| scripts/sources.json | 来源 URL 配置，与伪代码分离，便于网页端修改 |

## 5. 伪代码如何"按需补充"

当前 PSEUDOCODE.md 为骨架，规则类别均以 `TODO` 标注。
流程：**提出需要某类规则 → 在伪代码对应平台小节追加条目 → 同步到 scripts 实现 → 重新运行 workflow 验证**。

示例：当提出"给 Egern 增加广告拦截"，则在 `generate_egern()` 中追加一条来源与输出说明，再在 `scripts/merge.py` 实现对应拉取与合并即可。

## 6. 注意事项

- 上游仓库可能变更路径，`sources.json` 失效时按 GitHub API 重新定位
- 大量拉取注意 GitHub 未认证 API 限流（60 次/小时），脚本内已做缓存与合并请求
- 规则版权归上游作者，分发时保留出处说明
