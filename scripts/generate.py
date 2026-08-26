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
from dataclasses import dataclass
from abc import ABC, abstractmethod

# ==================== 路径配置 ====================
SCRIPT_DIR = Path(__file__).parent
BASE_DIR = SCRIPT_DIR.parent
CONFIG_PATH = BASE_DIR / "config" / "my_rules.yaml"
TEMP_DIR = BASE_DIR / "temp_dist"   # 临时构建目录（原子性替换）
FINAL_DIR = BASE_DIR / "dist"       # 最终输出目录

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

# ==================== 规则源 URL 模板 ====================
URL_TEMPLATES = {
    "blackmatrix7": "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Surge/{name}/{name}.list",
    "loyalsoldier": "https://raw.githubusercontent.com/Loyalsoldier/surge-rules/release/{name}.txt",
    "acl4ssr": "https://raw.githubusercontent.com/ACL4SSR/ACL4SSR/master/Clash/{name}.list",
    "repcz": "https://cdn.jsdelivr.net/gh/Repcz/Tool@X/Egern/Rules/{name}.yaml",
    "accademia": "https://cdn.jsdelivr.net/gh/Accademia/Additional_Rule_For_Clash@master/GeositeCN/{name}.yaml",
    "repcz_egernrules": "https://raw.githubusercontent.com/Repcz/EgernRules/X/Rules/{name}/{name}.yaml",
}

# 自动回退顺序
FALLBACK_ORDER = ["blackmatrix7", "loyalsoldier", "acl4ssr", "repcz", "accademia", "repcz_egernrules"]

def resolve_match(match: str) -> List[str]:
    """
    解析规则匹配值，返回一个 URL 列表（用于自动回退）。
    如果 match 是完整 URL，直接返回单元素列表。
    如果是 "source:name"，返回该来源的 URL。
    如果是纯名称，尝试所有来源模板，返回所有可能的 URL（按 FALLBACK_ORDER 顺序）。
    """
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
        # 纯名称，尝试所有来源
        return [URL_TEMPLATES[s].format(name=match) for s in FALLBACK_ORDER if s in URL_TEMPLATES]

def is_valid_domain(domain: str) -> bool:
    """简单的域名格式过滤，只允许标准域名和泛域名（以 . 开头）"""
    if domain.startswith('.'):
        domain = domain[1:]
    if not domain:
        return False
    return bool(re.match(r'^[a-zA-Z0-9-]+(\.[a-zA-Z0-9-]+)*\.[a-zA-Z]{2,}$', domain))

def fetch_domains_from_url(url: str) -> Tuple[Set[str], bool]:
    """尝试下载并解析域名，返回 (域名集合, 是否成功)"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        resp = requests.get(url, timeout=30, headers=headers)
        resp.raise_for_status()
        text = resp.text
    except Exception as e:
        print(f"   ❌ 下载失败: {url} - {e}")
        return set(), False

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
                if domain and is_valid_domain(domain):
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
            if domain and is_valid_domain(domain):
                domains.add(domain)

    if not domains:
        print(f"   ⚠️ 未能提取到有效域名: {url}")
        return set(), False

    return domains, True

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
    total: int
    source_count: int
    sources: List[str]
    updated_at: str
    owner: str

# ==================== 序列化器基类 ====================
class Serializer(ABC):
    """序列化器基类 - 每个平台一个实现"""
    
    @abstractmethod
    def get_extension(self) -> str:
        """返回文件扩展名（含点，如 .list）"""
        pass
    
    @abstractmethod
    def serialize(self, rule_set: RuleSet) -> str:
        """将 RuleSet 序列化为目标格式的纯规则内容"""
        pass
    
    @abstractmethod
    def get_import_example(self, policy: str, base_url: str) -> str:
        """
        返回导入示例。
        base_url 格式: https://cdn.jsdelivr.net/gh/owner/repo@branch/Platform
        """
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
        return "\n".join(lines)
    
    def get_import_example(self, policy: str, base_url: str) -> str:
        return f"RULE-SET, {base_url}/{policy}.list, {policy}"

class LoonSerializer(Serializer):
    """Loon 规则集（.list，DOMAIN-SUFFIX 格式）"""
    def get_extension(self) -> str:
        return ".list"
    
    def serialize(self, rule_set: RuleSet) -> str:
        lines = []
        for d in sorted(rule_set.domains):
            lines.append(f"DOMAIN-SUFFIX,{d},{rule_set.policy}")
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
        return "\n".join(lines)
    
    def get_import_example(self, policy: str, base_url: str) -> str:
        return f"- RULE-SET, {base_url}/{policy}.yaml, {policy}"

class EgernSerializer(Serializer):
    def get_extension(self) -> str:
        return ".yaml"
    
    def serialize(self, rule_set: RuleSet) -> str:
        lines = ["rules:"]
        for d in sorted(rule_set.domains):
            lines.append(f"  - domain_suffix: {d}")
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
    """Quantumult X 规则集（.list，HOST-SUFFIX 格式）"""
    def get_extension(self) -> str:
        return ".list"
    
    def serialize(self, rule_set: RuleSet) -> str:
        lines = []
        for d in sorted(rule_set.domains):
            lines.append(f"HOST-SUFFIX,{d},{rule_set.policy}")
        return "\n".join(lines)
    
    def get_import_example(self, policy: str, base_url: str) -> str:
        return f"RULE-SET, {base_url}/{policy}.list, {policy}"

class SingboxSerializer(Serializer):
    """
    Sing-box 官方 rule_set JSON 格式
    参考: https://sing-box.sagernet.org/configuration/route/rule-set/
    """
    def get_extension(self) -> str:
        return ".json"
    
    def serialize(self, rule_set: RuleSet) -> str:
        # 官方格式: {"version": 1, "rules": [{"domain_suffix": [...]}]}
        data = {
            "version": 1,
            "rules": [
                {
                    "domain_suffix": sorted(rule_set.domains)
                }
            ]
        }
        return json.dumps(data, indent=2, ensure_ascii=False)
    
    def get_import_example(self, policy: str, base_url: str) -> str:
        return f"在 route.rules 中引用: {{ 'rule_set': '{base_url}/{policy}.json' }}"

# ==================== 序列化器注册表 ====================
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
        f"# 规则总数: {rule_set.total} 条",
        f"# 规则来源条目总数: {rule_set.source_count} 条",
        f"# 规则来源: {', '.join(rule_set.sources)}",
        f"# 作者: {rule_set.owner}",
        f"# 最后更新: {now}",
        "# ============================================================",
        ""
    ]
    return '\n'.join(lines)

# ==================== 平台 README 生成 ====================
def write_platform_readme(platform_dir: Path, rule_set: RuleSet, platform: str, base_url: str):
    """为每个平台目录生成 README.md（扁平化，只生成一个总 README）"""
    serializer = SERIALIZERS[platform]
    ext = serializer.get_extension()
    filename = f"{rule_set.policy}{ext}"
    
    content = f"""# {platform} 规则集

## 基本信息
- **策略名称**: {rule_set.policy}
- **规则总数**: {rule_set.total} 条
- **规则来源条目总数**: {rule_set.source_count} 条
- **规则来源**: {', '.join(rule_set.sources)}

## 导入链接

### Raw 链接
https://raw.githubusercontent.com/{TARGET_REPO}/{TARGET_BRANCH}/{platform}/{filename}

### CDN 加速
{base_url}/{filename}

## 使用示例

### {platform}
{serializer.get_import_example(rule_set.policy, base_url)}

## 更新频率
本规则集每日自动更新（北京时间 20:00）。
"""
    readme_path = platform_dir / "README.md"
    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write(content)

# ==================== 主程序 ====================
def main():
    # 1. 清空并重建临时目录（原子性构建）
    if TEMP_DIR.exists():
        shutil.rmtree(TEMP_DIR)
    TEMP_DIR.mkdir(parents=True, exist_ok=True)

    print("📖 解析规则配置文件...")
    rules = parse_rules_yaml(CONFIG_PATH)
    groups = defaultdict(list)
    for r in rules:
        if r.get('type') == 'rule_set' and 'match' in r:
            original = r['match']
            possible_urls = resolve_match(original)
            if len(possible_urls) > 1:
                print(f"   🔄 自动回退已启用: {original} -> 将尝试 {len(possible_urls)} 个来源")
            groups[r['policy']].extend(possible_urls)

    print(f"发现 {len(groups)} 个策略组")

    # 存储成功构建的策略组
    success_groups = {}
    failed_groups = []

    for policy, urls in groups.items():
        print(f"\n🔄 处理组: {policy} (共 {len(urls)} 个候选URL)")
        all_domains = set()
        successful_urls = []
        failed_urls = []

        for url in urls:
            domains_ok, ok = fetch_domains_from_url(url)
            if ok:
                print(f"   ✅ 成功: {url} -> {len(domains_ok)} 条")
                all_domains.update(domains_ok)
                successful_urls.append(url)
            else:
                failed_urls.append(url)

        if not all_domains:
            print(f"   ❌ 策略组 {policy} 完全失败（尝试了 {len(urls)} 个来源）")
            failed_groups.append(policy)
            continue

        if failed_urls:
            print(f"   ⚠️ 部分失败: {len(failed_urls)}/{len(urls)} 个来源失败，但已从其他来源获取数据")

        # 标准化域名
        normalized = normalize_domains(list(all_domains))
        if not normalized:
            print(f"   ❌ 策略组 {policy} 清洗后无有效域名")
            failed_groups.append(policy)
            continue

        # 构建来源信息
        source_info = []
        for url in successful_urls:
            source_info.append(extract_source_path(url))
        source_info = list(dict.fromkeys(source_info))

        rule_set = RuleSet(
            policy=policy,
            domains=normalized,
            total=len(normalized),
            source_count=len(source_info),
            sources=source_info,
            updated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            owner=OWNER
        )
        success_groups[policy] = rule_set

    # 2. 检查是否有任何成功组
    if not success_groups:
        print("❌ 没有任何策略组成功生成规则，工作流将失败")
        shutil.rmtree(TEMP_DIR)
        raise RuntimeError("No rules generated")

    if failed_groups:
        print(f"⚠️ 以下策略组失败，将使用旧版本（如果有）: {', '.join(failed_groups)}")

    # 3. 生成规则文件到临时目录（扁平化结构）
    for policy, rule_set in success_groups.items():
        print(f"\n📝 生成策略组: {policy} (规则总数: {rule_set.total})")
        
        for platform_name, serializer in SERIALIZERS.items():
            # 扁平化路径: temp_dist/Platform/Policy.ext
            platform_dir = TEMP_DIR / platform_name
            platform_dir.mkdir(parents=True, exist_ok=True)

            # 生成规则内容
            content = serializer.serialize(rule_set)
            header = build_header(rule_set)
            full_content = header + "\n" + content

            filename = f"{policy}{serializer.get_extension()}"
            file_path = platform_dir / filename
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(full_content)
            
            # 生成 README（每个平台目录只生成一个总 README）
            base_url = f"https://cdn.jsdelivr.net/gh/{TARGET_REPO}@{TARGET_BRANCH}/{platform_name}"
            write_platform_readme(platform_dir, rule_set, platform_name, base_url)

        print(f"   ✅ 组 {policy} 已生成所有平台文件（扁平化）")

    # 4. 原子性替换：将 TEMP_DIR 的内容覆盖到 FINAL_DIR
    if FINAL_DIR.exists():
        print(f"🗑️ 删除旧的 dist 目录: {FINAL_DIR}")
        shutil.rmtree(FINAL_DIR)
    
    # 复制临时目录到最终目录
    shutil.copytree(TEMP_DIR, FINAL_DIR)
    print(f"✅ 原子性替换完成: {TEMP_DIR} -> {FINAL_DIR}")

    # 5. 清理临时目录
    shutil.rmtree(TEMP_DIR)

    print("\n🎉 所有规则生成完成！")
    print(f"📁 输出目录: {FINAL_DIR.absolute()}")
    print(f"📊 成功策略组: {', '.join(success_groups.keys())}")
    if failed_groups:
        print(f"⚠️ 失败策略组（未更新）: {', '.join(failed_groups)}")

if __name__ == "__main__":
    main()
