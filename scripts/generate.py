from pathlib import Path
from collections import defaultdict
from parser import parse_rules_yaml
from utils import fetch_domains_from_url, format_surge_domainset, format_egern_yaml, format_clash_yaml

CONFIG_PATH = Path("config/my_rules.yaml")
OUTPUT_DIR = Path("output")

PLATFORMS = {
    "Surge": {"ext": ".list", "formatter": format_surge_domainset},
    "Egern": {"ext": ".yaml", "formatter": format_egern_yaml},
    "Clash": {"ext": ".yaml", "formatter": format_clash_yaml},
}

def main():
    print("📖 解析规则配置文件...")
    rules = parse_rules_yaml(CONFIG_PATH)
    
    groups = defaultdict(list)
    special_rules = []
    for r in rules:
        if r.get('type') == 'rule_set' and 'match' in r:
            groups[r['policy']].append(r['match'])
        elif r.get('type') in ('domain', 'domain_keyword', 'domain_regex'):
            special_rules.append(r)
    
    print(f"发现 {len(groups)} 个策略组，{len(special_rules)} 条特殊规则")
    
    for plat in PLATFORMS:
        (OUTPUT_DIR / plat / "Rules").mkdir(parents=True, exist_ok=True)
    
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
    
    if special_rules:
        for plat in PLATFORMS:
            lines = []
            for r in special_rules:
                typ = r['type']
                if typ == 'domain':
                    lines.append(f"DOMAIN,{r['match']},{r['policy']}")
                elif typ == 'domain_keyword':
                    lines.append(f"DOMAIN-KEYWORD,{r['match']},{r['policy']}")
                elif typ == 'domain_regex':
                    lines.append(f"DOMAIN-REGEX,{r['match']},{r['policy']}")
            if lines:
                file_path = OUTPUT_DIR / plat / "Rules" / f"Custom{PLATFORMS[plat]['ext']}"
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write("# 特殊规则（单条）\n")
                    f.write('\n'.join(lines))
                print(f"   ✅ 生成 {plat} 特殊规则: {file_path}")
    
    print("🎉 所有规则生成完成！")

if __name__ == "__main__":
    main()
