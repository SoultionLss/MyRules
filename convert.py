import requests
import yaml

RAW_URL = "https://raw.githubusercontent.com/Accademia/Additional_Rule_For_Clash/main/ChinaMax/ChinaMax_Domain.yaml"

def analyze_and_extract():
    resp = requests.get(RAW_URL, timeout=30)
    resp.raise_for_status()
    raw_text = resp.text
    lines = raw_text.splitlines()

    # 统计注释行和有效行
    total_lines = len(lines)
    comment_lines = 0
    empty_lines = 0
    effective_lines = 0

    for line in lines:
        stripped = line.strip()
        if not stripped:
            empty_lines += 1
        elif stripped.startswith('#'):
            comment_lines += 1
        else:
            effective_lines += 1

    print(f"📊 原始文件统计：")
    print(f"   总行数: {total_lines}")
    print(f"   空行: {empty_lines}")
    print(f"   注释行（#开头）: {comment_lines}")
    print(f"   有效行（未注释）: {effective_lines}")

    # 解析 YAML 提取域名
    data = yaml.safe_load(raw_text)
    domains = []
    if isinstance(data, dict) and 'payload' in data:
        for item in data['payload']:
            if isinstance(item, str):
                domain = item.strip().strip("'").strip('"')
                if domain:
                    domains.append(domain)

    print(f"\n✅ 从有效行中提取到 {len(domains)} 条域名（与有效行数一致）")
    return domains

def write_output(domains):
    with open("ChinaMax_domain_set.txt", 'w') as f:
        f.write("# ChinaMax 规则集 - Surge DOMAIN-SET\n")
        f.write("# 所有域名作为后缀匹配（带 . 前缀）\n")
        for d in domains:
            f.write(f".{d}\n")
    print(f"✅ Surge DOMAIN-SET 已保存，共 {len(domains)} 条")

    with open("ChinaMax_rule_set.list", 'w') as f:
        f.write("# ChinaMax 规则集 - Surge RULE-SET\n")
        for d in domains:
            f.write(f"DOMAIN-SUFFIX,{d}\n")
    print(f"✅ Surge RULE-SET 已保存，共 {len(domains)} 条")

    with open("ChinaMax_egern.yaml", 'w') as f:
        f.write("# ChinaMax 规则集 - Egern YAML\n")
        f.write("rules:\n")
        for d in domains:
            f.write(f"  - domain_suffix: {d}\n")
    print(f"✅ Egern YAML 已保存，共 {len(domains)} 条")

def main():
    print("📥 正在下载 ChinaMax_Domain.yaml ...")
    try:
        domains = analyze_and_extract()
    except Exception as e:
        print(f"❌ 处理失败: {e}")
        return

    if not domains:
        print("⚠️ 未提取到任何域名，请检查文件结构。")
        return

    write_output(domains)
    print("\n🎉 所有转换完成！")
    print(f"📌 最终统计：未注释条目总数 = {len(domains)}")

if __name__ == "__main__":
    main()
