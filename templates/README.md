# MyRules - 自动化规则集生成器

本项目通过 GitHub Actions 每日自动聚合多个公开规则源，生成适配 Surge、Loon、Egern、Clash 等客户端的规则集和配置文件。

## 📂 仓库结构
+ MyRules/
  + .github/workflows/sync.yml # GitHub Actions 工作流
  + config/
  + my_rules.yaml # 规则源配置文件
  + scripts/
  + generate.py # 规则集生成器
  + config_builder.py # 配置文件生成器
  + templates/
  + Egern.yaml # Egern 核心模板（输入）
  + Surge.conf # Surge 配置文件（输出）
  + Loon.conf # Loon 配置文件（输出）
  + Clash.yaml # Clash 配置文件（输出）
  + dist/ # 生成的规则集文件
  + README.md
## 🚀 使用方法

### 1. 规则集引用

生成的规则集位于 `dist/` 目录，每个策略组一个文件夹：
+ dist/
  + DIRECT/
  + DIRECT.list # Surge/Loon/Egern 格式
  + DIRECT.yaml # Clash 格式
  + README.md # 使用说明
  + REJECT/
  + ...
  + ...
### 2. 配置文件模板

生成的配置文件模板位于 `templates/` 目录：

- `Surge.conf` → Surge 配置文件
- `Loon.conf` → Loon 配置文件
- `Clash.yaml` → Clash 配置文件

将代理节点填入 `[Proxy]` 部分即可使用。

## ⚙️ 自定义规则源

编辑 `config/my_rules.yaml`，按优先级添加或删除规则源。

## 📅 更新频率

每日北京时间 20:00 自动更新，也支持手动触发（Actions → Run workflow）。

## 📝 许可证

MIT
