# MyRules · 自动化规则集生成器

[![GitHub Actions](https://img.shields.io/badge/Actions-自动构建-blue?logo=github)](https://github.com/SoultionLss/MyRules/actions)
[![License](https://img.shields.io/badge/License-MIT-green)](#)

本仓库通过 **GitHub Actions** 每日自动聚合多个公开规则源，生成适配 **Surge**、**Egern**、**Clash** 等客户端的规则文件，开箱即用。

---

## ✨ 特性

- 🔄 **每日自动更新**：北京时间 20:00 自动拉取上游最新规则，无需手动维护。
- 🧩 **多源聚合**：整合 blackmatrix7、Loyalsoldier、ACL4SSR 等主流规则集，去重合并。
- 📦 **多平台输出**：同时生成 Surge、Egern、Clash 三种格式的规则文件。
- ⚙️ **完全可定制**：编辑 `config/my_rules.yaml` 即可自由增删规则源和策略。
- 🚀 **CDN 加速**：所有规则文件通过 jsDelivr CDN 分发，加载速度快。

---

## 📂 目录结构
```
dist/
├── Surge/
│ └── Rules/
│ ├── DIRECT/
│ │ ├── DIRECT.list # Surge/Loon 格式
│ │ └── README.md # 使用说明
│ ├── REJECT/
│ └── ...
├── Clash/
│ └── Rules/
│ ├── DIRECT/
│ │ ├── DIRECT.yaml # Clash payload: 格式
│ │ └── README.md
│ └── ...
├── Egern/
│ └── Rules/
│ ├── DIRECT/
│ │ ├── DIRECT.yaml # Egern rules: 格式
│ │ └── README.md
│ └── ...
└── v2ray/
└── Rules/
├── DIRECT/
│ ├── DIRECT_domain.txt # 纯域名列表
│ └── README.md
└── ...
```
---


每个策略组（如 `DIRECT`、`REJECT`）在四个平台下均有独立文件夹，内含规则文件和 README。

---

## 🚀 快速开始

### 1. 直接使用（推荐）

直接引用对应平台的规则文件（以 `DIRECT` 策略为例）：

| 客户端 | 规则格式 | CDN 引用示例 |
|--------|----------|-------------|
| **Surge / Loon** | `.list` | `RULE-SET, https://cdn.jsdelivr.net/gh/SoultionLss/MyRules@Rules/dist/Surge/Rules/DIRECT/DIRECT.list, DIRECT` |
| **Clash** | `.yaml` | `- RULE-SET, https://cdn.jsdelivr.net/gh/SoultionLss/MyRules@Rules/dist/Clash/Rules/DIRECT/DIRECT.yaml, DIRECT` |
| **Egern** | `.yaml` | `- rule_set: match: https://cdn.jsdelivr.net/gh/SoultionLss/MyRules@Rules/dist/Egern/Rules/DIRECT/DIRECT.yaml policy: DIRECT` |
| **v2ray** | `_domain.txt` | 在 `domain` 字段引用 `https://cdn.jsdelivr.net/gh/SoultionLss/MyRules@Rules/dist/v2ray/Rules/DIRECT/DIRECT_domain.txt` |

### 2. 使用完整配置模板

仓库 `templates/` 目录下提供了各客户端的完整配置文件模板，下载后填入代理节点即可使用。

---

## ⚙️ 自定义规则源

编辑 `config/my_rules.yaml`，支持简写格式 `source:name`，例如：

```yaml
- rule_set:
    match: blackmatrix7:Google
    policy: Google
- rule_set:
    match: loyalsoldier:direct
    policy: DIRECT
- rule_set:
    match: acl4ssr:Advertising
    policy: REJECT
也支持完整 URL（向后兼容）。
---
```

## 📅 更新频率

- **自动更新**：每天北京时间 20:00（UTC 12:00）自动运行。
- **手动触发**：进入 GitHub Actions 页面，点击 "Run workflow" 即可立即更新。

---

## 📝 规则来源

本项目聚合了以下主流规则源（持续更新中）：

| 来源 | 说明 |
|------|------|
| [blackmatrix7/ios_rule_script](https://github.com/blackmatrix7/ios_rule_script) | 最全的 iOS/Clash 规则集 |
| [Loyalsoldier/clash-rules](https://github.com/Loyalsoldier/clash-rules) | 精简高效的 Clash 规则 |
| [Loyalsoldier/v2ray-rules-dat](https://github.com/Loyalsoldier/v2ray-rules-dat) | v2ray 域名/IP 规则 |
| [Loyalsoldier/surge-rules](https://github.com/Loyalsoldier/surge-rules) | Surge 格式规则集 |
| [ACL4SSR/ACL4SSR](https://github.com/ACL4SSR/ACL4SSR) | 广告拦截规则 |
| [xkww3n/Rules](https://github.com/xkww3n/Rules) | 国内直连规则 |
| [DustinWin/ruleset_geodata](https://github.com/DustinWin/ruleset_geodata) | 地理数据规则集 |

---

## 📄 许可证

[MIT License](https://opensource.org/licenses/MIT)
