#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import subprocess
import yaml
import shutil
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
BASE_DIR = SCRIPT_DIR.parent
TEMPLATE_DIR = BASE_DIR / "templates"
EGERN_TEMPLATE = TEMPLATE_DIR / "Egern.yaml"
DIST_DIR = BASE_DIR / "dist"

def get_repo_info():
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
        owner, name = repo.split("/")
        branch = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=BASE_DIR,
            text=True
        ).strip()
        return repo, branch
    except Exception as e:
        print(f"⚠️ 无法获取仓库信息，使用默认值: {e}")
        return "SoultionLss/MyRules", "main"

TARGET_REPO, TARGET_BRANCH = get_repo_info()

def load_yaml(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def dump_yaml(data, filepath):
    with open(filepath, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, allow_unicode=True, sort_keys=False, indent=2)

def build_rule_refs(rules, platform, cdn_base):
    refs = []
    for rule in rules:
        if 'rule_set' in rule:
            entry = rule['rule_set']
            policy = entry['policy']
            if entry.get('disabled', False):
                continue
            if platform == 'Surge' or platform == 'Loon':
                url = f"{cdn_base}/Surge/{policy}.list"
                refs.append(f"RULE-SET, {url}, {policy}")
            elif platform == 'Clash':
                url = f"{cdn_base}/Clash/{policy}.yaml"
                refs.append(f"  - RULE-SET, {url}, {policy}")
            elif platform == 'Egern':
                url = f"{cdn_base}/Egern/{policy}.yaml"
                refs.append(f"  - rule_set:\n      match: {url}\n      policy: {policy}")
    return refs

def main():
    print("📖 读取 Egern 核心模板 (templates/Egern.yaml)...")
    if not EGERN_TEMPLATE.exists():
        print("❌ 未找到 templates/Egern.yaml，跳过配置生成")
        return

    egern_data = load_yaml(EGERN_TEMPLATE)
    policy_groups = egern_data.get('policy_groups')
    rules = egern_data.get('rules')

    if policy_groups is None or rules is None:
        print("❌ templates/Egern.yaml 缺少 policy_groups 或 rules，跳过")
        return

    cdn_base = f"https://cdn.jsdelivr.net/gh/{TARGET_REPO}@{TARGET_BRANCH}"

    # Surge
    surge_dir = DIST_DIR / "Surge"
    surge_dir.mkdir(parents=True, exist_ok=True)
    surge_lines = []
    surge_lines.append("# ============================================================")
    surge_lines.append("# Surge 配置文件（由 config_builder 生成）")
    surge_lines.append(f"# 仓库: https://github.com/{TARGET_REPO}")
    surge_lines.append("# ============================================================")
    surge_lines.append("")
    surge_lines.append("[General]")
    surge_lines.append("skip-proxy = 127.0.0.1, 192.168.0.0/16, 10.0.0.0/8, 172.16.0.0/12, 100.64.0.0/10, localhost, *.local")
    surge_lines.append("bypass-tun = 192.168.0.0/16, 10.0.0.0/8, 172.16.0.0/12")
    surge_lines.append("dns-server = 223.5.5.5, 119.29.29.29")
    surge_lines.append("")
    surge_lines.append("[Proxy]")
    surge_lines.append("# 在此填写您的代理节点")
    surge_lines.append("")
    surge_lines.append("[Proxy Group]")
    for group in policy_groups:
        if 'select' in group:
            g = group['select']
            name = g['name']
            policies = g['policies']
            if isinstance(policies, list):
                policies_str = ', '.join(policies)
            else:
                policies_str = str(policies)
            surge_lines.append(f"{name} = select, {policies_str}")
        elif 'fallback' in group:
            g = group['fallback']
            name = g['name']
            policies = g['policies']
            policies_str = ', '.join(policies)
            surge_lines.append(f"{name} = fallback, {policies_str}")
        elif 'auto_test' in group:
            g = group['auto_test']
            name = g['name']
            policies = g['policies']
            policies_str = ', '.join(policies)
            surge_lines.append(f"{name} = url-test, {policies_str}, url = http://1.1.1.1/generate_204, interval = 600")
    surge_lines.append("")
    surge_lines.append("[Rule]")
    refs = build_rule_refs(rules, 'Surge', cdn_base)
    surge_lines.extend(refs)
    surge_lines.append("FINAL, Proxy")
    with open(surge_dir / "Surge.conf", 'w', encoding='utf-8') as f:
        f.write('\n'.join(surge_lines))
    print("   ✅ Surge 主配置已生成")

    # Clash
    clash_dir = DIST_DIR / "Clash"
    clash_dir.mkdir(parents=True, exist_ok=True)
    providers = {}
    for rule in rules:
        if 'rule_set' in rule:
            entry = rule['rule_set']
            policy = entry['policy']
            if entry.get('disabled', False):
                continue
            url = f"{cdn_base}/Clash/{policy}.yaml"
            providers[policy] = {
                "type": "http",
                "url": url,
                "interval": 86400,
                "behavior": "classical"
            }
    clash_rules = []
    for rule in rules:
        if 'rule_set' in rule:
            policy = rule['rule_set']['policy']
            if rule['rule_set'].get('disabled', False):
                continue
            clash_rules.append(f"  - RULE-SET, {policy}, {policy}")
    clash_data = {
        "mode": "rule",
        "log-level": "info",
        "ipv6": False,
        "allow-lan": False,
        "external-controller": "127.0.0.1:9090",
        "proxies": [],
        "proxy-groups": [],
        "rule-providers": providers,
        "rules": clash_rules + ["  - MATCH, PROXY"]
    }
    proxy_groups = []
    for group in policy_groups:
        if 'select' in group:
            g = group['select']
            proxy_groups.append({
                "name": g['name'],
                "type": "select",
                "proxies": g['policies']
            })
        elif 'fallback' in group:
            g = group['fallback']
            proxy_groups.append({
                "name": g['name'],
                "type": "fallback",
                "proxies": g['policies']
            })
        elif 'auto_test' in group:
            g = group['auto_test']
            proxy_groups.append({
                "name": g['name'],
                "type": "url-test",
                "proxies": g['policies'],
                "url": "http://1.1.1.1/generate_204",
                "interval": 600
            })
    clash_data["proxy-groups"] = proxy_groups
    dump_yaml(clash_data, clash_dir / "Clash.yaml")
    print("   ✅ Clash 主配置已生成")

    # Egern
    egern_dir = DIST_DIR / "Egern"
    egern_dir.mkdir(parents=True, exist_ok=True)
    # 更新规则引用
    updated_rules = []
    for rule in rules:
        if 'rule_set' in rule:
            entry = rule['rule_set']
            policy = entry['policy']
            if entry.get('disabled', False):
                continue
            # 替换为 CDN 链接（扁平化）
            entry['match'] = f"{cdn_base}/Egern/{policy}.yaml"
            updated_rules.append(rule)
        else:
            updated_rules.append(rule)
    egern_data['rules'] = updated_rules
    dump_yaml(egern_data, egern_dir / "Egern.yaml")
    print("   ✅ Egern 主配置已生成")

    # Loon 与 Surge 类似，也可生成（可选）
    loon_dir = DIST_DIR / "Loon"
    loon_dir.mkdir(parents=True, exist_ok=True)
    # 简单复制 Surge 配置并修改文件名（Loon 与 Surge 高度兼容）
    shutil.copy(surge_dir / "Surge.conf", loon_dir / "Loon.conf")
    # 替换规则引用中的 Surge 为 Loon（但我们的规则文件是共享的，所以不改）
    print("   ✅ Loon 主配置已生成（基于 Surge 模板）")

    print("🎉 所有主配置文件生成完成！")

if __name__ == "__main__":
    main()
