#!/usr/bin/env python3
"""
将 Accademia/Additional_Rule_For_Clash 的 ChinaMax.yaml
转换为 Surge / Egern 支持的格式
"""
import requests

RAW_URL = "https://raw.githubusercontent.com/Accademia/Additional_Rule_For_Clash/main/ChinaMax/ChinaMax.yaml"

def fetch_rules():
    resp = requests.get(RAW_URL, timeout=30)
    resp.raise_for_status()
    lines = resp.text.splitlines()

    domains = []
    suffixes = []

    for line in lines:
        line = line.strip()
        if line.startswith('DOMAIN,'):
            domain = line.split(',', 1)[1].strip()
            if domain:
                domains.append(domain)
        elif line.startswith('DOMAIN-SUFFIX,'):
            suffix = line.split(',', 1)[1].strip()
            if suffix:
                suffixes.append(suffix)

    return domains, suffixes

def write_surge_domain_set(domains, suffixes, filename="ChinaMax_domain_set.txt"):
    with open(filename, 'w') as f:
        f.write("# ChinaMax 规则集 - Surge DOMAIN-SET\n")
        f.write("# 精确匹配\n")
        for d in domains:
            f.write(f"{d}\n")
        f.write("\n# 后缀匹配（带 . 前缀）\n")
        for s in suffixes:
            f.write(f".{s}\n")
    print(f"✅ Surge DOMAIN-SET 已保存到 {filename}")

def write_surge_rule_set(domains, suffixes, filename="ChinaMax_rule_set.list"):
    with open(filename, 'w') as f:
        f.write("# ChinaMax 规则集 - Surge RULE-SET\n")
        for d in domains:
            f.write(f"DOMAIN,{d}\n")
        for s in suffixes:
            f.write(f"DOMAIN-SUFFIX,{s}\n")
    print(f"✅ Surge RULE-SET 已保存到 {filename}")

def write_egern_yaml(domains, suffixes, filename="ChinaMax_egern.yaml"):
    with open(filename, 'w') as f:
        f.write("# ChinaMax 规则集 - Egern YAML\n")
        f.write("rules:\n")
        for d in domains:
            f.write(f"  - domain: {d}\n")
        for s in suffixes:
            f.write(f"  - domain_suffix: {s}\n")
    print(f"✅ Egern YAML 已保存到 {filename}")

def main():
    print("📥 正在下载 ChinaMax.yaml ...")
    try:
        domains, suffixes = fetch_rules()
    except Exception as e:
        print(f"❌ 下载失败: {e}")
        return

    print(f"   精确匹配: {len(domains)} 条")
    print(f"   后缀匹配: {len(suffixes)} 条")

    write_surge_domain_set(domains, suffixes)
    write_surge_rule_set(domains, suffixes)
    write_egern_yaml(domains, suffixes)
    print("🎉 所有转换完成！")

if __name__ == "__main__":
    main()
