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

# ==================== 规则源 URL 模板（简写自动补全） ====================
URL_TEMPLATES = {
    "blackmatrix7": "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Surge/{name}/{name}.list",
    "loyalsoldier": "https://raw.githubusercontent.com/Loyalsoldier/surge-rules/release/{name}.txt",
    "acl4ssr": "https://raw.githubusercontent.com/ACL4SSR/ACL4SSR/master/Clash/{name}.list",
    "repcz": "https://raw.githubusercontent.com/Repcz/EgernRules/X/Rules/{name}/{name}.yaml",
    "accademia": "https://cdn.jsdelivr.net/gh/Accademia/Additional_Rule_For_Clash@master/GeositeCN/{name}.yaml",
    # 需要新增规则源时，在此添加一行即可，格式: "source": "template_url_with_{name}"
}

def resolve_match(match: str) -> str:
    """
    解析规则匹配值：
      - 若为完整 URL (http/https)，原样返回。
      - 若包含 ':'，按 "source:name" 格式解析，用 URL_TEMPLATES 补全。
      - 若不包含 ':'，视为名称，默认使用 blackmatrix7 补全。
    """
    if match.startswith(('http://', 'https://')):
        return match

    if ':' in match:
        source, name = match.split(':', 1)
        source = source.lower()
        if source in URL_TEMPLATES:
            return URL_TEMPLATES[source].format(name=name)
        else:
            print(f"⚠️ 未知规则源: {source}，原样保留: {match}")
            return match
    else:
        # 未指定来源，默认用 blackmatrix7
        return URL_TEMPLATES["blackmatrix7"].format(name=match)

# ==================== 核心工具函数 ====================

def fetch_domains_from_url(url: str) -> Set[str]:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    resp = requests.get(url, timeout=30, headers=headers)
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

def extract_source_path(url: str) -> str:
    """
    从规则源 URL 中提取可读的路径标识，格式: owner/repo@branch/path/to/file
    """
    if url.startswith('https://'):
        url = url[8:]

    if url.startswith('raw.githubusercontent.com/'):
        parts = url.split('/', 3)
        if len(parts) >= 4:
            return f"{parts[1]}/{parts[2]}@{parts[3]}"

    if url.startswith('cdn.jsdelivr.net/gh/'):
        parts = url.split('/', 3)
        if len(parts) >= 4:
            return parts[3]

    return url

def write_rule_file(file_path: Path, content: str, policy: str, total_domains: int, source_info: list, source_count: int):
    sources = ', '.join(source_info)
    header = [
        "# ============================================================",
        f"# 规则策略: {policy}",
        f"# 规则总数: {total_domains} 条",
        f"# 规则来源条目总数: {source_count} 条",
        f"# 规则来源: {sources}",
        "# ============================================================",
        ""
    ]
    header_text = '\n'.join(header)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(header_text)
        f.write('\n')
        f.write(content)

def write_readme(policy_dir: Path, policy: str, domains: set, source_info: list, source_count: int):
    total = len(domains)
    sources = ', '.join(source_info)

    base_url_raw = f"https://raw.githubusercontent.com/{FULL_REPO}/{BRANCH}/dist/{policy}"
    base_url_cdn = f"https://cdn.jsdelivr.net/gh/{FULL_REPO}@{BRANCH}/dist/{policy}"

    content = f"""# {policy} 规则集

## 基本信息
- **策略名称**: {policy}
- **规则总数**: {total} 条
- **规则来源条目总数**: {source_count} 条
- **规则来源**: {sources}

## 文件说明
- `{policy}.list`  → Surge / Loon / Egern 通用（后缀匹配，每行 .domain）
- `{policy}.yaml`  → Clash RULE-SET 格式（payload: 列表）
- `{policy}_domain.txt` → v2ray 纯域名列表（每行一个域名）

## 导入链接

### Surge / Loon / Egern（使用 .list）
- Raw 链接: {base_url_raw}/{policy}.list
- CDN 加速: {base_url_cdn}/{policy}.list

### Clash（使用 .yaml）
- Raw 链接: {base_url_raw}/{policy}.yaml
- CDN 加速: {base_url_cdn}/{policy}.yaml

### v2ray（使用 _domain.txt）
- Raw 链接: {base_url_raw}/{policy}_domain.txt
- CDN 加速: {base_url_cdn}/{policy}_domain.txt

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
            original = r['match']
            resolved = resolve_match(original)
            if original != resolved:
                print(f"   🔄 简写映射: {original} -> {resolved}")
            groups[r['policy']].append(resolved)

    print(f"发现 {len(groups)} 个策略组（来自 my_rules.yaml）")

    for policy, urls in groups.items():
        print(f"\n🔄 处理组: {policy} (共 {len(urls)} 个源)")
        all_domains = set()
        successful_urls = []

        for url in urls:
            try:
                domains = fetch_domains_from_url(url)
                print(f"   ✅ {url} -> {len(domains)} 条")
                all_domains.update(domains)
                successful_urls.append(url)
            except Exception as e:
                print(f"   ❌ 拉取失败: {url} - {e}")

        if not all_domains:
            print(f"   ⚠️ 无域名，跳过")
            continue

        policy_dir = DIST_DIR / policy
        policy_dir.mkdir(exist_ok=True)

        # 生成来源信息
        source_info = []
        for url in successful_urls:
            source_info.append(extract_source_path(url))
        source_info = list(dict.fromkeys(source_info))
        source_count = len(source_info)

        total_domains = len(all_domains)

        # 1. Surge / Loon / Egern .list
        list_content = format_surge_domainset(all_domains)
        list_path = policy_dir / f"{policy}.list"
        write_rule_file(list_path, list_content, policy, total_domains, source_info, source_count)
        print(f"   ✅ 生成 Surge/Loon/Egern 规则: {list_path}")

        # 2. Clash .yaml
        yaml_content = format_clash_yaml(all_domains, policy)
        yaml_path = policy_dir / f"{policy}.yaml"
        write_rule_file(yaml_path, yaml_content, policy, total_domains, source_info, source_count)
        print(f"   ✅ 生成 Clash 规则: {yaml_path}")

        # 3. v2ray 纯域名 .txt
        txt_content = format_v2ray_domain_txt(all_domains)
        txt_path = policy_dir / f"{policy}_domain.txt"
        write_rule_file(txt_path, txt_content, policy, total_domains, source_info, source_count)
        print(f"   ✅ 生成 v2ray 域名列表: {txt_path}")

        # 4. README.md
        write_readme(policy_dir, policy, all_domains, source_info, source_count)
        print(f"   ✅ 生成 README: {policy_dir / 'README.md'}")

    print("\n🎉 所有规则生成完成！")
    print(f"📁 输出目录: {DIST_DIR.absolute()}")

if __name__ == "__main__":
    main()
