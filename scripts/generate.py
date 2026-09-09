#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import shutil
import subprocess
import requests
import yaml
import re
import json
from pathlib import Path
from collections import defaultdict
from datetime import datetime
from typing import Set, List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from abc import ABC, abstractmethod

# ==================== 路径配置 ====================
SCRIPT_DIR = Path(__file__).parent
BASE_DIR = SCRIPT_DIR.parent
CONFIG_PATH = BASE_DIR / "config" / "my_rules.yaml"
SOURCES_PATH = BASE_DIR / "config" / "sources.yaml"
TEMP_DIR = BASE_DIR / "temp_dist"
FINAL_DIR = BASE_DIR / "dist"
MANIFEST_PATH = BASE_DIR / "merge_manifest.json"   # 新增

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
OWNER = TARGET_REPO.split('/')[0]

# ==================== 从 sources.yaml 加载来源模板 ====================
def infer_name_pattern(url: str) -> str:
    if '{name}' in url:
        return url
    patterns = [
        r'/([A-Z][a-zA-Z0-9_-]+)/([A-Z][a-zA-Z0-9_-]+)\.([a-z]+)$',
        r'/([A-Z][a-zA-Z0-9_-]+)\.([a-z]+)$',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            name = match.group(1)
            result = url.replace(f'/{name}/', '/{name}/')
            result = result.replace(f'/{name}.', '/{name}.')
            if result == url:
                filename = match.group(0)
                result = url.replace(filename, f'/{name}.{match.group(2)}' if '/' in filename else f'{name}.{match.group(2)}')
                result = result.replace(name, '{name}')
            return result
    parts = url.split('/')
    last_part = parts[-1]
    if '.' in last_part:
        name = last_part.split('.')[0]
        if name in url:
            result = url.replace(name, '{name}')
            return result
    print(f"⚠️ 无法从 URL 推断占位符: {url}，将使用原 URL")
    return url

def load_url_templates() -> Dict[str, str]:
    if not SOURCES_PATH.exists():
        print("⚠️ config/sources.yaml 不存在，使用内置默认模板")
        return URL_TEMPLATES_DEFAULT
    try:
        with open(SOURCES_PATH, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        if not isinstance(data, dict):
            print("⚠️ sources.yaml 格式错误，应为字典格式，使用默认模板")
            return URL_TEMPLATES_DEFAULT
        templates = {}
        for key, value in data.items():
            if key.startswith('#'):
                continue
            if not isinstance(value, str):
                continue
            if '{name}' not in value:
                inferred = infer_name_pattern(value)
                templates[key] = inferred
                if inferred != value:
                    print(f"   🔄 自动推断: {key} -> {inferred}")
            else:
                templates[key] = value
        if templates:
            print(f"✅ 从 sources.yaml 加载了 {len(templates)} 个来源模板")
            return templates
        else:
            print("⚠️ sources.yaml 为空，使用默认模板")
            return URL_TEMPLATES_DEFAULT
    except Exception as e:
        print(f"⚠️ 加载 sources.yaml 失败: {e}，使用内置默认模板")
        return URL_TEMPLATES_DEFAULT

URL_TEMPLATES_DEFAULT = {
    "blackmatrix7": "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Surge/{name}/{name}.list",
    "loyalsoldier": "https://raw.githubusercontent.com/Loyalsoldier/surge-rules/release/{name}.txt",
    "acl4ssr": "https://raw.githubusercontent.com/ACL4SSR/ACL4SSR/master/Clash/{name}.list",
    "repcz": "https://cdn.jsdelivr.net/gh/Repcz/Tool@X/Egern/Rules/{name}.yaml",
    "accademia": "https://cdn.jsdelivr.net/gh/Accademia/Additional_Rule_For_Clash@master/GeositeCN/{name}.yaml",
    "repcz_egernrules": "https://raw.githubusercontent.com/Repcz/EgernRules/X/Rules/{name}/{name}.yaml",
}

print("📖 加载规则来源模板...")
URL_TEMPLATES = load_url_templates()
FALLBACK_ORDER = list(URL_TEMPLATES.keys())

def resolve_match(match: str) -> List[str]:
    if match.startswith(('http://', 'https://')):
        return [match]
    if ':' in match:
        source, name = match.split(':', 1)
        source = source.lower()
        if source in URL_TEMPLATES:
            return [URL_TEMPLATES[source].format(name=name)]
        else:
            print(f"⚠️ 未知规则源: {source}，尝试自动回退...")
            return [URL_TEMPLATES[s].format(name=name) for s in FALLBACK_ORDER if s in URL_TEMPLATES]
    else:
        return [URL_TEMPLATES[s].format(name=match) for s in FALLBACK_ORDER if s in URL_TEMPLATES]

def is_valid_domain(domain: str) -> bool:
    if domain.startswith('.'):
        domain = domain[1:]
    if not domain:
        return False
    return bool(re.match(r'^[a-zA-Z0-9-]+(\.[a-zA-Z0-9-]+)*\.[a-zA-Z]{2,}$', domain))

def is_valid_ip_cidr(cidr: str) -> bool:
    if '/' not in cidr:
        return False
    parts = cidr.split('/')
    if len(parts) != 2:
        return False
    ip, mask = parts[0].strip(), parts[1].strip()
    if re.match(r'^(\d{1,3}\.){3}\d{1,3}$', ip):
        try:
            return 0 <= int(mask) <= 32
        except ValueError:
            return False
    if ':' in ip:
        return True
    return False

def parse_rules_line(line: str, domains: Set[str], ip_cidrs: Set[str]):
    """
    解析单行规则，支持：
    1. 单条规则：DOMAIN-SUFFIX,google.com
    2. 空格分隔的多条规则：.a1.mzstatic.com .a2.mzstatic.com
    3. IP-CIDR 规则
    """
    line = line.strip()
    if not line or line.startswith('#'):
        return

    parts = line.split()
    if len(parts) > 1:
        for part in parts:
            parse_rules_line(part, domains, ip_cidrs)
        return

    part = parts[0] if parts else line

    # IP-CIDR
    if part.startswith('IP-CIDR,'):
        sub_parts = part.split(',', 2) if part.count(',') >= 2 else part.split(',', 1)
        if len(sub_parts) >= 2:
            cidr = sub_parts[1].strip()
            if is_valid_ip_cidr(cidr):
                ip_cidrs.add(cidr)
        return

    if part.startswith('IP-CIDR6,'):
        sub_parts = part.split(',', 2) if part.count(',') >= 2 else part.split(',', 1)
        if len(sub_parts) >= 2:
            cidr = sub_parts[1].strip()
            if is_valid_ip_cidr(cidr):
                ip_cidrs.add(cidr)
        return

    # 域名规则（DOMAIN, DOMAIN-SUFFIX, 或纯域名）
    if part.startswith('DOMAIN,') or part.startswith('DOMAIN-SUFFIX,'):
        domain = part.split(',', 1)[1].split(',')[0].strip("'").strip('"')
        if is_valid_domain(domain):
            domains.add(domain)
        return

    # 纯域名（如 .a1.mzstatic.com）
    if '#' in part:
        part = part.split('#')[0].strip()
    if not part:
        return

    if part.startswith('.'):
        part = part[1:]

    if is_valid_domain(part):
        domains.add(part)

def fetch_rules_from_url(url: str) -> Tuple[Set[str], Set[str], bool]:
    """
    从 URL 下载规则，返回 (域名集合, IP-CIDR 集合, 是否成功)
    支持 YAML、每行一条、空格分隔三种格式
    """
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
    try:
        resp = requests.get(url, timeout=30, headers=headers)
        resp.raise_for_status()
        text = resp.text
    except Exception as e:
        print(f"   ❌ 下载失败: {url} - {e}")
        return set(), set(), False

    domains = set()
    ip_cidrs = set()

    try:
        data = yaml.safe_load(text)
        if isinstance(data, dict) and 'payload' in data:
            items = data['payload']
            for item in items:
                if isinstance(item, str):
                    parse_rules_line(item, domains, ip_cidrs)
            if domains or ip_cidrs:
                return domains, ip_cidrs, True
        elif isinstance(data, list):
            for item in data:
                if isinstance(item, str):
                    parse_rules_line(item, domains, ip_cidrs)
            if domains or ip_cidrs:
                return domains, ip_cidrs, True
    except Exception:
        pass

    for line in text.splitlines():
        parse_rules_line(line, domains, ip_cidrs)

    if not domains and not ip_cidrs:
        print(f"   ⚠️ 未能提取到有效规则: {url}")
        return set(), set(), False

    return domains, ip_cidrs, True

def normalize_domains(domains: List[str]) -> List[str]:
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
        if d and is_valid_domain(d):
            cleaned.append(d)
    seen = set()
    result = []
    for d in cleaned:
        if d not in seen:
            seen.add(d)
            result.append(d)
    return result

def normalize_ip_cidrs(ip_cidrs: List[str]) -> List[str]:
    cleaned = []
    for c in ip_cidrs:
        c = c.strip()
        if not c:
            continue
        if '#' in c:
            c = c.split('#')[0].strip()
        if is_valid_ip_cidr(c):
            cleaned.append(c)
    seen = set()
    result = []
    for c in cleaned:
        if c not in seen:
            seen.add(c)
            result.append(c)
    return result

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

# ==================== 中间数据结构 ====================
@dataclass
class RuleSet:
    policy: str
    domains: List[str]
    ip_cidrs: List[str]
    total_domains: int
    total_ip_cidrs: int
    source_count: int
    sources: List[str]
    updated_at: str
    owner: str

    @property
    def total(self) -> int:
        return self.total_domains + self.total_ip_cidrs

@dataclass
class SourceData:
    name: str
    policy: str
    domains: Set[str]
    ip_cidrs: Set[str]
    sources: List[str]
    url: str

# ==================== 序列化器基类 ====================
class Serializer(ABC):
    @abstractmethod
    def get_extension(self) -> str:
        pass
    @abstractmethod
    def serialize(self, rule_set: RuleSet) -> str:
        pass
    @abstractmethod
    def get_import_example(self, policy: str, base_url: str) -> str:
        pass

# ==================== 各平台序列化器 ====================
class SurgeSerializer(Serializer):
    def get_extension(self) -> str:
        return ".list"
    def serialize(self, rule_set: RuleSet) -> str:
        lines = []
        for d in sorted(rule_set.domains):
            if d.startswith('.'):
                d = d[1:]
            lines.append(f".{d}")
        for cidr in sorted(rule_set.ip_cidrs):
            lines.append(f"IP-CIDR,{cidr},{rule_set.policy}")
        return "\n".join(lines)
    def get_import_example(self, policy: str, base_url: str) -> str:
        return f"RULE-SET, {base_url}/{policy}.list, {policy}"

class LoonSerializer(Serializer):
    def get_extension(self) -> str:
        return ".list"
    def serialize(self, rule_set: RuleSet) -> str:
        lines = []
        for d in sorted(rule_set.domains):
            lines.append(f"DOMAIN-SUFFIX,{d},{rule_set.policy}")
        for cidr in sorted(rule_set.ip_cidrs):
            lines.append(f"IP-CIDR,{cidr},{rule_set.policy}")
        return "\n".join(lines)
    def get_import_example(self, policy: str, base_url: str) -> str:
        return f"RULE-SET, {base_url}/{policy}.list, {policy}"

class ClashSerializer(Serializer):
    def get_extension(self) -> str:
        return ".yaml"
    def serialize(self, rule_set: RuleSet) -> str:
        lines = ["payload:"]
        for d in sorted(rule_set.domains):
            lines.append(f"  - DOMAIN-SUFFIX,{d},{rule_set.policy}")
        for cidr in sorted(rule_set.ip_cidrs):
            lines.append(f"  - IP-CIDR,{cidr},{rule_set.policy}")
        return "\n".join(lines)
    def get_import_example(self, policy: str, base_url: str) -> str:
        return f"- RULE-SET, {base_url}/{policy}.yaml, {policy}"

# ==================== 修改：EgernSerializer 使用原生格式 ====================
class EgernSerializer(Serializer):
    def get_extension(self) -> str:
        return ".yaml"
    def serialize(self, rule_set: RuleSet) -> str:
        lines = []
        # 添加 no_resolve（如果有任何规则）
        if rule_set.domains or rule_set.ip_cidrs:
            lines.append("no_resolve: true")
            lines.append("")
        # domain_suffix_set
        if rule_set.domains:
            lines.append("domain_suffix_set:")
            for d in sorted(rule_set.domains):
                if d.startswith('.'):
                    d = d[1:]
                lines.append(f"- {d}")
            lines.append("")
        # ip_cidr_set
        if rule_set.ip_cidrs:
            lines.append("ip_cidr_set:")
            for cidr in sorted(rule_set.ip_cidrs):
                lines.append(f"- {cidr}")
        # 如果没有规则，输出占位
        if not lines:
            lines.append("domain_suffix_set:")
            lines.append("  # 无有效规则，请替换")
            lines.append("- example.com")
        return "\n".join(lines)
    def get_import_example(self, policy: str, base_url: str) -> str:
        return f"- rule_set:\n    match: {base_url}/{policy}.yaml\n    policy: {policy}"

class V2raySerializer(Serializer):
    def get_extension(self) -> str:
        return "_domain.txt"
    def serialize(self, rule_set: RuleSet) -> str:
        return "\n".join(sorted(rule_set.domains))
    def get_import_example(self, policy: str, base_url: str) -> str:
        return f"在配置文件的 'domain' 或 'domains' 字段引用 {base_url}/{policy}_domain.txt"

class QuantumultXSerializer(Serializer):
    def get_extension(self) -> str:
        return ".list"
    def serialize(self, rule_set: RuleSet) -> str:
        lines = []
        for d in sorted(rule_set.domains):
            lines.append(f"HOST-SUFFIX,{d},{rule_set.policy}")
        for cidr in sorted(rule_set.ip_cidrs):
            lines.append(f"IP-CIDR,{cidr},{rule_set.policy}")
        return "\n".join(lines)
    def get_import_example(self, policy: str, base_url: str) -> str:
        return f"RULE-SET, {base_url}/{policy}.list, {policy}"

class SingboxSerializer(Serializer):
    def get_extension(self) -> str:
        return ".json"
    def serialize(self, rule_set: RuleSet) -> str:
        data = {"version": 1, "rules": []}
        if rule_set.domains:
            data["rules"].append({"domain_suffix": sorted(rule_set.domains)})
        if rule_set.ip_cidrs:
            data["rules"].append({"ip_cidr": sorted(rule_set.ip_cidrs)})
        return json.dumps(data, indent=2, ensure_ascii=False)
    def get_import_example(self, policy: str, base_url: str) -> str:
        return f"在 route.rules 中引用: {{ 'rule_set': '{base_url}/{policy}.json' }}"

SERIALIZERS = {
    "Surge": SurgeSerializer(),
    "Loon": LoonSerializer(),
    "Clash": ClashSerializer(),
    "Egern": EgernSerializer(),
    "v2ray": V2raySerializer(),
    "QuantumultX": QuantumultXSerializer(),
    "Singbox": SingboxSerializer(),
}

# ==================== 头部注释生成 ====================
def build_header(rule_set: RuleSet) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        "# ============================================================",
        f"# 规则策略: {rule_set.policy}",
        f"# 域名规则总数: {rule_set.total_domains} 条",
        f"# IP-CIDR 规则总数: {rule_set.total_ip_cidrs} 条",
        f"# 规则来源条目总数: {rule_set.source_count} 条",
        f"# 规则来源: {', '.join(rule_set.sources)}",
        f"# 作者: {rule_set.owner}",
        f"# 最后更新: {now}",
        "# ============================================================",
        ""
    ]
    return '\n'.join(lines)

# ==================== 生成单个平台的规则文件 ====================
def generate_platform_files(platform_name: str, serializer: Serializer,
                           merged_groups: Dict[str, RuleSet],
                           separate_sources: Dict[str, SourceData],
                           output_root: Path):
    platform_dir = output_root / platform_name
    platform_dir.mkdir(parents=True, exist_ok=True)

    # 1. 生成独立文件
    for raw_name, src_data in separate_sources.items():
        if '://' in raw_name or raw_name.startswith('/'):
            import os
            base = os.path.basename(raw_name)
            source_name = base.split('.')[0] if '.' in base else base
        else:
            source_name = raw_name

        policy = src_data.policy
        strategy_dir = platform_dir / policy
        strategy_dir.mkdir(exist_ok=True)

        domain_list = sorted(src_data.domains)
        ip_cidr_list = sorted(src_data.ip_cidrs)
        rule_set = RuleSet(
            policy=policy,
            domains=domain_list,
            ip_cidrs=ip_cidr_list,
            total_domains=len(domain_list),
            total_ip_cidrs=len(ip_cidr_list),
            source_count=len(src_data.sources),
            sources=src_data.sources,
            updated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            owner=OWNER
        )

        filename = f"{source_name}{serializer.get_extension()}"
        file_path = strategy_dir / filename
        content = serializer.serialize(rule_set)
        # Egern 格式不需要头部注释（但其他平台保留）
        if platform_name == "Egern":
            full_content = content
        else:
            full_content = build_header(rule_set) + "\n" + content
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(full_content)

    # 2. 生成合并文件
    for policy, rule_set in merged_groups.items():
        strategy_dir = platform_dir / policy
        strategy_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{policy}{serializer.get_extension()}"
        file_path = strategy_dir / filename
        content = serializer.serialize(rule_set)
        if platform_name == "Egern":
            full_content = content
        else:
            full_content = build_header(rule_set) + "\n" + content
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(full_content)

    return platform_dir

# ==================== 生成平台 README ====================
def write_platform_readme(platform_dir: Path, merged_groups: Dict[str, RuleSet],
                         separate_sources: Dict[str, SourceData], platform: str):
    lines = [
        f"# {platform} 规则集",
        "",
        "本目录包含以下策略组的规则文件。",
        "",
        "## 策略组列表",
        ""
    ]
    for policy in sorted(merged_groups.keys()):
        lines.append(f"### {policy}")
        lines.append("")
        ext = SERIALIZERS[platform].get_extension()
        merged_file = f"{policy}{ext}"
        lines.append(f"- 合并文件: `{merged_file}`")
        independent = []
        for name, src in separate_sources.items():
            if src.policy == policy:
                if '://' in name or name.startswith('/'):
                    import os
                    base = os.path.basename(name)
                    display_name = base.split('.')[0] if '.' in base else base
                else:
                    display_name = name
                independent.append(display_name)
        if independent:
            lines.append("- 独立文件:")
            for name in sorted(independent):
                lines.append(f"  - `{name}{ext}`")
        lines.append("")
    lines.append("## 使用方式")
    lines.append("在客户端配置中按需引用对应文件，推荐顺序：独立文件优先，合并文件兜底。")
    lines.append("")
    lines.append("## 更新频率")
    lines.append("本规则集每日自动更新（北京时间 20:00）。")

    readme_path = platform_dir / "README.md"
    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

# ==================== 主程序 ====================
def main():
    if TEMP_DIR.exists():
        shutil.rmtree(TEMP_DIR)
    TEMP_DIR.mkdir(parents=True, exist_ok=True)

    print("\n📖 解析规则配置文件...")
    rules = parse_rules_yaml(CONFIG_PATH)

    group_domains = defaultdict(set)
    group_ip_cidrs = defaultdict(set)
    group_sources = defaultdict(set)
    separate_data = {}

    for rule in rules:
        if rule.get('type') != 'rule_set' or 'match' not in rule:
            continue
        policy = rule['policy']
        match_str = rule['match']
        separate = rule.get('separate', False)

        possible_urls = resolve_match(match_str)
        if not possible_urls:
            print(f"⚠️ 无法解析: {match_str}，跳过")
            continue

        domains = set()
        ip_cidrs = set()
        success_urls = []
        for url in possible_urls:
            d, c, ok = fetch_rules_from_url(url)
            if ok:
                domains.update(d)
                ip_cidrs.update(c)
                success_urls.append(url)
                break

        if not domains and not ip_cidrs:
            print(f"❌ 规则源 {match_str} 完全失败，跳过")
            continue

        normalized_domains = normalize_domains(list(domains))
        normalized_ip_cidrs = normalize_ip_cidrs(list(ip_cidrs))

        if not normalized_domains and not normalized_ip_cidrs:
            print(f"❌ 规则源 {match_str} 清洗后无有效规则，跳过")
            continue

        group_domains[policy].update(normalized_domains)
        group_ip_cidrs[policy].update(normalized_ip_cidrs)
        for url in success_urls:
            group_sources[policy].add(extract_source_path(url))

        if separate:
            if ':' in match_str:
                _, name = match_str.split(':', 1)
            else:
                import os
                base = os.path.basename(match_str)
                name = base.split('.')[0] if '.' in base else base

            if name in separate_data:
                separate_data[name].domains.update(normalized_domains)
                separate_data[name].ip_cidrs.update(normalized_ip_cidrs)
                separate_data[name].sources.extend([extract_source_path(u) for u in success_urls])
            else:
                separate_data[name] = SourceData(
                    name=name,
                    policy=policy,
                    domains=set(normalized_domains),
                    ip_cidrs=set(normalized_ip_cidrs),
                    sources=[extract_source_path(u) for u in success_urls],
                    url=match_str
                )

    merged_groups = {}
    for policy in group_domains.keys():
        domain_list = sorted(group_domains[policy])
        ip_cidr_list = sorted(group_ip_cidrs[policy])
        sources = sorted(group_sources[policy])
        merged_groups[policy] = RuleSet(
            policy=policy,
            domains=domain_list,
            ip_cidrs=ip_cidr_list,
            total_domains=len(domain_list),
            total_ip_cidrs=len(ip_cidr_list),
            source_count=len(sources),
            sources=sources,
            updated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            owner=OWNER
        )

    for platform_name, serializer in SERIALIZERS.items():
        print(f"\n📦 生成 {platform_name} 平台规则...")
        platform_dir = TEMP_DIR / platform_name
        generate_platform_files(platform_name, serializer, merged_groups, separate_data, TEMP_DIR)
        write_platform_readme(platform_dir, merged_groups, separate_data, platform_name)
        print(f"   ✅ {platform_name} 规则生成完成")

    # ==================== 新增：生成 merge_manifest.json ====================
    # 构建 manifest（即使没有规则也生成空文件）
    manifest = {
        "version": "1.0",
        "generated_at": datetime.now().isoformat(),
        "platforms": list(SERIALIZERS.keys()),
        "merges": {},   # 后续可扩展合并功能
        "independents": {}
    }
    # 记录独立源信息（如果有）
    for src_name, src in separate_data.items():
        manifest["independents"][src_name] = {"policy": src.policy}
    with open(MANIFEST_PATH, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    print(f"✅ 生成 merge_manifest.json")

    if FINAL_DIR.exists():
        print(f"\n🗑️ 删除旧的 dist 目录: {FINAL_DIR}")
        shutil.rmtree(FINAL_DIR)
    shutil.copytree(TEMP_DIR, FINAL_DIR)
    print(f"✅ 原子性替换完成: {TEMP_DIR} -> {FINAL_DIR}")

    shutil.rmtree(TEMP_DIR)

    print("\n🎉 所有规则生成完成！")
    print(f"📁 输出目录: {FINAL_DIR.absolute()}")
    print(f"📊 策略组数量: {len(merged_groups)}")
    print(f"📊 独立源数量: {len(separate_data)}")

if __name__ == "__main__":
    main()
