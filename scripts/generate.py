#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import shutil
import subprocess
import requests
import yaml
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
    """从 git remote 获取仓库的 owner/name 和当前分支"""
    try:
        # 获取 remote URL
        remote_url = subprocess.check_output(
            ["git", "config", "--get", "remote.origin.url"],
            cwd=BASE_DIR,
            stderr=subprocess.DEVNULL,
            text=True
        ).strip()
        # 解析 URL，支持 https 和 git@ 格式
        if remote_url.startswith("https://"):
            # https://github.com/owner/repo.git
            path = remote_url.replace("https://", "").split("/", 1)[1]
            repo = path.replace(".git", "")
        elif remote_url.startswith("git@"):
            # git@github.com:owner/repo.git
            repo = remote_url.split(":")[1].replace(".git", "")
        else:
            raise ValueError("Unknown remote URL format")
        owner, name = repo.split("/")
        # 获取当前分支
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

# ==================== 核心工具函数 ====================

def fetch_domains_from_url(url: str) -> Set[str]:
    """从任意规则源（支持 YAML、list）提取域名集合"""
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

def format_surge_domainset(domains: Set[str]) -> str:
    return '\n'.join(f".{d}" for d in sorted(domains))

def format_clash_yaml(domains: Set[str], policy: str) -> str:
    lines = ["payload:"]
    for d in sorted(domains):
        lines.append(f"  - DOMAIN-SUFFIX,{d},{policy}")
    return '\n'.join(lines)

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

def extract_source_name(url: str) -> str:
    filename = url.split('/')[-1]
    base = filename.split('.')[0]
    if base.endswith('_Domain'):
        base = base[:-7]
    if base.endswith('_list'):
        base = base[:-5]
    return base

def write_readme(policy_dir: Path, policy: str, domains: set, source_names: list):
    total = len(domains)
    sources = ', '.join(source_names)

    raw_list = f"https://raw.githubusercontent.com/{FULL_REPO}/{BRANCH}/dist/{policy}/{policy}.list"
    cdn_list = f"https://cdn.jsdelivr.net/gh/{FULL_REPO}@{BRANCH}/dist/{policy}/{policy}.list"
    raw_yaml = f"https://raw.githubusercontent.com/{FULL_REPO}/{BRANCH}/dist/{policy}/{policy}.yaml"
    cdn_yaml = f"https://cdn.jsdelivr.net/gh/{FULL_REPO}@{BRANCH}/dist/{policy}/{policy}.yaml"

    content = f"""# {policy} 规则集

## 基本信息
- **策略名称**: {policy}
- **规则总数**: {total} 条
- **规则来源**: {sources}

## 导入方式

### Surge (使用 .list)
- Raw 链接: {raw_list}
- CDN 加速: {cdn_list}

### Clash (使用 .yaml)
- Raw 链接: {raw_yaml}
- CDN 加速: {cdn_yaml}

> 注：Egern 用户也可使用 .yaml，但需自行调整格式（将 payload: 改为 rules:）。

## 使用示例

Surge:
在 [Rule] 部分添加：
RULE-SET, {cdn_list}, {policy}

Clash:
在 rules 部分添加：
- RULE-SET, {cdn_yaml}, {policy}

Egern:
（需将 YAML 中的 payload: 手动改为 rules:）
- rule_set:
    match: {cdn_yaml}
    policy: {policy}

## 更新频率
本规则集每日自动更新（北京时间 20:00），确保与上游保持同步。
"""
    readme_path = policy_dir / "README.md"
    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write(content)

# ==================== 主程序 ====================

def main():
    # 清空旧的 dist
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

    print(f"发现 {len(groups)} 个策略组")

    for policy, urls in groups.items():
        print(f"\n🔄 处理组: {policy} (共 {len(urls)} 个源)")
        all_domains = set()
        for url in urls:
            try:
                domains = fetch_domains_from_url(url)
                print(f"   ✅ {url} -> {len(domains)} 条")
                all_domains.update(domains)
            except Exception as e:
                print(f"   ❌ 拉取失败: {url} - {e}")

        if not all_domains:
            print(f"   ⚠️ 无域名，跳过")
            continue

        policy_dir = DIST_DIR / policy
        policy_dir.mkdir(exist_ok=True)

        source_names = [extract_source_name(url) for url in urls]

        list_path = policy_dir / f"{policy}.list"
        with open(list_path, 'w', encoding='utf-8') as f:
            f.write(format_surge_domainset(all_domains))
        print(f"   ✅ 生成 Surge 规则: {list_path}")

        yaml_path = policy_dir / f"{policy}.yaml"
        with open(yaml_path, 'w', encoding='utf-8') as f:
            f.write(format_clash_yaml(all_domains, policy))
        print(f"   ✅ 生成 Clash 规则: {yaml_path}")

        write_readme(policy_dir, policy, all_domains, source_names)
        print(f"   ✅ 生成 README: {policy_dir / 'README.md'}")

    print("\n🎉 所有规则生成完成！")
    print(f"📁 输出目录: {DIST_DIR.absolute()}")

if __name__ == "__main__":
    main()
