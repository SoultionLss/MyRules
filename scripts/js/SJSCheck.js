// 司机社自动签到 - Egern 适配版
// 配置方式：在 Egern 中创建 schedule 类型脚本，设置 cron 表达式如 "0 8 * * *"（每天早上8点执行）

const MAIN_URL = "https://xsijishe.com";
const USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/114.0 Safari/537.36";

// 从环境变量读取账号配置
// 在 Egern 脚本配置中设置 env，格式为 JSON 数组：
// ACCOUNTS=[{"username":"user1","password":"pass1"},{"username":"user2","password":"pass2"}]
function getAccounts(ctx) {
    const accountsJson = ctx.env.ACCOUNTS;
    if (!accountsJson) {
        throw new Error("未配置 ACCOUNTS 环境变量，请按 [{\"username\":\"user1\",\"password\":\"pass1\"}] 格式配置");
    }
    try {
        const accounts = JSON.parse(accountsJson);
        if (!Array.isArray(accounts) || accounts.length === 0) {
            throw new Error("ACCOUNTS 必须是非空数组");
        }
        return accounts;
    } catch (e) {
        throw new Error("ACCOUNTS 格式错误，请使用有效的 JSON 数组: " + e.message);
    }
}

// 生成随机字符串
function getRandomString(length) {
    const chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789";
    let result = "";
    for (let i = 0; i < length; i++) {
        result += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    return result;
}

// MD5 加密（使用 Web Crypto API）
async function md5(message) {
    const msgUint8 = new TextEncoder().encode(message);
    const hashBuffer = await crypto.subtle.digest("MD5", msgUint8);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    return hashArray.map(b => b.toString(16).padStart(2, "0")).join("");
}

// 发起 HTTP 请求的辅助函数
async function httpRequest(url, options = {}) {
    const method = options.method || "GET";
    const headers = {
        "User-Agent": USER_AGENT,
        ...options.headers
    };
    
    const fetchOptions = {
        method: method,
        headers: headers,
        redirect: "follow"
    };
    
    if (options.body) {
        fetchOptions.body = options.body;
        if (!headers["Content-Type"]) {
            headers["Content-Type"] = "application/x-www-form-urlencoded";
        }
    }
    
    const response = await fetch(url, fetchOptions);
    return await response.text();
}

// 获取登录参数（formhash）
async function getLoginParams() {
    const referer = `${MAIN_URL}/home.php?mod=space`;
    const html = await httpRequest(referer, {
        headers: { "Referer": MAIN_URL + "/" }
    });
    
    // 解析 formhash
    const match = html.match(/<input\s+type="hidden"\s+name="formhash"\s+value="([^"]+)"/i);
    if (!match) {
        throw new Error("无法获取 formhash，可能页面结构已变化");
    }
    return {
        formhash: match[1],
        referer: referer
    };
}

// 登录
async function login(username, password, params) {
    const passwordMd5 = await md5(password);
    const loginUrl = `${MAIN_URL}/member.php?mod=logging&action=login&loginsubmit=yes&handlekey=login&loginhash=L${getRandomString(4)}&inajax=1`;
    
    const body = new URLSearchParams({
        formhash: params.formhash,
        referer: params.referer,
        username: username,
        password: passwordMd5,
        questionid: "0",
        answer: ""
    }).toString();
    
    const response = await httpRequest(loginUrl, {
        method: "POST",
        headers: { "Referer": params.referer },
        body: body
    });
    
    if (response.includes("欢迎您回来") || response.includes("欢迎回来")) {
        return true;
    }
    throw new Error("登录失败");
}

// 获取签到参数
async function getCheckInParams() {
    const referer = `${MAIN_URL}/k_misign-sign.html`;
    const html = await httpRequest(referer, {
        headers: { "Referer": MAIN_URL + "/" }
    });
    
    // 解析签到链接
    const match = html.match(/<a[^>]*id="JD_sign"[^>]*href="([^"]+)"/i);
    if (!match) {
        throw new Error("无法获取签到链接（可能已签到或页面结构变化）");
    }
    return {
        href: match[1],
        referer: referer
    };
}

// 执行签到
async function doCheckIn(params) {
    const checkInUrl = `${MAIN_URL}/${params.href}`;
    const response = await httpRequest(checkInUrl, {
        headers: { "Referer": params.referer }
    });
    
    if (response.includes("今日已签") || response.includes("您今天已经签到过了")) {
        return { status: "already", message: "今日已签到" };
    } else if (response.includes("签到成功") || response.includes("CDATA")) {
        return { status: "success", message: "签到成功！" };
    } else {
        return { status: "unknown", message: "签到结果未知" };
    }
}

// 获取用户信息
async function getUserInfo() {
    const url = `${MAIN_URL}/k_misign-sign.html`;
    const html = await httpRequest(url, {
        headers: { "Referer": MAIN_URL + "/" }
    });
    
    const getValue = (id) => {
        const match = html.match(new RegExp(`<input[^>]*id="${id}"[^>]*value="([^"]*)"`, "i"));
        return match ? match[1] : "未知";
    };
    
    // 解析积分
    let totalReward = "未知";
    const rewardMatch = html.match(/<li[^>]*class="nexmemberinfostwos"[^>]*>\s*<p>([^<]*)<\/p>/i);
    if (rewardMatch) {
        totalReward = rewardMatch[1].trim();
    }
    
    return {
        qiandaoNum: getValue("qiandaobtnnum"),
        lxlevel: getValue("lxlevel"),
        lxdays: getValue("lxdays"),
        lxtdays: getValue("lxtdays"),
        lxreward: getValue("lxreward"),
        totalReward: totalReward
    };
}

// 处理单个账号的签到
async function processAccount(account) {
    const results = [];
    const username = account.username;
    const password = account.password;
    
    try {
        results.push(`========== 开始签到: ${username} ==========`);
        
        // 1. 获取登录参数
        const loginParams = await getLoginParams();
        results.push(`获取登录参数成功: formhash=${loginParams.formhash}`);
        
        // 2. 登录
        await login(username, password, loginParams);
        results.push("✅ 登录成功");
        
        // 3. 获取签到参数
        const checkInParams = await getCheckInParams();
        results.push(`获取签到参数成功: ${checkInParams.href}`);
        
        // 4. 执行签到
        const checkInResult = await doCheckIn(checkInParams);
        results.push(`📌 ${checkInResult.message}`);
        
        // 5. 获取用户信息
        const userInfo = await getUserInfo();
        results.push(`📊 签到排名: ${userInfo.qiandaoNum}`);
        results.push(`📊 签到等级: Lv.${userInfo.lxlevel}`);
        results.push(`📊 连续签到: ${userInfo.lxdays} 天`);
        results.push(`📊 签到总数: ${userInfo.lxtdays} 天`);
        results.push(`📊 签到奖励: ${userInfo.lxreward}`);
        results.push(`📊 总积分: ${userInfo.totalReward}`);
        
        results.push(`✅ 完成处理: ${username}`);
    } catch (error) {
        results.push(`❌ 处理 ${username} 失败: ${error.message}`);
    }
    
    return results;
}

// Egern 脚本主入口
export default async function(ctx) {
    const results = [];
    results.push("🚀 司机社自动签到开始");
    results.push(`⏰ 执行时间: ${new Date().toLocaleString()}`);
    results.push("----------------------------------------");
    
    try {
        const accounts = getAccounts(ctx);
        results.push(`📋 共 ${accounts.length} 个账号待处理`);
        
        for (const account of accounts) {
            const accountResults = await processAccount(account);
            results.push(...accountResults);
            results.push("----------------------------------------");
        }
        
        results.push("🎉 所有账号签到处理完成");
    } catch (error) {
        results.push(`❌ 脚本执行失败: ${error.message}`);
        results.push("💡 请检查 ACCOUNTS 环境变量配置是否正确");
    }
    
    // 将结果输出到日志
    console.log(results.join("\n"));
    
    // 返回结果（可用于小组件显示）
    return {
        type: "widget",
        children: [
            {
                type: "text",
                text: "司机社签到",
                font: { size: "title2", weight: "bold" },
                textColor: "#FFFFFF"
            },
            {
                type: "text",
                text: results.slice(-5).join("\n"),
                font: { size: "footnote" },
                textColor: "#CCCCCC",
                numberOfLines: 0
            }
        ],
        backgroundColor: "#2D6A4F",
        padding: 16
    };
}
