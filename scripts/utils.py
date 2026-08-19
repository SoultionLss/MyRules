import requests
import yaml
from typing import Set

def fetch_domains_from_url(url: str) -> Set[str]:
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    text = resp.text
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
                if domain:
                    domains.add(domain)
    except:
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            for prefix in ['DOMAIN-SUFFIX,', 'DOMAIN,']:
                if line.startswith(prefix):
                    line = line[len(prefix):]
            domain = line.strip("'").strip('"')
            if domain:
                domains.add(domain)
    
    return domains

def format_surge_domainset(domains: Set[str]) -> str:
    return '\n'.join(f".{d}" for d in sorted(domains))

def format_egern_yaml(domains: Set[str]) -> str:
    lines = ["rules:"]
    lines.extend(f"  - domain_suffix: {d}" for d in sorted(domains))
    return '\n'.join(lines)

def format_clash_yaml(domains: Set[str], policy: str) -> str:
    lines = ["payload:"]
    lines.extend(f"  - DOMAIN-SUFFIX,{d},{policy}" for d in sorted(domains))
    return '\n'.join(lines)
