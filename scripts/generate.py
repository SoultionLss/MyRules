# -*- coding: utf-8 -*-
"""按 Repcz/Tool 架构生成全平台规则合集仓库内容。

- 拉取上游规则 -> 合并去重 -> 按平台格式输出 <平台>/Rules/<类别>.<ext>
- 渲染主配置模板 -> 输出 <平台>/<主配置>（规则引用 raw 链接自动指向本仓库）

用法:
    python scripts/generate.py                 # 生成所有平台
    python scripts/generate.py surge           # 仅生成指定平台
    python scripts/generate.py --cats AI,Netflix surge   # 仅测试部分类别
"""
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent.parent
UA = "Mozilla/5.0 (compatible; rules-collection/1.0)"

REPOS = {
    "blackmatrix7": {
        "base": "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Clash/",
        "path": lambda s: "{cat}/{cat}.yaml".format(**s),
    },
    "xkww3n": {
        "base": "https://rules.xkww3n.cyou/text/",
        "path": lambda s: s["file"] + ".txt",
    },
    "quixoticheart-ruleset": {
        "base": "https://raw.githubusercontent.com/QuixoticHeart/rule-set/ruleset/egern/",
        "path": lambda s: s["file"],
    },
    "quixoticheart-custom": {
        "base": "https://raw.githubusercontent.com/QuixoticHeart/rule-set/master/custom/",
        "path": lambda s: s["file"],
    },
}

SECTION_MAP = {
    "DOMAIN": "domain_set",
    "DOMAIN-SUFFIX": "domain_suffix_set",
    "DOMAIN-KEYWORD": "domain_keyword_set",
    "DOMAIN-REGEX": "domain_regex_set",
    "URL-REGEX": "url_regex_set",
    "IP-CIDR": "ip_cidr",
    "IP-CIDR6": "ip_cidr6",
    "IP-ASN": "ip_asn",
    "GEOIP": "geoip",
    "PROCESS-NAME": "process_name",
    "USER-AGENT": "user_agent",
}

REVERSE_MAP = {
    "domain": "DOMAIN",
    "domain_suffix": "DOMAIN-SUFFIX",
    "domain_keyword": "DOMAIN-KEYWORD",
    "domain_regex": "DOMAIN-REGEX",
    "url_regex": "URL-REGEX",
    "ip_cidr": "IP-CIDR",
    "ip_cidr6": "IP-CIDR6",
    "ip_asn": "IP-ASN",
    "geoip": "GEOIP",
    "process_name": "PROCESS-NAME",
    "user_agent": "USER-AGENT",
}

SECTION_RE = re.compile(
    r"^(domain|domain_suffix|domain_keyword|domain_regex|url_regex|ip_cidr6|ip_cidr|ip_asn|geoip|process_name|user_agent)(_set)?:$"
)

IPV4_RE = re.compile(r"^\d{1,3}(\.\d{1,3}){3}/\d{1,2}$")
IPV6_RE = re.compile(r"^[0-9a-fA-F:]+/\d{1,3}$")

def log(msg):
    print("[generate] " + msg)

def fetch(url):
    for attempt in range(3):
        try:
            req = Request(url, headers={"User-Agent": UA})
            with urlopen(req, timeout=60) as resp:
                return resp.read().decode("utf-8", "replace")
        except Exception as exc:
            if attempt == 2:
                raise
            time.sleep(2)

def clean_line(line):
    line = line.strip()
    if not line or line.startswith(("#", "!", "//", ";")):
        return None
    return line

def parse_payload(text):
    lines = []
    in_payload = False
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("payload:"):
            in_payload = True
            continue
        if not in_payload:
            continue
        if line and not line.startswith("-"):
            in_payload = False
            continue
        item = clean_line(line.lstrip("-").strip().strip('"').strip("'"))
        if item:
            lines.append(item)
    return lines

def parse_domain_sets(text):
    section = None
    lines = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.endswith(":"):
            m = SECTION_RE.match(line)
            section = REVERSE_MAP.get(m.group(1)) if m else None
            continue
        if section and line.startswith("-"):
            item = clean_line(line.lstrip("-").strip().strip('"').strip("'"))
            if item:
                lines.append("{},{}".format(section, item))
    return lines

def parse_text_dot(text):
    lines = []
    for raw in text.splitlines():
        item = clean_line(raw)
        if not item:
            continue
        if "," in item:
            lines.append(item)
        elif IPV4_RE.match(item):
            lines.append("IP-CIDR," + item)
        elif IPV6_RE.match(item):
            lines.append("IP-CIDR6," + item)
        elif item.startswith("."):
            lines.append("DOMAIN-SUFFIX," + item.lstrip("."))
        elif "." in item:
            lines.append("DOMAIN-SUFFIX," + item)
        else:
            lines.append(item)
    return lines

def detect_format(text):
    if re.search(r"^payload:", text, re.M):
        return "clash"
    if re.search(SECTION_RE.pattern, text, re.M):
        return "singbox-yaml"
    return "text-dot"

PARSERS = {
    "clash": parse_payload,
    "singbox-yaml": parse_domain_sets,
    "text-dot": parse_text_dot,
}

def dedupe(items):
    seen = set()
    out = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out

def load_config():
    with open(ROOT / "scripts" / "sources.json", "r", encoding="utf-8") as f:
        return json.load(f)

def repo_identity():
    env_repo = os.environ.get("GITHUB_REPOSITORY", "")
    if "/" in env_repo:
        owner, name = env_repo.split("/", 1)
        branch = os.environ.get("GITHUB_REF_NAME", "main")
        return owner, name, branch
    return "用户名", "仓库名", "main"

def resolve_url(repo_key, spec):
    if spec.get("url"):
        return spec["url"]
    repo = REPOS[repo_key]
    return repo["base"] + repo["path"](spec)

def fetch_rules(repo_key, spec):
    if spec.get("enabled") is False:
        log("跳过(未启用): {} {} - {}".format(repo_key, spec.get("cat", spec.get("file")), spec.get("note", "")))
        return []
    url = resolve_url(repo_key, spec)
    try:
        text = fetch(url)
    except Exception as exc:
        log("获取失败: {} ({})".format(url, exc))
        return []
    fmt = spec.get("format") or detect_format(text)
    rules = PARSERS[fmt](text)
    log("获取成功: {}  ({} 条, 格式: {})".format(url, len(rules), fmt))
    return rules

def group_rules(rules):
    groups = {}
    for line in rules:
        kind, _, value = line.partition(",")
        value = value.strip()
        if ",no-resolve" in value:
            value = value.replace(",no-resolve", "")
        section = SECTION_MAP.get(kind)
        if not section or not value:
            continue
        groups.setdefault(section, []).append(value)
    for section in groups:
        groups[section] = dedupe(groups[section])
    return groups

def emit_yaml(out_file, cat_key, groups):
    lines = ["# 规则名称: {}".format(cat_key),
             "# 规则统计: {}".format(sum(len(v) for v in groups.values())), ""]
    for section in SECTION_MAP.values():
        values = groups.get(section)
        if not values:
            continue
        lines.append("{}:".format(section))
        for value in sorted(values, key=str.lower):
            lines.append("  - {}".format(value))
        lines.append("")
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines).rstrip() + "\n")
    return sum(len(v) for v in groups.values())

def emit_list(out_file, cat_key, groups):
    lines = ["# 规则名称: {}".format(cat_key),
             "# 规则统计: {}".format(sum(len(v) for v in groups.values())), ""]
    reverse = {v: k for k, v in SECTION_MAP.items()}
    total = 0
    for section, values in groups.items():
        kind = reverse[section]
        for value in sorted(values, key=str.lower):
            lines.append("{},{}".format(kind, value))
        total += len(values)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines).rstrip() + "\n")
    return total

QX_PREFIX = {
    "domain_set": "host",
    "domain_suffix_set": "host-suffix",
    "domain_keyword_set": "host-keyword",
    "ip_cidr": "ip-cidr",
    "ip_cidr6": "ip-cidr6",
    "ip_asn": "ip-asn",
    "geoip": "geoip",
}

def emit_qx(out_file, cat_key, groups):
    lines = ["# 规则名称: {}".format(cat_key),
             "# 规则统计: {}".format(sum(len(v) for v in groups.values())), ""]
    total = 0
    for section, values in groups.items():
        prefix = QX_PREFIX.get(section)
        if not prefix:
            continue
        for value in sorted(values, key=str.lower):
            lines.append("{},{}".format(prefix, value))
        total += len(values)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines).rstrip() + "\n")
    return total

def emit_json(out_file, cat_key, groups):
    rules = []
    if groups.get("domain_set"):
        rules.append({"domain": sorted(groups["domain_set"], key=str.lower)})
    if groups.get("domain_suffix_set"):
        rules.append({"domain_suffix": sorted(groups["domain_suffix_set"], key=str.lower)})
    if groups.get("domain_keyword_set"):
        rules.append({"domain_keyword": sorted(groups["domain_keyword_set"], key=str.lower)})
    if groups.get("domain_regex_set"):
        rules.append({"domain_regex": sorted(groups["domain_regex_set"])})
    if groups.get("url_regex_set"):
        rules.append({"url_regex": sorted(groups["url_regex_set"])})
    if groups.get("ip_cidr"):
        rules.append({"ip_cidr": sorted(groups["ip_cidr"], key=str.lower)})
    if groups.get("ip_cidr6"):
        rules.append({"ip_cidr6": sorted(groups["ip_cidr6"], key=str.lower)})
    if groups.get("ip_asn"):
        rules.append({"ip_asn": sorted(groups["ip_asn"], key=int)})
    if groups.get("geoip"):
        rules.append({"geoip": sorted(groups["geoip"], key=str.lower)})
    payload = {"version": 1, "rules": rules}
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8", newline="\n") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return sum(len(v) for v in groups.values())

EMITTERS = {
    "yaml": emit_yaml,
    "list": emit_list,
    "qx": emit_qx,
    "json": emit_json,
}

def rule_url(owner, name, branch, output, cat_key, ext):
    return "https://github.com/{}/{}/raw/{}/{}/Rules/{}.{}".format(
        owner, name, branch, output, cat_key, ext)

def render_rules_egern(categories, owner, name, branch, output, ext):
    lines = ["rules:"]
    for cat_key, cat in categories.items():
        lines.append("- rule_set:")
        lines.append("    match: {}".format(rule_url(owner, name, branch, output, cat_key, ext)))
        lines.append("    policy: {}".format(cat.get("policy", "Global")))
    return {"{{RULES}}": "\n".join(lines)}

def render_rules_surge(categories, owner, name, branch, output, ext):
    lines = ["[Rule]"]
    for cat_key, cat in categories.items():
        lines.append("RULE-SET,{},{}".format(
            rule_url(owner, name, branch, output, cat_key, ext), cat.get("policy", "Global")))
    lines.append("GEOIP,CN,DIRECT")
    lines.append("FINAL,Final")
    return {"{{RULES}}": "\n".join(lines)}

def render_rules_loon(categories, owner, name, branch, output, ext):
    lines = ["[Remote Rule]"]
    for cat_key, cat in categories.items():
        lines.append("RULE-SET,{},{}".format(
            rule_url(owner, name, branch, output, cat_key, ext), cat.get("policy", "Global")))
    lines.append("GEOIP,CN,DIRECT")
    lines.append("FINAL,Final")
    return {"{{RULES}}": "\n".join(lines)}

def render_rules_shadowrocket(categories, owner, name, branch, output, ext):
    return render_rules_surge(categories, owner, name, branch, output, ext)

def render_rules_qx(categories, owner, name, branch, output, ext):
    lines = ["[filter_remote]"]
    for cat_key, cat in categories.items():
        lines.append("{}, tag={}, force-policy={}, update-interval=86400, opt-parser=false".format(
            rule_url(owner, name, branch, output, cat_key, ext),
            cat_key, cat.get("policy", "Global")))
    return {"{{RULES}}": "\n".join(lines)}

def render_rules_clash(categories, owner, name, branch, output, ext):
    providers = ["rule-providers:"]
    entries = ["rules:"]
    for cat_key, cat in categories.items():
        providers.append("  {}:".format(cat_key))
        providers.append("    type: http")
        providers.append("    behavior: classical")
        providers.append("    url: {}".format(rule_url(owner, name, branch, output, cat_key, ext)))
        providers.append("    path: ./ruleset/{}.yaml".format(cat_key))
        providers.append("    interval: 86400")
        entries.append("  - RULE-SET,{},{}".format(cat_key, cat.get("policy", "Global")))
    entries.append("  - GEOIP,CN,DIRECT")
    entries.append("  - MATCH,Final")
    return {"{{RULE_PROVIDERS}}": "\n".join(providers),
            "{{RULE_ENTRIES}}": "\n".join(entries)}

def render_rules_singbox(categories, owner, name, branch, output, ext):
    rule_sets = ["\"rule_set\": ["]
    outbound_rules = ["\"rules\": ["]
    items = list(categories.items())
    for i, (cat_key, cat) in enumerate(items):
        rule_sets.append("    {{\"type\": \"remote\", \"tag\": \"{}\", \"url\": \"{}\", \"download_detour\": \"auto\"}}{}".format(
            cat_key, rule_url(owner, name, branch, output, cat_key, ext), "," if i < len(items) - 1 else ""))
        outbound_rules.append("    {{\"action\": \"route\", \"rule_set\": [\"{}\"], \"outbound\": \"{}\"}},".format(
            cat_key, cat.get("policy", "Global")))
    rule_sets.append("  ],")
    outbound_rules.append("    {\"action\": \"route\", \"geoip\": [\"cn\"], \"outbound\": \"direct\"},")
    outbound_rules.append("    {\"action\": \"route\", \"ip_is_private\": true, \"outbound\": \"direct\"},")
    outbound_rules.append("    {\"action\": \"route\", \"outbound\": \"final\"}")
    outbound_rules.append("  ]")
    return {"{{RULE_SETS}}": "\n".join(rule_sets),
            "{{ROUTE_RULES}}": "\n".join(outbound_rules)}

RENDERERS = {
    "egern": render_rules_egern,
    "surge": render_rules_surge,
    "loon": render_rules_loon,
    "shadowrocket": render_rules_shadowrocket,
    "quantumultx": render_rules_qx,
    "mihomo": render_rules_clash,
    "stash": render_rules_clash,
    "surfboard": render_rules_clash,
    "singbox": render_rules_singbox,
}

def render_template(tpl_path, placeholders, now):
    text = tpl_path.read_text(encoding="utf-8")
    for key, value in placeholders.items():
        text = text.replace(key, value)
    text = text.replace("{{RULES_TIMESTAMP}}", now)
    return text

def generate_platform(pkey, pconf, categories, identity, only_cats=None):
    owner, name, branch = identity
    out_dir = ROOT / pconf["output"]
    rule_fmt = pconf.get("rule_fmt", "yaml")
    rule_ext = pconf.get("rule_ext", "yaml")
    emit = EMITTERS[rule_fmt]
    selected = categories if only_cats is None else {
        k: v for k, v in categories.items() if k in only_cats}
    if not selected:
        log("[{}] 无已配置类别，跳过".format(pconf.get("label", pkey)))
        return
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    log("[{}] 开始生成 {} 个类别 (格式: {})".format(
        pconf.get("label", pkey), len(selected), rule_fmt))
    for cat_key, cat in selected.items():
        rules = []
        for spec in cat.get("sources", []):
            rules.extend(fetch_rules(spec["repo"], spec))
        rules = dedupe(rules)
        groups = group_rules(rules)
        total = emit(out_dir / "Rules" / (cat_key + "." + rule_ext), cat_key, groups)
        log("已输出: {}  ({} 条)".format("Rules/" + cat_key + "." + rule_ext, total))
    tpl = ROOT / pconf["template"]
    if tpl.exists():
        renderer = RENDERERS.get(pkey, render_rules_egern)
        placeholders = renderer(selected, owner, name, branch, pconf["output"], rule_ext)
        content = render_template(tpl, placeholders, now)
        main_file = out_dir / pconf.get("main", pconf.get("label", pkey) + ".conf")
        main_file.parent.mkdir(parents=True, exist_ok=True)
        with open(main_file, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)
        log("已输出: {}  (主配置)".format(main_file.relative_to(ROOT)))

def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = [a for a in sys.argv[1:]]
    only_cats = None
    if "--cats" in args:
        idx = args.index("--cats")
        only_cats = set(args[idx + 1].split(","))
        args = args[:idx] + args[idx + 2:]
    config = load_config()
    identity = repo_identity()
    platforms = config["platforms"]
    targets = args or list(platforms.keys())
    for pkey in targets:
        if pkey not in platforms:
            log("未知平台: {}，可用: {}".format(pkey, ", ".join(platforms)))
            continue
        pconf = platforms[pkey]
        categories = config["categories"] if pconf.get("use_shared") else pconf.get("categories", {})
        generate_platform(pkey, pconf, categories, identity, only_cats)
    log("全部完成")

if __name__ == "__main__":
    main()
