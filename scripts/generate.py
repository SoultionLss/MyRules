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
}

def resolve_match(match: str) -> str:
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
        return URL_TEMPLATES["blackmatrix7"].format(name=match)

# ==================== 规范化清洗函数 ====================
def normalize_domains(domains: List[str]) -> List[str]:
    """通用域名清洗：去空格、注释、后缀、去重、小写"""
    cleaned = []
    for d in domains:
        d = d.strip()
        if not d:
            continue
        if '#' in d:
            d = d.split('#')[0].strip()
        d = d.rstrip(',;')
        d = d.lower()
        for prefix in ['http://', 'https://']:
            if d.startswith(prefix):
                d = d[len(prefix):]
        if '/' in d:
            d = d.split('/')[0]
        if d:
            cleaned.append(d)
    seen = set()
    result = []
    for d in cleaned:
        if d not in seen:
            seen.add(d)
            result.append(d)
    return result

def clean_surge_domainset(domains: List[str]) -> str:
    """Surge DOMAIN-SET 格式：每行 .domain"""
    cleaned = []
    for d in domains:
        if d.startswith('.'):
            d = d[1:]
        for prefix in ['DOMAIN,', 'DOMAIN-SUFFIX,']:
            if d.startswith(prefix):
                d = d[len(prefix):]
        if ',' in d:
            d = d.split(',')[0]
        d = d.strip().lower()
        if d and not d.startswith('#'):
            cleaned.append(f".{d}")
    # 去重
    seen = set()
    result = []
    for d in cleaned:
        if d not in seen:
            seen.add(d)
            result.append(d)
    return '\n'.join(result)

def clean_clash_yaml(domains: List[str], policy: str) -> str:
    """Clash RULE-SET YAML (payload:)"""
    cleaned = []
    for d in domains:
        for prefix in ['DOMAIN,', 'DOMAIN-SUFFIX,', 'DOMAIN-KEYWORD,']:
            if d.startswith(prefix):
                d = d[len(prefix):]
        if ',' in d:
            d = d.split(',')[0]
        d = d.strip().lower()
        if d and not d.startswith('#'):
            cleaned.append(d)
    seen = set()
    result = []
    for d in cleaned:
        if d not in seen:
            seen.add(d)
            result.append(d)
    lines = ["payload:"]
    for d in sorted(result):
        lines.append(f"  - DOMAIN-SUFFIX,{d},{policy}")
    return '\n'.join(lines)

def clean_egern_yaml(domains: List[str]) -> str:
    """Egern RULE-SET YAML (rules:)"""
    cleaned = []
    for d in domains:
        for prefix in ['DOMAIN,', 'DOMAIN-SUFFIX,']:
            if d.startswith(prefix):
                d = d[len(prefix):]
        if ',' in d:
            d = d.split(',')[0]
        d = d.strip().lower()
        if d and not d.startswith('#'):
            cleaned.append(d)
    seen = set()
    result = []
    for d in cleaned:
        if d not in seen:
            seen.add(d)
            result.append(d)
    lines = ["rules:"]
    for d in sorted(result):
        lines.append(f"  - domain_suffix: {d}")
    return '\n'.join(lines)

def clean_v2ray_txt(domains: List[str]) -> str:
    """v2ray 纯域名列表（保留特殊前缀）"""
    cleaned = []
    for d in domains:
        d = d.strip()
        if not d or d.startswith('#'):
            continue
        # 保留特殊前缀
        has_prefix = False
        for prefix in ['domain:', 'full:', 'keyword:', 'regexp:']:
            if d.lower().startswith(prefix):
                has_prefix = True
                break
        if not has_prefix:
            for prefix in ['DOMAIN,', 'DOMAIN-SUFFIX,']:
                if d.startswith(prefix):
                    d = d[len(prefix):]
            if ',' in d:
                d = d.split(',')[0]
            d = d.lower()
        if d:
            cleaned.append(d)
    seen = set()
    result = []
    for d in cleaned:
        if d not in seen:
            seen.add(d)
            result.append(d)
    return '\n'.join(result)

# ==================== 拉取函数 ====================
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

def extract_source_path(url: str) -> str:
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

# ==================== 解析 my_rules.yaml ====================
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

# ==================== 生成平台特定 README ====================
def write_platform_readme(platform_dir: Path, policy: str, domains: set, source_info: list, source_count: int, platform: str):
    """为指定平台生成 README.md"""
    total = len(domains)
    sources = ', '.join(source_info)
    base_raw = f"https://raw.githubusercontent.com/{FULL_REPO}/{BRANCH}/dist/{platform}/Rules/{policy}"
    base_cdn = f"https://cdn.jsdelivr.net/gh/{FULL_REPO}@{BRANCH}/dist/{platform}/Rules/{policy}"

    # 文件扩展名根据平台不同
    ext_map = {
        "Surge": ".list",
        "Clash": ".yaml",
        "Egern": ".yaml",
        "v2ray": "_domain.txt"
    }
    ext = ext_map.get(platform, ".list")
    filename = f"{policy}{ext}"

    content = f"""# {policy} 规则集（{platform} 平台）

## 基本信息
- **策略名称**: {policy}
- **规则总数**: {total} 条
- **规则来源条目总数**: {source_count} 条
- **规则来源**: {sources}

## 文件说明
- `{filename}` → {platform} 专用规则文件

## 导入链接

### Raw 链接
{base_raw}/{filename}

### CDN 加速
{base_cdn}/{filename}

## 使用示例

### {platform}
"""
    if platform == "Surge" or platform == "Loon":
        content += f"RULE-SET, {base_cdn}/{filename}, {policy}"
    elif platform == "Clash":
        content += f"- RULE-SET, {base_cdn}/{filename}, {policy}"
    elif platform == "Egern":
        content += f"- rule_set:\n    match: {base_cdn}/{filename}\n    policy: {policy}"
    elif platform == "v2ray":
        content += f"在配置文件的 'domain' 或 'domains' 字段引用该 txt 文件。"

    content += f"""

## 更新频率
本规则集每日自动更新（北京时间 20:00），确保与上游保持同步。
"""
    readme_path = platform_dir / "README.md"
    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write(content)

# ==================== 主程序 ====================
def main():
    # 清空旧 dist
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

    print(f"发现 {len(groups)} 个策略组")

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

        # 提取来源信息
        source_info = []
        for url in successful_urls:
            source_info.append(extract_source_path(url))
        source_info = list(dict.fromkeys(source_info))
        source_count = len(source_info)

        # 转换为列表并清洗
        domain_list = list(all_domains)
        normalized = normalize_domains(domain_list)

        # 平台配置
        platforms = {
            "Surge": {"ext": ".list", "formatter": clean_surge_domainset, "extra_args": []},
            "Clash": {"ext": ".yaml", "formatter": clean_clash_yaml, "extra_args": [policy]},
            "Egern": {"ext": ".yaml", "formatter": clean_egern_yaml, "extra_args": []},
            "v2ray": {"ext": "_domain.txt", "formatter": clean_v2ray_txt, "extra_args": []},
        }

        for plat, cfg in platforms.items():
            # 创建平台子目录
            platform_dir = DIST_DIR / plat / "Rules" / policy
            platform_dir.mkdir(parents=True, exist_ok=True)

            # 生成规则文件
            if cfg["extra_args"]:
                content = cfg["formatter"](normalized, *cfg["extra_args"])
            else:
                content = cfg["formatter"](normalized)
            filename = f"{policy}{cfg['ext']}"
            file_path = platform_dir / filename
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"   ✅ 生成 {plat} 规则: {file_path}")

            # 生成对应平台的 README
            write_platform_readme(platform_dir, policy, set(normalized), source_info, source_count, plat)

    print("\n🎉 所有规则生成完成！")
    print(f"📁 输出目录: {DIST_DIR.absolute()}")

if __name__ == "__main__":
    main()
