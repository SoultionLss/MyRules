# 规则合集自动生成仓库（Auto Rules Collection）

由 **GitHub Actions 全自动驱动、零本地操作**：定时从多个公开规则源拉取规则，合并去重后生成规则集并自动提交推送。

## 特性

- 全自动：GitHub Actions 每天 **北京时间 12:00**（UTC 04:00）自动更新 + 手动触发
- 架构一致：每个平台一个目录，主配置引用 `Rules/*.yaml` 的 raw 链接（自动指向本仓库与当前分支）
- 自由添加上游：在 `scripts/sources.json` 中任意添加/移除来源（支持内置仓库缩写与任意完整 URL）
- 自动去重：跨来源合并时按规则行去重，剔除注释/空行
- 网页版友好：全部文件可在 GitHub 网页端创建维护，无需本地环境

## 平台与来源

| 平台 | 来源仓库 |
| --- | --- |
| Egern | xkww3n/Rules、blackmatrix7/ios_rule_script、QuixoticHeart/rule-set |
| Clash / Clash Meta | Loyalsoldier/clash-rules、DustinWin/ruleset_geodata、ACL4SSR |
| Surge | blackmatrix7/ios_rule_script、xkww3n/Rules、Hackl0us/SS-Rule-Snippet |
| Shadowrocket | GMOogway/shadowrocket-rules、blackmatrix7/ios_rule_script |
| Loon / Quantumult X | blackmatrix7/ios_rule_script、fmz200/wool_scripts |
| sing-box | xkww3n/Rules、DustinWin/ruleset_geodata |

## 目录结构

```
.
├── .github/workflows/sync.yml   # 定时工作流（每天北京时间 12:00）
├── scripts/
│   ├── generate.py              # 生成器：拉取 -> 合并去重 -> 多格式输出 + 渲染主配置
│   └── sources.json             # 共享类别与各平台配置（可自由添加）
├── templates/                   # 各平台主配置模板（{{RULES}} 等占位符自动替换）
│   ├── egern/Egern.yaml
│   ├── surge/Surge.conf
│   ├── loon/Loon.conf
│   ├── shadowrocket/Shadowrocket.conf
│   ├── quantumultx/QuantumultX.conf
│   ├── clash/mihomo.yaml        # mihomo / Stash / Surfboard 共用
│   └── singbox/config.json
├── Egern/                       # 生成产物（9 个平台目录，对齐 Repcz/Tool）
│   ├── Egern.yaml               #   主配置（raw 链接指向本仓库）
│   └── Rules/*.yaml             #   规则集（sing-box 风格 YAML）
├── Surge/                       #   Surge.conf + Rules/*.list（Surge 行格式）
├── Loon/                        #   Loon.conf + Rules/*.list
├── Shadowrocket/                #   Shadowrocket.conf + Rules/*.list
├── QuantumultX/                 #   QuantumultX.conf + Rules/*.list（host-suffix 格式）
├── mihomo/  Stash/  Surfboard/  #   主配置 + Rules/*.list（rule-providers 引用）
├── sing-box/                    #   config.json + Rules/*.json（sing-box 规则集）
├── README.md                    # 本文档
├── EXPLANATION.md               # 解释描述文件
└── PSEUDOCODE.md                # 生成逻辑伪代码（规则补充入口）
```

## 各平台规则文件格式

| 平台 | Rules 文件 | 格式 |
| --- | --- | --- |
| Egern | `*.yaml` | sing-box 风格 YAML（domain_set / domain_suffix_set ...） |
| Surge / Loon / Shadowrocket / Stash / Surfboard / mihomo | `*.list` | Surge 行格式（`DOMAIN-SUFFIX,xxx`） |
| QuantumultX | `*.list` | QX 前缀格式（host / host-suffix / ip-cidr ...） |
| sing-box | `*.json` | sing-box 规则集（`{"version":1,"rules":[...]}`） |

## 工作流程

1. 定时触发（每天 UTC 04:00 = 北京时间 12:00）或手动 `workflow_dispatch`；修改 `scripts/`、`templates/` 也会触发
2. 按 `sources.json` 共享类别拉取各平台上游规则，自动识别 3 种上游格式（Clash payload / sing-box YAML / 点号通配文本）
3. 合并去重，按平台格式输出 `<平台>/Rules/<类别>.<ext>`
4. 按模板渲染各平台主配置（规则引用 raw 链接自动填入 仓库名/当前分支）
5. 自动 commit & push（适配任意默认分支名）

## 网页版 GitHub 创建步骤

1. 右上角 `+` → `New repository`，创建公开仓库
2. 仓库内 `Add file → Create new file`，按目录结构逐个粘贴本套文件
3. 添加 `.github/workflows/sync.yml`
4. Actions 首次运行需手动触发一次（Actions → 选中工作流 → Run workflow）

## 如何自由添加上游

编辑 `scripts/sources.json` 中对应平台的 `categories.<类别>.sources`：

```json
{"repo": "blackmatrix7", "cat": "Netflix"},            // 内置仓库缩写
{"repo": "xkww3n", "file": "youtube"},                 // 内置仓库缩写
{"url": "https://raw.githubusercontent.com/某用户/某仓库/main/某文件.yaml"}  // 任意完整 URL
```

## 产物使用方式

Egern 客户端直接导入 `Egern/Egern.yaml` 的 raw 链接即可（规则集自动按需拉取）；
单个规则集也可单独订阅 `Egern/Rules/<类别>.yaml`。

## 免责声明

本仓库仅做规则转发与合并，规则版权归各自上游作者所有，请遵守上游仓库 License。
