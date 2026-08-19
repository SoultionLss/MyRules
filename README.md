# 聚合规则集生成器

本仓库通过 GitHub Actions 每日自动聚合多个公开规则源，生成适配 Surge、Egern、Clash 等客户端的规则文件。

## 📂 规则文件输出结构

生成的规则文件位于 `output/` 目录，结构如下：
output/
├── Surge/
│ └── Rules/
│ ├── DIRECT.list
│ ├── REJECT.list
│ ├── Google.list
│ └── ...
├── Egern/
│ └── Rules/
│ ├── DIRECT.yaml
│ ├── REJECT.yaml
│ └── ...
└── Clash/
└── Rules/
├── DIRECT.yaml
├── REJECT.yaml
└── ...

## 🔧 自定义规则源

编辑 `config/my_rules.yaml`，按优先级添加或删除 `rule_set` 条目。

## 🚀 使用方式

- **Surge**：  
  `RULE-SET, https://raw.githubusercontent.com/你的用户名/仓库名/Rules/output/Surge/Rules/REJECT.list, REJECT`
- **Egern**：  
  `- rule_set: match: https://raw.githubusercontent.com/你的用户名/仓库名/Rules/output/Egern/Rules/REJECT.yaml policy: REJECT`
- **Clash**：  
  `- RULE-SET, https://raw.githubusercontent.com/你的用户名/仓库名/Rules/output/Clash/Rules/REJECT.yaml, REJECT`

## 📅 更新频率

每天北京时间 20:00 自动更新，也支持手动触发（在 Actions 页面点击 “Run workflow”）。
