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
MyRules/
├── .github/workflows/ # GitHub Actions 工作流
│ └── sync.yml # 每日自动更新任务
├── config/
│ └── my_rules.yaml # ⭐ 规则源配置文件（唯一需要编辑的文件）
├── scripts/
│ ├── generate.py # 规则生成器
│ └── config_builder.py # 配置文件生成器
├── templates/ # 客户端配置模板
│ ├── Egern.yaml # Egern 核心模板
│ ├── Surge.conf # Surge 配置文件
│ ├── Loon.conf # Loon 配置文件
│ └── Clash.yaml # Clash 配置文件
├── dist/ # ⭐ 生成的规则文件（自动推送）
│ ├── DIRECT/ # 每个策略组一个文件夹
│ │ ├── DIRECT.list # Surge / Loon / Egern 格式
│ │ ├── DIRECT.yaml # Clash 格式
│ │ ├── DIRECT_domain.txt # v2ray 纯域名列表
│ │ └── README.md # 该策略组的使用说明
│ ├── REJECT/
│ ├── Google/
│ └── ...
└── README.md # 本文件
```
---

## 🚀 快速开始

### 1. 直接使用（推荐）

生成的规则文件位于 `dist/` 目录，每个策略组独立文件夹。你可以在客户端中直接引用以下 CDN 链接：

| 客户端 | 规则格式 | 引用示例 |
|--------|----------|----------|
| **Surge** | `.list` | `RULE-SET, https://cdn.jsdelivr.net/gh/SoultionLss/MyRules@Rules/dist/DIRECT/DIRECT.list, DIRECT` |
| **Egern** | `.list` | `- rule_set: match: https://cdn.jsdelivr.net/gh/SoultionLss/MyRules@Rules/dist/DIRECT/DIRECT.list policy: DIRECT` |
| **Clash** | `.yaml` | `- RULE-SET, https://cdn.jsdelivr.net/gh/SoultionLss/MyRules@Rules/dist/DIRECT/DIRECT.yaml, DIRECT` |

> 💡 将 `DIRECT` 替换为任意策略组名称（如 `REJECT`、`Google`、`YouTube` 等）即可引用对应规则。

### 2. 使用完整配置模板

仓库 `templates/` 目录下提供了各客户端的完整配置文件模板：

- **Surge**：`templates/Surge.conf`
- **Loon**：`templates/Loon.conf`
- **Clash**：`templates/Clash.yaml`
- **Egern**：`templates/Egern.yaml`

下载后填入你的代理节点信息即可直接使用。

---

## ⚙️ 自定义规则源

编辑 `config/my_rules.yaml` 文件，按优先级添加或删除 `rule_set` 条目。

**示例：添加一个新的规则源**

```yaml
- rule_set:
    match: https://cdn.jsdelivr.net/gh/用户/仓库@分支/路径/规则.list
    policy: 策略组名称
**支持的策略组**（与模板中的策略组一一对应）：
`DIRECT`、`REJECT`、`Google`、`YouTube`、`GitHub`、`Telegram`、`TikTok`、`Streaming`、`Social`、`HongKongSocial`、`AI`、`Global`、`Microsoft`

---

```markdown
---

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
