import yaml
from typing import List, Dict

def parse_rules_yaml(filepath: str) -> List[Dict]:
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
        elif 'domain' in item:
            entry = item['domain']
            entry['type'] = 'domain'
            rules.append(entry)
        elif 'domain_keyword' in item:
            entry = item['domain_keyword']
            entry['type'] = 'domain_keyword'
            rules.append(entry)
        elif 'domain_regex' in item:
            entry = item['domain_regex']
            entry['type'] = 'domain_regex'
            rules.append(entry)
        elif 'default' in item:
            rules.append({'type': 'default', 'policy': item['default']['policy']})
    return rules
