import shutil
from pathlib import Path
from collections import defaultdict
from parser import parse_rules_yaml
from utils import fetch_domains_from_url, format_surge_domainset, format_egern_yaml, format_clash_yaml

# 路径修正（基于脚本位置）
SCRIPT_DIR = Path(__file__).parent
BASE_DIR = SCRIPT_DIR.parent

CONFIG_PATH = BASE_DIR / "config" / "my_rules.yaml"
OUTPUT_DIR = BASE_DIR / "output"

PLATFORMS = {
    "Surge": {"ext": ".list", "formatter": format_surge_domainset},
    "Egern": {"ext": ".yaml", "formatter": format_egern_yaml},
    "Clash": {"ext": ".yaml", "formatter": format_clash_yaml},
}

def main():
    # ---------- 1. 清空旧的 output ----------
    if OUTPUT_DIR.exists():
        print(f"🗑️ 删除旧的 output 目录: {OUTPUT_DIR}")
        shutil.rmtree(OUTPUT_DIR)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    # ----------------------------------------

    print("📖 解析规则配置文件...")
    rules = parse_rules_yaml(CONFIG_PATH)

    # 按策略分组：rule_set 和特殊规则
    groups = defaultdict(list)
    special_rules = defaultdict(list)
    for r in rules:
        if r.get('type') == 'rule_set' and 'match' in r:
            groups[r['policy']].append(r['match'])
        elif r.get('type') in ('domain', 'domain_keyword', 'domain_regex'):
            special_rules[r['policy']].append(r)

    print(f"发现 {len(groups)} 个策略组，{len(special_rules)} 个有特殊规则的策略")

    # 创建各平台的 Rules 子目录
    for plat in PLATFORMS:
        (OUTPUT_DIR / plat / "Rules").mkdir(parents=True, exist_ok=True)

    # ---------- 2. 处理 rule_set 组 ----------
    for policy, urls in groups.items():
        print(f"🔄 处理组: {policy} (共 {len(urls)} 个源)")
        all_domains = set()
        for url in urls:
            try:
                domains = fetch_domains_from_url(url)
                print(f"   ✅ {url} -> {len(domains)} 条")
                all_domains.update(domains)
            except Exception as e:
                print(f"   ❌ 拉取失败: {url} - {e}")

        if not all_domains:
            print(f"   ⚠️ 无域名，跳过")
            continue

        for plat, info in PLATFORMS.items():
            formatter = info['formatter']
            if plat == "Clash":
                content = formatter(all_domains, policy)
            else:
                content = formatter(all_domains)
            file_path = OUTPUT_DIR / plat / "Rules" / f"{policy}{info['ext']}"
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"   ✅ 生成 {plat} 规则: {file_path}")

    # ---------- 3. 处理特殊规则（仅 Surge 生成 _Extra 文件） ----------
    if special_rules:
        for policy, items in special_rules.items():
            lines = []
            for r in items:
                typ = r['type']
                if typ == 'domain':
                    lines.append(f"DOMAIN,{r['match']}")
                elif typ == 'domain_keyword':
                    lines.append(f"DOMAIN-KEYWORD,{r['match']}")
                elif typ == 'domain_regex':
                    lines.append(f"DOMAIN-REGEX,{r['match']}")
            if lines:
                file_path = OUTPUT_DIR / "Surge" / "Rules" / f"{policy}_Extra.list"
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write("# 特殊规则（单条）\n")
                    f.write('\n'.join(lines))
                print(f"   ✅ 生成 Surge 特殊规则: {file_path}")

    print("🎉 所有规则生成完成！")

if __name__ == "__main__":
    main()
