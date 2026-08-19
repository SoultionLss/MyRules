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
LOYALSOLDIER_BASE = "https://raw.githubusercontent.com/Loyalsoldier/v2ray-rules-dat/release"
LOYALSOLDIER_SOURCES = {
    "direct-list.txt": "DIRECT",
    "proxy-list.txt": None,      # 不预设策略，由用户决定
    "reject-list.txt": "REJECT",
}

# ==================== 核心工具函数 ====================

def fetch_domains_from_url(url: str) -> Set[str]:
    """从任意规则源（支持 YAML、list、txt）提取域名集合"""
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    text = resp.text
    domains = set()

    # 尝试 YAML 解析
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
        # 按行解析（.list 或 .txt 格式）
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

def fetch_loyalsoldier_list(filename: str) -> Set[str]:
    """从 Loyalsoldier 仓库拉取文本规则列表"""
    url = f"{LOYALSOLDIER_BASE}/{filename}"
    print(f"   📥 拉取 Loyalsoldier: {filename}")
    return fetch_domains_from_url(url)

def format_surge_domainset(domains: Set[str]) -> str:
    """Surge / Loon / Egern 后缀匹配列表，每行 .domain"""
    return '\n'.join(f".{d}" for d in sorted(domains))

def format_clash_yaml(domains: Set[str], policy: str) -> str:
    """Clash RULE-SET YAML 格式（payload: 列表）"""
    lines = ["payload:"]
    for d in sorted(domains):
        lines.append(f"  - DOMAIN-SUFFIX,{d},{policy}")
    return '\n'.join(lines)

def format_v2ray_domain_txt(domains: Set[str]) -> str:
    """v2ray 纯域名列表，每行一个域名，不带前缀"""
    return '\n'.join(sorted(domains))

def parse_rules_yaml(filepath: Path) -> List[Dict]:
    """解析 config/my_rules.yaml，返回规则条目列表（仅处理 rule_set）"""
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
    """从 URL 中提取简洁的来源名称"""
    filename = url.split('/')[-1]
    base = filename.split('.')[0]
    if base.endswith('_Domain'):
        base = base[:-7]
    if base.endswith('_list'):
        base = base[:-5]
    return base

def write_readme(policy_dir: Path, policy: str, domains: set, source_names: list):
    """生成 README.md，包含所有平台的导入链接（纯文本，无代码块）"""
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
    # 清空旧的 dist
    if DIST_DIR.exists():
        print(f"🗑️ 删除旧的 dist 目录: {DIST_DIR}")
        shutil.rmtree(DIST_DIR)
    DIST_DIR.mkdir(parents=True, exist_ok=True)

    print("📖 解析规则配置文件...")
    rules = parse_rules_yaml(CONFIG_PATH)

    # 按策略分组（从 my_rules.yaml 中读取）
    groups = defaultdict(list)
    for r in rules:
        if r.get('type') == 'rule_set' and 'match' in r:
            groups[r['policy']].append(r['match'])

    print(f"发现 {len(groups)} 个策略组（来自 my_rules.yaml）")

    # ========== 新增：从 Loyalsoldier 仓库拉取规则 ==========
    print("\n📥 从 Loyalsoldier/v2ray-rules-dat 拉取规则...")
    for filename, policy in LOYALSOLDIER_SOURCES.items():
        if policy is None:
            print(f"   ⏭️ 跳过 {filename}（无预设策略）")
            continue
        try:
            domains = fetch_loyalsoldier_list(filename)
            print(f"   ✅ {filename} -> {len(domains)} 条，归入策略: {policy}")
            # 将域名合并到对应策略组
            groups[policy].append(f"Loyalsoldier: {filename}")
            # 同时存储域名供后续合并使用
            if not hasattr(main, '_loyalsoldier_domains'):
                main._loyalsoldier_domains = {}
            main._loyalsoldier_domains[policy] = domains
        except Exception as e:
            print(f"   ❌ 拉取失败: {filename} - {e}")

    print(f"\n总共 {len(groups)} 个策略组（含 Loyalsoldier）")

    # 处理每个策略组
    for policy, urls in groups.items():
        print(f"\n🔄 处理组: {policy} (共 {len(urls)} 个源)")
        all_domains = set()

        # 处理常规 URL 源
        for url in urls:
            # 如果是 Loyalsoldier 标记，跳过（已单独处理）
            if url.startswith("Loyalsoldier:"):
                continue
            try:
                domains = fetch_domains_from_url(url)
                print(f"   ✅ {url} -> {len(domains)} 条")
                all_domains.update(domains)
            except Exception as e:
                print(f"   ❌ 拉取失败: {url} - {e}")

        # 合并 Loyalsoldier 域名
        if hasattr(main, '_loyalsoldier_domains') and policy in main._loyalsoldier_domains:
            ls_domains = main._loyalsoldier_domains[policy]
            print(f"   ✅ 合并 Loyalsoldier 域名: {len(ls_domains)} 条")
            all_domains.update(ls_domains)

        if not all_domains:
            print(f"   ⚠️ 无域名，跳过")
            continue

        policy_dir = DIST_DIR / policy
        policy_dir.mkdir(exist_ok=True)

        # 生成来源名称列表（仅显示短名称）
        source_names = []
        for url in urls:
            if url.startswith("Loyalsoldier:"):
                source_names.append("Loyalsoldier")
            else:
                source_names.append(extract_source_name(url))

        # 去重来源名称
        source_names = list(dict.fromkeys(source_names))

        # 1. Surge / Loon / Egern .list
        list_path = policy_dir / f"{policy}.list"
        with open(list_path, 'w', encoding='utf-8') as f:
            f.write(format_surge_domainset(all_domains))
        print(f"   ✅ 生成 Surge/Loon/Egern 规则: {list_path}")

        # 2. Clash .yaml
        yaml_path = policy_dir / f"{policy}.yaml"
        with open(yaml_path, 'w', encoding='utf-8') as f:
            f.write(format_clash_yaml(all_domains, policy))
        print(f"   ✅ 生成 Clash 规则: {yaml_path}")

        # 3. v2ray 纯域名 .txt
        txt_path = policy_dir / f"{policy}_domain.txt"
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(format_v2ray_domain_txt(all_domains))
        print(f"   ✅ 生成 v2ray 域名列表: {txt_path}")

        # 4. README.md
        write_readme(policy_dir, policy, all_domains, source_names)
        print(f"   ✅ 生成 README: {policy_dir / 'README.md'}")

    print("\n🎉 所有规则生成完成！")
    print(f"📁 输出目录: {DIST_DIR.absolute()}")

if __name__ == "__main__":
    main()
