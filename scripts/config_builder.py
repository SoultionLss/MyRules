# """
# 配置文件生成器
# 功能：
# 1. 读取 merge_manifest.json 获取合并关系和独立源
# 2. 读取 templates/Egern.yaml 作为骨架模板
# 3. 为各平台生成主配置文件，输出到仓库二对应平台根目录
# 4. 为各平台生成根目录 README.md（引用语法已核对官方文档）
# """

import os
import json
import subprocess
import yaml
from pathlib import Path
from datetime import datetime

# ==================== 路径配置 ====================
SCRIPT_DIR = Path(__file__).parent
BASE_DIR = SCRIPT_DIR.parent
TEMPLATE_DIR = BASE_DIR / "templates"
EGERN_TEMPLATE = TEMPLATE_DIR / "Egern.yaml"
MANIFEST_PATH = BASE_DIR / "merge_manifest.json"
DIST_DIR = BASE_DIR / "dist"


# ==================== 目标仓库配置 ====================
def get_target_repo_info():
    target_repo = os.environ.get("TARGET_REPO")
    target_branch = os.environ.get("TARGET_BRANCH")
    if target_repo and target_branch:
        return target_repo, target_branch

    try:
        remote_url = subprocess.check_output(
            ["git", "config", "--get", "remote.origin.url"],
            cwd=BASE_DIR,
            stderr=subprocess.DEVNULL,
            text=True
        ).strip()
        if remote_url.startswith("https://"):
            path = remote_url.replace("https://", "").split("/", 1)[1]
            repo = path.replace(".git", "")
        elif remote_url.startswith("git@"):
            repo = remote_url.split(":")[1].replace(".git", "")
        else:
            raise ValueError("Unknown remote URL format")
        branch = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=BASE_DIR,
            text=True
        ).strip()
        return repo, branch
    except Exception as e:
        print(f"⚠️ 无法获取仓库信息，使用默认值: {e}")
        return "SoultionLss/MyRules", "main"


TARGET_REPO, TARGET_BRANCH = get_target_repo_info()
FULL_REPO = TARGET_REPO


def load_yaml(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def dump_yaml(data, filepath):
    with open(filepath, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, allow_unicode=True, sort_keys=False, indent=2)


def load_json(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


# ==================== 各平台规则引用生成 ====================

def generate_rule_refs_surge(platform: str, manifest: dict, cdn_base: str) -> list:
    """生成 Surge / Loon / QuantumultX 格式的规则引用"""
    refs = []
    ext = ".list"

    # 1. 合集引用（带注释）
    for merge_name, merge_info in manifest.get("merges", {}).items():
        sources = merge_info.get("sources", [])
        policy = merge_info.get("policy", merge_name)
        if not sources:
            continue

        refs.append(f"# 合并源: {', '.join(sources)} (共 {len(sources)} 个源)")
        url = f"{cdn_base}/{platform}/{policy}/{policy}{ext}"
        refs.append(f"RULE-SET, {url}, {policy}")
        refs.append("")  # 空行

    # 2. 独立源引用
    for source_name, src_info in manifest.get("independents", {}).items():
        policy = src_info.get("policy", source_name)
        url = f"{cdn_base}/{platform}/{policy}/{source_name}{ext}"
        refs.append(f"RULE-SET, {url}, {policy}")
        refs.append("")

    # 3. 兜底策略
    refs.append("FINAL, PROXY")

    return refs


def generate_rule_refs_clash(platform: str, manifest: dict, cdn_base: str) -> tuple:
    """生成 Clash 格式的规则引用 + rule-providers"""
    refs = []
    providers = {}

    # 1. 合集引用
    for merge_name, merge_info in manifest.get("merges", {}).items():
        sources = merge_info.get("sources", [])
        policy = merge_info.get("policy", merge_name)
        if not sources:
            continue

        refs.append(f"  # 合并源: {', '.join(sources)} (共 {len(sources)} 个源)")
        refs.append(f"  - RULE-SET, {policy}, {policy}")

        providers[policy] = {
            "type": "http",
            "url": f"{cdn_base}/{platform}/{policy}/{policy}.yaml",
            "interval": 86400,
            "behavior": "classical"
        }

    # 2. 独立源引用
    for source_name, src_info in manifest.get("independents", {}).items():
        policy = src_info.get("policy", source_name)
        refs.append(f"  - RULE-SET, {source_name}, {policy}")

        providers[source_name] = {
            "type": "http",
            "url": f"{cdn_base}/{platform}/{policy}/{source_name}.yaml",
            "interval": 86400,
            "behavior": "classical"
        }

    # 3. 兜底策略
    refs.append("  - MATCH, PROXY")

    return refs, providers


def generate_rule_refs_egern(platform: str, manifest: dict, cdn_base: str) -> list:
    """生成 Egern 格式的规则引用"""
    refs = []

    # 1. 合集引用（带注释）
    for merge_name, merge_info in manifest.get("merges", {}).items():
        sources = merge_info.get("sources", [])
        policy = merge_info.get("policy", merge_name)
        if not sources:
            continue

        refs.append(f"  # 合并源: {', '.join(sources)} (共 {len(sources)} 个源)")
        url = f"{cdn_base}/{platform}/{policy}/{policy}.yaml"
        refs.append(f"  - rule_set:")
        refs.append(f"      match: {url}")
        refs.append(f"      policy: {policy}")
        refs.append("")  # 空行

    # 2. 独立源引用
    for source_name, src_info in manifest.get("independents", {}).items():
        policy = src_info.get("policy", source_name)
        url = f"{cdn_base}/{platform}/{policy}/{source_name}.yaml"
        refs.append(f"  - rule_set:")
        refs.append(f"      match: {url}")
        refs.append(f"      policy: {policy}")
        refs.append("")

    # 3. 兜底策略
    refs.append("  - default:")
    refs.append("      policy: PROXY")

    return refs


def generate_rule_refs_singbox(platform: str, manifest: dict, cdn_base: str) -> tuple:
    """生成 Sing-box 格式的规则引用 + rule_set 定义"""
    refs = []
    rule_sets = []

    # 1. 合集引用
    for merge_name, merge_info in manifest.get("merges", {}).items():
        sources = merge_info.get("sources", [])
        policy = merge_info.get("policy", merge_name)
        if not sources:
            continue

        refs.append(f"    # 合并源: {', '.join(sources)} (共 {len(sources)} 个源)")
        refs.append(f'    {{ "rule_set": "{policy}" }},')

        rule_sets.append({
            "tag": policy,
            "type": "remote",
            "format": "source",
            "url": f"{cdn_base}/{platform}/{policy}/{policy}.json"
        })

    # 2. 独立源引用
    for source_name, src_info in manifest.get("independents", {}).items():
        policy = src_info.get("policy", source_name)
        refs.append(f'    {{ "rule_set": "{source_name}" }},')

        rule_sets.append({
            "tag": source_name,
            "type": "remote",
            "format": "source",
            "url": f"{cdn_base}/{platform}/{policy}/{source_name}.json"
        })

    # 3. 兜底策略（将最后一个逗号移除）
    if refs:
        refs[-1] = refs[-1].rstrip(',')

    return refs, rule_sets


def generate_rule_refs_v2ray(platform: str, manifest: dict, cdn_base: str) -> list:
    """生成 v2ray 格式的规则引用"""
    refs = []

    # 1. 合集引用
    for merge_name, merge_info in manifest.get("merges", {}).items():
        sources = merge_info.get("sources", [])
        policy = merge_info.get("policy", merge_name)
        if not sources:
            continue

        refs.append(f"    # 合并源: {', '.join(sources)} (共 {len(sources)} 个源)")
        refs.append(f'    {{ "domain": ["geosite:{policy}"] }},')

    # 2. 独立源引用
    for source_name, src_info in manifest.get("independents", {}).items():
        policy = src_info.get("policy", source_name)
        refs.append(f'    {{ "domain": ["geosite:{source_name}"] }},')

    # 3. 兜底策略
    if refs:
        refs[-1] = refs[-1].rstrip(',')

    return refs


def get_platform_config(platform: str, manifest: dict, cdn_base: str) -> dict:
    """根据平台生成对应的配置内容"""
    configs = {
        "Surge": {
            "output_file": "Surge.conf",
            "format_type": "ini",
            "rule_refs": generate_rule_refs_surge("Surge", manifest, cdn_base)
        },
        "Loon": {
            "output_file": "Loon.conf",
            "format_type": "ini",
            "rule_refs": generate_rule_refs_surge("Loon", manifest, cdn_base)
        },
        "QuantumultX": {
            "output_file": "QuantumultX.conf",
            "format_type": "ini",
            "rule_refs": generate_rule_refs_surge("QuantumultX", manifest, cdn_base)
        },
        "Clash": {
            "output_file": "Clash.yaml",
            "format_type": "yaml",
            "rule_refs": generate_rule_refs_clash("Clash", manifest, cdn_base)
        },
        "Egern": {
            "output_file": "Egern.yaml",
            "format_type": "yaml",
            "rule_refs": generate_rule_refs_egern("Egern", manifest, cdn_base)
        },
        "Singbox": {
            "output_file": "Singbox.json",
            "format_type": "json",
            "rule_refs": generate_rule_refs_singbox("Singbox", manifest, cdn_base)
        },
        "v2ray": {
            "output_file": "v2ray.json",
            "format_type": "json",
            "rule_refs": generate_rule_refs_v2ray("v2ray", manifest, cdn_base)
        }
    }
    return configs.get(platform)


# ==================== 各平台配置生成函数 ====================

def generate_ini_config(platform: str, base_config: dict, policy_groups: list, rule_refs: list) -> str:
    """生成 INI 格式配置（Surge / Loon / QuantumultX）"""
    lines = [
        f"# ============================================================",
        f"# {platform} 主配置文件（由 config_builder 生成）",
        f"# 仓库: https://github.com/{FULL_REPO}",
        f"# 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "# ============================================================",
        ""
    ]

    # General 部分
    lines.append("[General]")
    general = base_config.get('http_port') or base_config.get('general')
    if isinstance(general, dict):
        for key, value in general.items():
            lines.append(f"{key} = {value}")
    elif general:
        lines.append(str(general))
    else:
        lines.append("skip-proxy = 127.0.0.1, 192.168.0.0/16, 10.0.0.0/8, 172.16.0.0/12, 100.64.0.0/10, localhost, *.local")
        lines.append("bypass-tun = 192.168.0.0/16, 10.0.0.0/8, 172.16.0.0/12")
        lines.append("dns-server = 223.5.5.5, 119.29.29.29")
    lines.append("")

    # Proxy 部分
    lines.append("[Proxy]")
    lines.append("# 在此填写您的代理节点")
    lines.append("")

    # Proxy Group 部分
    lines.append("[Proxy Group]")
    for group in policy_groups:
        if 'select' in group:
            g = group['select']
            name = g['name']
            policies = g['policies']
            if isinstance(policies, list):
                policies_str = ', '.join(policies)
            else:
                policies_str = str(policies)
            lines.append(f"{name} = select, {policies_str}")
        elif 'fallback' in group:
            g = group['fallback']
            name = g['name']
            policies = g['policies']
            policies_str = ', '.join(policies)
            lines.append(f"{name} = fallback, {policies_str}")
        elif 'auto_test' in group:
            g = group['auto_test']
            name = g['name']
            policies = g['policies']
            policies_str = ', '.join(policies)
            lines.append(f"{name} = url-test, {policies_str}, url = http://1.1.1.1/generate_204, interval = 600")
    lines.append("")

    # Rule 部分
    lines.append("[Rule]")
    lines.extend(rule_refs)

    return '\n'.join(lines)


def generate_clash_config(base_config: dict, policy_groups: list, rule_refs: list, providers: dict) -> dict:
    """生成 Clash YAML 配置"""
    data = {
        "mode": "rule",
        "log-level": "info",
        "ipv6": False,
        "allow-lan": False,
        "external-controller": "127.0.0.1:9090",
        "proxies": [],
        "proxy-groups": [],
        "rule-providers": providers,
        "rules": rule_refs
    }

    for group in policy_groups:
        if 'select' in group:
            g = group['select']
            data["proxy-groups"].append({
                "name": g['name'],
                "type": "select",
                "proxies": g['policies']
            })
        elif 'fallback' in group:
            g = group['fallback']
            data["proxy-groups"].append({
                "name": g['name'],
                "type": "fallback",
                "proxies": g['policies']
            })
        elif 'auto_test' in group:
            g = group['auto_test']
            data["proxy-groups"].append({
                "name": g['name'],
                "type": "url-test",
                "proxies": g['policies'],
                "url": "http://1.1.1.1/generate_204",
                "interval": 600
            })

    return data


def generate_egern_config(base_config: dict, policy_groups: list, rule_refs: list) -> dict:
    """生成 Egern YAML 配置"""
    data = dict(base_config)
    data['policy_groups'] = policy_groups
    data['rules'] = rule_refs
    return data


def generate_singbox_config(base_config: dict, policy_groups: list, rule_refs: list, rule_sets: list) -> dict:
    """生成 Sing-box JSON 配置"""
    data = {
        "route": {
            "rules": rule_refs,
            "rule_set": rule_sets
        }
    }
    for key, value in base_config.items():
        if key not in ['rules', 'policy_groups']:
            data[key] = value
    return data


def generate_v2ray_config(base_config: dict, policy_groups: list, rule_refs: list) -> dict:
    """生成 v2ray JSON 配置"""
    data = {
        "routing": {
            "rules": rule_refs
        }
    }
    for key, value in base_config.items():
        if key not in ['rules', 'policy_groups']:
            data[key] = value
    return data


# ==================== 生成平台根目录 README（核对官方文档） ====================

def generate_platform_readme(platform: str, manifest: dict, output_dir: Path, cdn_base: str) -> None:
    """为指定平台生成根目录 README.md，引用语法已核对官方文档"""
    merges = manifest.get("merges", {})
    independents = manifest.get("independents", {})

    # 构建策略组列表
    policy_groups_dict = {}
    for merge_name, merge_info in merges.items():
        policy = merge_info.get("policy", merge_name)
        if policy not in policy_groups_dict:
            policy_groups_dict[policy] = []
        policy_groups_dict[policy].append({
            "name": merge_name,
            "type": "合集",
            "sources": merge_info.get("sources", [])
        })

    for src_name, src_info in independents.items():
        policy = src_info.get("policy", src_name)
        if policy not in policy_groups_dict:
            policy_groups_dict[policy] = []
        policy_groups_dict[policy].append({
            "name": src_name,
            "type": "独立",
            "sources": []
        })

    # 平台专用配置
    platform_configs = {
        "Surge": {
            "ext": ".list",
            "conf_file": "Surge.conf",
            "ref_example": f"RULE-SET, {cdn_base}/Surge/AI/AI.list, AI",
            "full_example": f"""[Rule]
# 合并源: OpenAI, Claude, Grok (共 3 个源)
RULE-SET, {cdn_base}/Surge/AI/AI.list, AI
# 独立源
RULE-SET, {cdn_base}/Surge/Google/Google.list, Google
FINAL, PROXY""",
            "doc_link": "https://manual.nssurge.com/book/understanding-surge/rules/rule-set.html"
        },
        "Loon": {
            "ext": ".list",
            "conf_file": "Loon.conf",
            "ref_example": f"RULE-SET, {cdn_base}/Loon/AI/AI.list, AI",
            "full_example": f"""[Rule]
# 合并源: OpenAI, Claude, Grok (共 3 个源)
RULE-SET, {cdn_base}/Loon/AI/AI.list, AI
# 独立源
RULE-SET, {cdn_base}/Loon/Google/Google.list, Google
FINAL, PROXY""",
            "doc_link": "https://nsloon.app/docs/"
        },
        "QuantumultX": {
            "ext": ".list",
            "conf_file": "QuantumultX.conf",
            "ref_example": f"RULE-SET, {cdn_base}/QuantumultX/AI/AI.list, AI",
            "full_example": f"""[Rule]
# 合并源: OpenAI, Claude, Grok (共 3 个源)
RULE-SET, {cdn_base}/QuantumultX/AI/AI.list, AI
# 独立源
RULE-SET, {cdn_base}/QuantumultX/Google/Google.list, Google
FINAL, PROXY""",
            "doc_link": "https://qx.atlucky.me/rule.html"
        },
        "Clash": {
            "ext": ".yaml",
            "conf_file": "Clash.yaml",
            "ref_example": f"""rule-providers:
  AI:
    type: http
    url: {cdn_base}/Clash/AI/AI.yaml
    interval: 86400
    behavior: classical
rules:
  - RULE-SET, AI, AI""",
            "full_example": f"""rule-providers:
  AI:
    type: http
    url: {cdn_base}/Clash/AI/AI.yaml
    interval: 86400
    behavior: classical
  Google:
    type: http
    url: {cdn_base}/Clash/Google/Google.yaml
    interval: 86400
    behavior: classical
rules:
  # 合并源: OpenAI, Claude, Grok (共 3 个源)
  - RULE-SET, AI, AI
  # 独立源
  - RULE-SET, Google, Google
  - MATCH, PROXY""",
            "doc_link": "https://clashfaq.com/rule-providers/"
        },
        "Egern": {
            "ext": ".yaml",
            "conf_file": "Egern.yaml",
            "ref_example": f"""- rule_set:
    match: {cdn_base}/Egern/AI/AI.yaml
    policy: AI""",
            "full_example": f"""rules:
  # 合并源: OpenAI, Claude, Grok (共 3 个源)
  - rule_set:
      match: {cdn_base}/Egern/AI/AI.yaml
      policy: AI
  # 独立源
  - rule_set:
      match: {cdn_base}/Egern/Google/Google.yaml
      policy: Google
  - default:
      policy: PROXY""",
            "doc_link": "https://egernapp.com/docs/"
        },
        "Singbox": {
            "ext": ".json",
            "conf_file": "Singbox.json",
            "ref_example": f"""{{
  "route": {{
    "rule_set": [
      {{
        "tag": "AI",
        "type": "remote",
        "format": "source",
        "url": "{cdn_base}/Singbox/AI/AI.json"
      }}
    ],
    "rules": [
      {{ "rule_set": "AI" }}
    ]
  }}
}}""",
            "full_example": f"""{{
  "route": {{
    "rule_set": [
      {{
        "tag": "AI",
        "type": "remote",
        "format": "source",
        "url": "{cdn_base}/Singbox/AI/AI.json"
      }},
      {{
        "tag": "Google",
        "type": "remote",
        "format": "source",
        "url": "{cdn_base}/Singbox/Google/Google.json"
      }}
    ],
    "rules": [
      {{ "rule_set": "AI" }},
      {{ "rule_set": "Google" }}
    ]
  }}
}}""",
            "doc_link": "https://sing-box.sagernet.org/configuration/route/rule-set/"
        },
        "v2ray": {
            "ext": "_domain.txt",
            "conf_file": "v2ray.json",
            "ref_example": f"""{{
  "routing": {{
    "rules": [
      {{ "domain": ["geosite:AI"] }}
    ]
  }}
}}""",
            "full_example": f"""{{
  "routing": {{
    "rules": [
      # 合并源: OpenAI, Claude, Grok (共 3 个源)
      {{ "domain": ["geosite:AI"] }},
      # 独立源
      {{ "domain": ["geosite:Google"] }}
    ]
  }}
}}""",
            "doc_link": "https://www.v2fly.org/config/routing.html#ruleobject"
        }
    }

    cfg = platform_configs.get(platform)
    if not cfg:
        return

    ext = cfg["ext"]
    conf_file = cfg["conf_file"]
    ref_example = cfg["ref_example"]
    full_example = cfg["full_example"]
    doc_link = cfg.get("doc_link", "")

    # 构建策略组列表文本
    policy_list_lines = []
    for policy in sorted(policy_groups_dict.keys()):
        policy_list_lines.append(f"### {policy}")
        policy_list_lines.append("")
        items = policy_groups_dict[policy]
        for item in items:
            if item["type"] == "合集":
                if item["sources"]:
                    sources_str = ", ".join(item["sources"])
                    policy_list_lines.append(f"- **合集** `{item['name']}`：包含 {sources_str}")
                else:
                    policy_list_lines.append(f"- **合集** `{item['name']}`")
            else:
                policy_list_lines.append(f"- **独立** `{item['name']}`")
        policy_list_lines.append("")

    policy_list = "\n".join(policy_list_lines)

    # 构建 README 内容
    content = f"""# {platform} 规则集

本目录包含 {platform} 平台的规则文件和主配置文件。

## 📁 目录结构

```
{platform}/
├── 策略组目录/          # 每个策略组一个子目录
│   ├── 合集文件          # 合并后的规则文件 ({ext})
│   └── 独立文件          # 独立规则源文件 ({ext})
└── {conf_file}          # 主配置文件
```

## 📋 策略组列表

{policy_list}

## 🔗 引用示例

### 单条规则引用

```{platform.lower()}
{ref_example}
```

### 完整配置示例

```{platform.lower()}
{full_example}
```

### 官方文档

更多语法请参考: {doc_link}

## 📅 更新频率

本规则集每日自动更新（北京时间 20:00）。

---

*最后更新: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""

    # 写入 README
    readme_path = output_dir / platform / "README.md"
    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"   ✅ 生成 {platform} README: {readme_path}")


# ==================== 主函数 ====================

def main():
    print("📖 读取配置文件...")

    # 1. 检查必要文件
    if not EGERN_TEMPLATE.exists():
        print("❌ templates/Egern.yaml 不存在，请先创建")
        return

    if not MANIFEST_PATH.exists():
        print("❌ merge_manifest.json 不存在，请先运行 generate.py")
        return

    # 2. 加载骨架模板和 manifest
    egern_data = load_yaml(EGERN_TEMPLATE)
    manifest = load_json(MANIFEST_PATH)

    print(f"✅ 读取 manifest 成功")
    print(f"   合并组: {len(manifest.get('merges', {}))} 个")
    print(f"   独立源: {len(manifest.get('independents', {}))} 个")

    # 3. 生成 CDN 基础 URL
    cdn_base = f"https://cdn.jsdelivr.net/gh/{FULL_REPO}@{TARGET_BRANCH}"

    # 4. 提取 Egern 模板中的基础配置（不含规则部分）
    base_config = {}
    exclude_keys = ['rules', 'policy_groups']
    for key, value in egern_data.items():
        if key not in exclude_keys:
            base_config[key] = value

    # 提取策略组定义
    policy_groups = egern_data.get('policy_groups', [])

    # 5. 为每个平台生成配置文件
    platform_names = ["Surge", "Loon", "QuantumultX", "Clash", "Egern", "Singbox", "v2ray"]

    for platform in platform_names:
        print(f"\n🔄 生成 {platform} 配置...")
        config = get_platform_config(platform, manifest, cdn_base)
        if not config:
            print(f"   ⚠️ 跳过 {platform}（不支持）")
            continue

        output_file = config["output_file"]

        if platform in ["Surge", "Loon", "QuantumultX"]:
            content = generate_ini_config(platform, base_config, policy_groups, config["rule_refs"])
            output_dir = DIST_DIR / platform
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / output_file
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"   ✅ 生成 {platform} 配置: {output_path}")

        elif platform == "Clash":
            refs, providers = config["rule_refs"]
            content = generate_clash_config(base_config, policy_groups, refs, providers)
            output_dir = DIST_DIR / platform
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / output_file
            dump_yaml(content, output_path)
            print(f"   ✅ 生成 {platform} 配置: {output_path}")

        elif platform == "Egern":
            refs = config["rule_refs"]
            content = generate_egern_config(base_config, policy_groups, refs)
            output_dir = DIST_DIR / platform
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / output_file
            dump_yaml(content, output_path)
            print(f"   ✅ 生成 {platform} 配置: {output_path}")

        elif platform == "Singbox":
            refs, rule_sets = config["rule_refs"]
            content = generate_singbox_config(base_config, policy_groups, refs, rule_sets)
            output_dir = DIST_DIR / platform
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / output_file
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(content, f, indent=2, ensure_ascii=False)
            print(f"   ✅ 生成 {platform} 配置: {output_path}")

        elif platform == "v2ray":
            refs = config["rule_refs"]
            content = generate_v2ray_config(base_config, policy_groups, refs)
            output_dir = DIST_DIR / platform
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / output_file
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(content, f, indent=2, ensure_ascii=False)
            print(f"   ✅ 生成 {platform} 配置: {output_path}")

    # ==================== 6. 生成各平台根目录 README ====================
    print("\n📝 生成各平台 README...")
    for platform in platform_names:
        generate_platform_readme(platform, manifest, DIST_DIR, cdn_base)

    print("\n🎉 所有平台配置文件生成完成！")


if __name__ == "__main__":
    main()
