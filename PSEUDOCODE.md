# 规则生成逻辑伪代码（骨架）

> 本文件是生成逻辑的"唯一真源"。当需要新增某类规则时，在对应平台小节追加条目，
> 再由 scripts/merge.py 实现。当前为骨架版本，具体规则类别以 `TODO` 标注，按需补充。

## 0. 全局流程

```
ON schedule(每天 06:00 UTC) / workflow_dispatch:
    RUN scripts/merge.py

merge.py:
    config = load("scripts/sources.json")        # 来源配置
    for platform in [egern, clash, surge, shadowrocket, loon, quantumultx, singbox]:
        generate_<platform>(config[platform])

    if 有变更:
        git add rules/
        git commit -m "auto: update rules (date)"
        git push
    else:
        log("无更新，跳过提交")
```

## 1. 平台级联关系

生成任一平台合集后，自动按顺序生成后续平台：

```
顺序: egern → clash → surge → shadowrocket → loon → quantumultx → singbox
规则: 上游平台产物可复用于下游平台（如 clash 产物转 surge list）
TODO: 细化各平台间产物复用关系（哪些平台的产物可直接转换给哪些平台）
```

## 2. 通用函数（各平台共用）

```
fetch(url)                     # 下载远程规则文本，失败重试 3 次
parse_<format>(text)           # 解析为规则行集合
    # 支持：Clash YAML payload / Surge List / QuantumultX / JSON / srs
normalize(line)                # 统一大小写、去首尾空格、修正前缀
dedupe(rules)                  # 去重 + 剔除空行 / 注释行
merge(*sources)                # 多来源顺序合并，后者补充前者
emit_<format>(rules, header)   # 序列化为目标平台格式
```

## 3. 各平台生成逻辑（骨架）

### 3.1 Egern

> 说明：blackmatrix7 无 Egern 专属目录，取其 Surge / Clash 分类做格式转换后合并；
> 每类规则独立输出一个文件，便于客户端按需订阅，另输出一个总合集。

```
generate_egern():
    base = [
        xkww3n/Rules 的 egern 分类,
        blackmatrix7/ios_rule_script 的 surge/clash 分类(转换格式),
        QuixoticHeart/rule-set,
    ]

    # A. 广告拦截
    adblock = merge(base["广告拦截"])                    # TODO: 补充广告源 URL

    # B. 中国规则（国内直连）
    china = merge(base["中国规则"])                      # TODO: 补充中国规则 URL

    # C. 流媒体（国际主流）
    streaming = merge(
        base["Netflix"],
        base["Disney+"],
        base["HBO Max"],                                 # hbo+
        base["Apple TV+"],
        base["其他国际流媒体"],                           # Prime Video / Spotify / Hulu 等
        # TODO: 补充具体流媒体 URL
    )

    # D. 社交媒体
    social = merge(
        base["Instagram"],
        base["Reddit"],
        base["Twitter / X"],
        base["Threads"],
        # TODO: 补充具体社交媒体 URL
    )

    # E. 即时通讯
    messaging = merge(
        base["WhatsApp"],
        base["LINE"],
        # TODO: 补充具体通讯 URL
    )

    # F. Telegram
    telegram = merge(base["Telegram"])                   # TODO: 补充 Telegram URL

    # G. YouTube
    youtube = merge(base["YouTube"])                     # TODO: 补充 YouTube URL

    # H. Google 服务（谷歌服务中国 + Gemini）
    google = merge(
        base["Google 服务中国"],                          # 国内可直连的谷歌服务
        base["Gemini"],
        # TODO: 补充 Google 相关 URL
    )

    # I. AI 规则（除 Gemini 外的国际主流 AI）
    ai_international = merge(
        base["ChatGPT / OpenAI"],
        base["Claude / Anthropic"],
        base["Perplexity"],
        # TODO: 补充其他国际 AI URL
    )

    # J. AI CN（国内主流 AI 模型）
    ai_cn = merge(
        base["DeepSeek"],
        base["Kimi / 月之暗面"],
        base["通义千问"],
        base["豆包"],
        base["文心一言"],
        # TODO: 补充其他国内 AI URL
    )

    # 输出：每类独立文件 + 一个总合集
    emit_egern("rules/egern/adblock.list",       adblock)
    emit_egern("rules/egern/china.list",         china)
    emit_egern("rules/egern/streaming.list",     streaming)
    emit_egern("rules/egern/social.list",        social)
    emit_egern("rules/egern/messaging.list",     messaging)
    emit_egern("rules/egern/telegram.list",      telegram)
    emit_egern("rules/egern/youtube.list",       youtube)
    emit_egern("rules/egern/google.list",        google)
    emit_egern("rules/egern/ai_international.list", ai_international)
    emit_egern("rules/egern/ai_cn.list",         ai_cn)
    emit_egern("rules/egern/all.list",           merge(以上全部))   # 总合集
```

### 3.2 Clash / Clash Meta

```
generate_clash():
    rules = []
    rules += fetch("Loyalsoldier/clash-rules 的全部规则集")
    rules += fetch("DustinWin/ruleset_geodata 的 clash 分类")
    rules += fetch("ACL4SSR 常用分组合并")
    # TODO: 在此追加具体规则类别
    emit_clash_yaml(dedupe(merge(rules)))
```

### 3.3 Surge

```
generate_surge():
    rules = []
    rules += fetch("blackmatrix7 的 surge 分类")
    rules += fetch("xkww3n/Rules 的 surge 分类")
    rules += fetch("Hackl0us/SS-Rule-Snippet")
    # TODO: 在此追加具体规则类别
    emit_surge_list(dedupe(merge(rules)))
```

### 3.4 Shadowrocket

```
generate_shadowrocket():
    rules = []
    rules += fetch("GMOogway/shadowrocket-rules")
    rules += fetch("blackmatrix7 的 shadowrocket 分类")
    # TODO: 在此追加具体规则类别
    emit_shadowrocket_list(dedupe(merge(rules)))
```

### 3.5 Loon

```
generate_loon():
    rules = []
    rules += fetch("blackmatrix7 的 loon 分类")
    rules += fetch("fmz200/wool_scripts 的 loon 分类")
    # TODO: 在此追加具体规则类别
    emit_loon_list(dedupe(merge(rules)))
```

### 3.6 Quantumult X

```
generate_quantumultx():
    rules = []
    rules += fetch("blackmatrix7 的 quantumultx 分类")
    rules += fetch("fmz200/wool_scripts 的 qx 分类")
    # TODO: 在此追加具体规则类别
    emit_qx_conf(dedupe(merge(rules)))
```

### 3.7 sing-box

```
generate_singbox():
    rules = []
    rules += fetch("xkww3n/Rules 的 singbox 分类")
    rules += fetch("DustinWin/ruleset_geodata 的 singbox 分类")
    # TODO: 在此追加具体规则类别
    emit_singbox_json(dedupe(merge(rules)))
```

## 4. 待补充清单

### 已完成（Egern 已按类别细化）
- [x] Egern：广告拦截 / 中国规则 / 流媒体（奈飞、迪士尼、HBO+、Apple TV+）/ 社交媒体（Instagram、Reddit、推特、Threads）/ 即时通讯（WhatsApp、LINE）/ Telegram / YouTube / Google（含谷歌服务中国、Gemini）/ 国际 AI（除 Gemini）/ AI-CN（DeepSeek、Kimi 等）

### 待补充
- [ ] 各平台（Clash / Surge / Shadowrocket / Loon / Quantumult X / sing-box）按 Egern 结构细化
- [ ] 隐私追踪 / 反指纹类规则
- [ ] 广告拦截、中国规则等类目补全其他平台来源
- [ ] Egern 各类别的具体来源 URL（sources.json）
- [ ] 各平台级联复用关系细化
- [ ] rules/README.md 订阅链接说明页
