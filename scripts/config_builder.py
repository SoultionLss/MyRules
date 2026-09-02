#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
配置文件生成器
功能：
1. 读取 merge_manifest.json 获取合并关系和独立源
2. 读取 templates/Egern.yaml 作为骨架模板
3. 为各平台生成主配置文件，输出到仓库二对应平台根目录
"""

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

    # 提取策略组定义（供各平台转换使用）
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

        # 生成配置内容
        if platform in ["Surge", "Loon", "QuantumultX"]:
            # INI 格式
            content = generate_ini_config(platform, base_config, policy_groups, config["rule_refs"])
            # 直接输出到 dist/{platform}/ 目录
            output_dir = DIST_DIR / platform
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / output_file
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"   ✅ 生成 {platform} 配置: {output_path}")

        elif platform == "Clash":
            # Clash YAML 格式
            refs, providers = config["rule_refs"]
            content = generate_clash_config(base_config, policy_groups, refs, providers)
            output_dir = DIST_DIR / platform
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / output_file
            dump_yaml(content, output_path)
            print(f"   ✅ 生成 {platform} 配置: {output_path}")

        elif platform == "Egern":
            # Egern YAML 格式
            refs = config["rule_refs"]
            content = generate_egern_config(base_config, policy_groups, refs)
            output_dir = DIST_DIR / platform
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / output_file
            dump_yaml(content, output_path)
            print(f"   ✅ 生成 {platform} 配置: {output_path}")

        elif platform == "Singbox":
            # Sing-box JSON 格式
            refs, rule_sets = config["rule_refs"]
            content = generate_singbox_config(base_config, policy_groups, refs, rule_sets)
            output_dir = DIST_DIR / platform
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / output_file
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(content, f, indent=2, ensure_ascii=False)
            print(f"   ✅ 生成 {platform} 配置: {output_path}")

        elif platform == "v2ray":
            # v2ray JSON 格式
            refs = config["rule_refs"]
            content = generate_v2ray_config(base_config, policy_groups, refs)
            output_dir = DIST_DIR / platform
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / output_file
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(content, f, indent=2, ensure_ascii=False)
            print(f"   ✅ 生成 {platform} 配置: {output_path}")

    print("\n🎉 所有平台配置文件生成完成！")


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
        # 默认配置
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

    # 转换策略组
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
    # 合并基础配置
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
    # 合并基础配置
    for key, value in base_config.items():
        if key not in ['rules', 'policy_groups']:
            data[key] = value
    return data


if __name__ == "__main__":
    main()
