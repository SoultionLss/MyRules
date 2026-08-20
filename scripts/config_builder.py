#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
配置文件生成器（基于 Egern 核心模板生成 Surge / Loon / Clash / Egern 模板）
- 读取 templates/Egern.yaml（Egern 核心配置，不含脚本/模块）
- 提取策略组（policy_groups）和规则（rules）结构
- 生成各平台完整配置文件，规则部分引用 dist/ 中的规则集
- 自动从 git 获取仓库信息，生成 CDN 链接
- 输出到 dist/{平台}/Rules/ 目录，与规则文件并列
"""

import os
import subprocess
import yaml
import shutil
from pathlib import Path

# ==================== 路径配置 ====================
SCRIPT_DIR = Path(__file__).parent
BASE_DIR = SCRIPT_DIR.parent
TEMPLATE_DIR = BASE_DIR / "templates"
EGERN_TEMPLATE = TEMPLATE_DIR / "Egern.yaml"
DIST_DIR = BASE_DIR / "dist"

# ==================== 自动获取仓库信息 ====================
def get_repo_info():
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

OWNER, REPO, BRANCH = get_repo_info()
FULL_REPO = f"{OWNER}/{REPO}"

# ==================== 工具函数 ====================
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
                url = f"{cdn_base}/Surge/Rules/{policy}/{policy}.list"
                refs.append(f"RULE-SET, {url}, {policy}")
            elif platform == 'Clash':
                url = f"{cdn_base}/Clash/Rules/{policy}/{policy}.yaml"
                refs.append(f"  - RULE-SET, {url}, {policy}")
            elif platform == 'Egern':
                url = f"{cdn_base}/Egern/Rules/{policy}/{policy}.yaml"
                refs.append(f"  - rule_set:\n      match: {url}\n      policy: {policy}")
    return refs

def get_target_repo_info():
    """从环境变量获取目标仓库信息，用于生成正确的链接"""
    target_repo = os.environ.get("TARGET_REPO")
    target_branch = os.environ.get("TARGET_BRANCH")
    if target_repo and target_branch:
        return target_repo, target_branch
    return FULL_REPO, BRANCH

# ==================== 主函数 ====================
def main():
    print("📖 读取 Egern 核心模板 (templates/Egern.yaml)...")
    if not EGERN_TEMPLATE.exists():
        print("❌ 未找到 templates/Egern.yaml，请先创建该文件。")
        print("   提示：从您提供的 Soultion.yaml 剔除 scriptings 和 modules 部分后保存。")
        return

    egern_data = load_yaml(EGERN_TEMPLATE)
    policy_groups = egern_data.get('policy_groups')
    rules = egern_data.get('rules')

    if policy_groups is None:
        print("❌ templates/Egern.yaml 中缺少 'policy_groups' 部分，请检查文件内容。")
        return
    if rules is None:
        print("❌ templates/Egern.yaml 中缺少 'rules' 部分，请检查文件内容。")
        return

    # 获取目标仓库信息（用于生成引用链接）
    target_repo, target_branch = get_target_repo_info()
    cdn_base = f"https://cdn.jsdelivr.net/gh/{target_repo}@{target_branch}"

    # ---------- 1. 生成 Surge 配置（放到 dist/Surge/Rules/） ----------
    print("🔄 生成 Surge 配置...")
    surge_dir = DIST_DIR / "Surge" / "Rules"
    surge_dir.mkdir(parents=True, exist_ok=True)

    surge_lines = []
    surge_lines.append("# ============================================================")
    surge_lines.append("# Surge 配置文件（由 config_builder 生成）")
    surge_lines.append("# 请将代理节点填入 [Proxy] 部分，策略组已定义好。")
    surge_lines.append(f"# 仓库: https://github.com/{target_repo}")
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

    surge_path = surge_dir / "Surge.conf"
    with open(surge_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(surge_lines))
    print(f"   ✅ Surge 配置已生成: {surge_path}")

    # ---------- 2. 生成 Loon 配置（放到 dist/Loon/Rules/） ----------
    print("🔄 生成 Loon 配置...")
    loon_dir = DIST_DIR / "Loon" / "Rules"
    loon_dir.mkdir(parents=True, exist_ok=True)

    loon_lines = []
    loon_lines.append("# ============================================================")
    loon_lines.append("# Loon 配置文件（由 config_builder 生成）")
    loon_lines.append("# 请将代理节点填入 [Proxy] 部分，策略组已定义好。")
    loon_lines.append(f"# 仓库: https://github.com/{target_repo}")
    loon_lines.append("# ============================================================")
    loon_lines.append("")
    loon_lines.append("[General]")
    loon_lines.append("bypass-tun = 192.168.0.0/16, 10.0.0.0/8, 172.16.0.0/12")
    loon_lines.append("dns-server = 223.5.5.5, 119.29.29.29")
    loon_lines.append("")
    loon_lines.append("[Proxy]")
    loon_lines.append("# 在此填写您的代理节点")
    loon_lines.append("")
    loon_lines.append("[Proxy Group]")
    for group in policy_groups:
        if 'select' in group:
            g = group['select']
            name = g['name']
            policies = g['policies']
            policies_str = ', '.join(policies) if isinstance(policies, list) else str(policies)
            loon_lines.append(f"{name} = select, {policies_str}")
        elif 'fallback' in group:
            g = group['fallback']
            name = g['name']
            policies = g['policies']
            policies_str = ', '.join(policies)
            loon_lines.append(f"{name} = fallback, {policies_str}")
        elif 'auto_test' in group:
            g = group['auto_test']
            name = g['name']
            policies = g['policies']
            policies_str = ', '.join(policies)
            loon_lines.append(f"{name} = url-test, {policies_str}, url = http://1.1.1.1/generate_204, interval = 600")
    loon_lines.append("")
    loon_lines.append("[Rule]")
    refs_loon = build_rule_refs(rules, 'Loon', cdn_base)
    loon_lines.extend(refs_loon)
    loon_lines.append("FINAL, Proxy")

    loon_path = loon_dir / "Loon.conf"
    with open(loon_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(loon_lines))
    print(f"   ✅ Loon 配置已生成: {loon_path}")

    # ---------- 3. 生成 Clash 配置（放到 dist/Clash/Rules/） ----------
    print("🔄 生成 Clash 配置...")
    clash_dir = DIST_DIR / "Clash" / "Rules"
    clash_dir.mkdir(parents=True, exist_ok=True)

    providers = {}
    for rule in rules:
        if 'rule_set' in rule:
            entry = rule['rule_set']
            policy = entry['policy']
            if entry.get('disabled', False):
                continue
            url = f"{cdn_base}/Clash/Rules/{policy}/{policy}.yaml"
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

    clash_path = clash_dir / "Clash.yaml"
    dump_yaml(clash_data, clash_path)
    print(f"   ✅ Clash 配置已生成: {clash_path}")

    # ---------- 4. 复制 Egern 模板到 dist/Egern/Rules/（并更新引用） ----------
    print("🔄 生成 Egern 配置...")
    egern_dir = DIST_DIR / "Egern" / "Rules"
    egern_dir.mkdir(parents=True, exist_ok=True)

    # 读取原始 Egern 模板
    egern_output = load_yaml(EGERN_TEMPLATE)

    # 更新规则中的引用链接（替换为 target_repo 的链接）
    # 注意：这里只处理 rule_set 中的 match 链接
    updated_rules = []
    for rule in egern_output.get('rules', []):
        if 'rule_set' in rule:
            entry = rule['rule_set']
            if 'match' in entry and 'cdn.jsdelivr.net' in entry['match']:
                # 保留原链接，不强制替换（用户可自行决定）
                pass
        updated_rules.append(rule)
    egern_output['rules'] = updated_rules

    egern_path = egern_dir / "Egern.yaml"
    dump_yaml(egern_output, egern_path)
    print(f"   ✅ Egern 配置已生成: {egern_path}")

    print("\n🎉 所有配置文件模板生成完成！")
    print("📁 生成的文件：")
    print(f"   - {surge_path}")
    print(f"   - {loon_path}")
    print(f"   - {clash_path}")
    print(f"   - {egern_path}")

if __name__ == "__main__":
    main()
