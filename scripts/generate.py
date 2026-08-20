#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import shutil
import subprocess
import requests
import yaml
import re
from pathlib import Path
from collections import defaultdict
from typing import Set, List, Dict

# ==================== 路径配置 ====================
SCRIPT_DIR = Path(__file__).parent
BASE_DIR = SCRIPT_DIR.parent
CONFIG_PATH = BASE_DIR / "config" / "my_rules.yaml"
DIST_DIR = BASE_DIR / "dist"

# ==================== 自动获取仓库信息 ====================
def get_repo_info() -> tuple:
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
        owner, name = repo.split("/")
        branch = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=BASE_DIR,
            text=True
        ).strip()
        return owner, name, branch
    except Exception as e:
        print(f"⚠️ 无法自动获取仓库信息，使用默认值: {e}")
        return "SoultionLss", "MyRules", "Rules"

OWNER, REPO_NAME, BRANCH = get_repo_info()
FULL_REPO = f"{OWNER}/{REPO_NAME}"

# ==================== Loyalsoldier 规则源 ====================
# 1. v2ray-rules-dat
V2RAY_BASE = "https://raw.githubusercontent.com/Loyalsoldier/v2ray-rules-dat/release"
V2RAY_SOURCES = {
    "direct-list.txt": "DIRECT",
    "proxy-list.txt": None,
    "reject-list.txt": "REJECT",
}

# 2. surge-rules
SURGE_RULES_BASE = "https://raw.githubusercontent.com/Loyalsoldier/surge-rules/release"
# 映射文件名 -> 策略组
SURGE_RULES_MAP = {
    "apple.txt": "Global",
    "google.txt": "Google",
    "youtube.txt": "YouTube",
    "github.txt": "GitHub",
    "telegram.txt": "Telegram",
    "netflix.txt": "Streaming",
    "disney.txt": "Streaming",
    "primevideo.txt": "Streaming",
    "hbo.txt": "Streaming",
    "hulu.txt": "Streaming",
    "pikpak.txt": "DIRECT",
    "twitter.txt": "Social",
    "instagram.txt": "Social",
    "reddit.txt": "Social",
    "whatsapp.txt": "HongKongSocial",
    "line.txt": "HongKongSocial",
    "tiktok.txt": "TikTok",
    "microsoft.txt": "Microsoft",
}

# ==================== 核心工具函数 ====================

def fetch_domains_from_url(url: str) -> Set[str]:
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    text = resp.text
    domains = set()

    try:
        data = yaml.safe_load(text)
        if isinstance(data, dict) and 'payload' in data:
            items = data['payload']
        elif isinstance(data, list):
            items = data
        else:
            raise ValueError("Unsupported YAML structure")

        for item in items:
            if isinstance(item, str):
                domain = item.strip()
                for prefix in ['DOMAIN,', 'DOMAIN-SUFFIX,']:
                    if domain.startswith(prefix):
                        domain = domain[len(prefix):]
                domain = domain.strip("'").strip('"')
                if domain:
                    domains.add(domain)
    except Exception:
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            for prefix in ['DOMAIN-SUFFIX,', 'DOMAIN,']:
                if line.startswith(prefix):
                    line = line[len(prefix):]
            domain = line.strip("'").strip('"')
            if domain:
                domains.add(domain)

    return domains

def fetch_loyalsoldier_v2ray_list(filename: str) -> Set[str]:
    url = f"{V2RAY_BASE}/{filename}"
    print(f"   📥 拉取 Loyalsoldier/v2ray-rules-dat: {filename}")
    return fetch_domains_from_url(url)

def fetch_loyalsoldier_surge_list(filename: str) -> Set[str]:
    url = f"{SURGE_RULES_BASE}/{filename}"
    print(f"   📥 拉取 Loyalsoldier/surge-rules: {filename}")
    return fetch_domains_from_url(url)

def format_surge_domainset(domains: Set[str]) -> str:
    return '\n'.join(f".{d}" for d in sorted(domains))

def format_clash_yaml(domains: Set[str], policy: str) -> str:
    lines = ["payload:"]
    for d in sorted(domains):
        lines.append(f"  - DOMAIN-SUFFIX,{d},{policy}")
    return '\n'.join(lines)

def format_v2ray_domain_txt(domains: Set[str]) -> str:
    return '\n'.join(sorted(domains))

def parse_rules_yaml(filepath: Path) -> List[Dict]:
    with open(filepath, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)

    rules = []
    for item in data:
        if not isinstance(item, dict):
            continue
        if 'rule_set' in item:
            entry = item['rule_set']
            entry['type'] = 'rule_set'
            rules.append(entry)
    return rules

def extract_repo_name(url: str) -> str:
    if url.startswith("Loyalsoldier:v2ray"):
        return "Loyalsoldier/v2ray-rules-dat"
    if url.startswith("Loyalsoldier:surge"):
        return "Loyalsoldier/surge-rules"

    patterns = [
        r"github\.com/([^/]+/[^/]+)",
        r"raw\.githubusercontent\.com/([^/]+/[^/]+)",
        r"cdn\.jsdelivr\.net/gh/([^/]+/[^/]+)",
        r"gitlab\.com/([^/]+/[^/]+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)

    filename = url.split('/')[-1]
    base = filename.split('.')[0]
    if base.endswith('_Domain'):
        base = base[:-7]
    if base.endswith('_list'):
        base = base[:-5]
    return base

def write_rule_file(file_path: Path, content: str, policy: str, total: int, source_names: list):
    sources = ', '.join(source_names)
    header = [
        "# ============================================================",
        f"# 规则策略: {policy}",
        f"# 规则总数: {total} 条",
        f"# 规则来源: {sources}",
        "# ============================================================",
        ""
    ]
    header_text = '\n'.join(header)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(header_text)
        f.write('\n')
        f.write(content)

def write_readme(policy_dir: Path, policy: str, domains: set, source_names: list):
    total = len(domains)
    sources = ', '.join(source_names)

    base_url_raw = f"https://raw.githubusercontent.com/{FULL_REPO}/{BRANCH}/dist/{policy}"
    base_url_cdn = f"https://cdn.jsdelivr.net/gh/{FULL_REPO}@{BRANCH}/dist/{policy}"

    content = f"""# {policy} 规则集

## 基本信息
- **策略名称**: {policy}
- **规则总数**: {total} 条
- **规则来源**: {sources}

## 文件说明
- `{policy}.list`  → Surge / Loon / Egern 通用（后缀匹配，每行 .domain）
- `{policy}.yaml`  → Clash RULE-SET 格式（payload: 列表）
- `{policy}_domain.txt` → v2ray 纯域名列表（每行一个域名）

## 导入链接

### Surge / Loon / Egern（使用 .list）
Raw 链接: {base_url_raw}/{policy}.list
CDN 加速: {base_url_cdn}/{policy}.list

### Clash（使用 .yaml）
Raw 链接: {base_url_raw}/{policy}.yaml
CDN 加速: {base_url_cdn}/{policy}.yaml

### v2ray（使用 _domain.txt）
Raw 链接: {base_url_raw}/{policy}_domain.txt
CDN 加速: {base_url_cdn}/{policy}_domain.txt

## 使用示例

Surge / Loon / Egern:
在 [Rule] 部分添加：
RULE-SET, {base_url_cdn}/{policy}.list, {policy}

Clash:
在 rules 部分添加：
- RULE-SET, {base_url_cdn}/{policy}.yaml, {policy}

v2ray:
在配置文件中的 "domain" 或 "domains" 字段引用该 txt 文件，或将其内容合并。

## 更新频率
本规则集每日自动更新（北京时间 20:00），确保与上游保持同步。
"""
    readme_path = policy_dir / "README.md"
    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write(content)

# ==================== 主程序 ====================

def main():
    if DIST_DIR.exists():
        print(f"🗑️ 删除旧的 dist 目录: {DIST_DIR}")
        shutil.rmtree(DIST_DIR)
    DIST_DIR.mkdir(parents=True, exist_ok=True)

    print("📖 解析规则配置文件...")
    rules = parse_rules_yaml(CONFIG_PATH)

    groups = defaultdict(list)
    for r in rules:
        if r.get('type') == 'rule_set' and 'match' in r:
            groups[r['policy']].append(r['match'])

    print(f"发现 {len(groups)} 个策略组（来自 my_rules.yaml）")

    # ========== 从 Loyalsoldier/v2ray-rules-dat 拉取 ==========
    print("\n📥 从 Loyalsoldier/v2ray-rules-dat 拉取规则...")
    loyalsoldier_v2ray_domains = {}
    for filename, policy in V2RAY_SOURCES.items():
        if policy is None:
            print(f"   ⏭️ 跳过 {filename}（无预设策略）")
            continue
        try:
            domains = fetch_loyalsoldier_v2ray_list(filename)
            print(f"   ✅ {filename} -> {len(domains)} 条，归入策略: {policy}")
            if policy not in loyalsoldier_v2ray_domains:
                loyalsoldier_v2ray_domains[policy] = set()
            loyalsoldier_v2ray_domains[policy].update(domains)
            groups[policy].append(f"Loyalsoldier:v2ray:{filename}")
        except Exception as e:
            print(f"   ❌ 拉取失败: {filename} - {e}")

    # ========== 从 Loyalsoldier/surge-rules 拉取 ==========
    print("\n📥 从 Loyalsoldier/surge-rules 拉取规则...")
    loyalsoldier_surge_domains = {}
    for filename, policy in SURGE_RULES_MAP.items():
        try:
            domains = fetch_loyalsoldier_surge_list(filename)
            print(f"   ✅ {filename} -> {len(domains)} 条，归入策略: {policy}")
            if policy not in loyalsoldier_surge_domains:
                loyalsoldier_surge_domains[policy] = set()
            loyalsoldier_surge_domains[policy].update(domains)
            groups[policy].append(f"Loyalsoldier:surge:{filename}")
        except Exception as e:
            print(f"   ❌ 拉取失败: {filename} - {e}")

    print(f"\n总共 {len(groups)} 个策略组（含 Loyalsoldier 源）")

    # 处理每个策略组
    for policy, urls in groups.items():
        print(f"\n🔄 处理组: {policy} (共 {len(urls)} 个源)")
        all_domains = set()

        for url in urls:
            if url.startswith("Loyalsoldier:"):
                continue
            try:
                domains = fetch_domains_from_url(url)
                print(f"   ✅ {url} -> {len(domains)} 条")
                all_domains.update(domains)
            except Exception as e:
                print(f"   ❌ 拉取失败: {url} - {e}")

        # 合并 v2ray 域名
        if policy in loyalsoldier_v2ray_domains:
            ls_domains = loyalsoldier_v2ray_domains[policy]
            print(f"   ✅ 合并 Loyalsoldier/v2ray 域名: {len(ls_domains)} 条")
            all_domains.update(ls_domains)

        # 合并 surge 域名
        if policy in loyalsoldier_surge_domains:
            ls_domains = loyalsoldier_surge_domains[policy]
            print(f"   ✅ 合并 Loyalsoldier/surge 域名: {len(ls_domains)} 条")
            all_domains.update(ls_domains)

        if not all_domains:
            print(f"   ⚠️ 无域名，跳过")
            continue

        policy_dir = DIST_DIR / policy
        policy_dir.mkdir(exist_ok=True)

        # 生成来源名称
        source_names = []
        for url in urls:
            if url.startswith("Loyalsoldier:v2ray"):
                source_names.append("Loyalsoldier/v2ray-rules-dat")
            elif url.startswith("Loyalsoldier:surge"):
                source_names.append("Loyalsoldier/surge-rules")
            else:
                repo = extract_repo_name(url)
                source_names.append(repo)
        source_names = list(dict.fromkeys(source_names))

        total = len(all_domains)

        list_content = format_surge_domainset(all_domains)
        list_path = policy_dir / f"{policy}.list"
        write_rule_file(list_path, list_content, policy, total, source_names)
        print(f"   ✅ 生成 Surge/Loon/Egern 规则: {list_path}")

        yaml_content = format_clash_yaml(all_domains, policy)
        yaml_path = policy_dir / f"{policy}.yaml"
        write_rule_file(yaml_path, yaml_content, policy, total, source_names)
        print(f"   ✅ 生成 Clash 规则: {yaml_path}")

        txt_content = format_v2ray_domain_txt(all_domains)
        txt_path = policy_dir / f"{policy}_domain.txt"
        write_rule_file(txt_path, txt_content, policy, total, source_names)
        print(f"   ✅ 生成 v2ray 域名列表: {txt_path}")

        write_readme(policy_dir, policy, all_domains, source_names)
        print(f"   ✅ 生成 README: {policy_dir / 'README.md'}")

    print("\n🎉 所有规则生成完成！")
    print(f"📁 输出目录: {DIST_DIR.absolute()}")

if __name__ == "__main__":
    main()
