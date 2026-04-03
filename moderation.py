"""话题审核模块 - 过滤不适宜公开辩论的内容"""

# 政治敏感话题（按类别组织，便于维护）
POLITICAL_KEYWORDS = [
    "国家领导人", "主席", "总统选举", "总理", "总书记",
    "推翻", "颠覆", "颜色革命", "分裂", "台独", "藏独", "疆独",
    "香港独立", "民主运动", "六四", "天安门事件",
    "一党专政", "多党制", "反对党", "在野党",
    "法轮功", "全能神", "邪教", "修炼", "大法",
    "反共", "亲共", "卖国", "汉奸",
]

# 暴力犯罪相关
VIOLENCE_KEYWORDS = [
    "如何杀人", "如何下毒", "如何制造炸弹", "如何抢劫",
    "家庭暴力", "虐待儿童", "性侵犯", "强奸",
    "自杀方法", "如何自杀", "自杀指南",
    "报复社会", "校园袭击",
]

# 色情相关
ADULT_KEYWORDS = [
    "如何约炮", "一夜情", "援助交际",
    "未成年人性", "儿童色情",
]

# 隐私财产相关
FRAUD_KEYWORDS = [
    "如何盗取", "如何诈骗", "如何伪造",
    "如何洗钱", "逃税方法", "避税技巧",
]


def check_topic(topic: str) -> tuple[bool, str]:
    """
    审核话题，返回 (是否通过, 拒绝原因)。
    通过返回 (True, "")。
    """
    t = topic.lower()

    for kw in POLITICAL_KEYWORDS:
        if kw.lower() in t:
            return False, f"话题涉及政治敏感内容（{kw}），不适合公开辩论"

    for kw in VIOLENCE_KEYWORDS:
        if kw.lower() in t:
            return False, f"话题涉及暴力相关（{kw}），不适合公开辩论"

    for kw in ADULT_KEYWORDS:
        if kw.lower() in t:
            return False, f"话题涉及不适宜内容（{kw}），不适合公开辩论"

    for kw in FRAUD_KEYWORDS:
        if kw.lower() in t:
            return False, f"话题涉及潜在违法内容（{kw}），不适合公开辩论"

    return True, ""


def contains_sensitive(text: str) -> bool:
    """检查文本是否包含明显敏感词（用于检查用户输入的背景信息）"""
    t = text.lower()
    all_keywords = POLITICAL_KEYWORDS + VIOLENCE_KEYWORDS + ADULT_KEYWORDS + FRAUD_KEYWORDS
    for kw in all_keywords:
        if kw.lower() in t:
            return True
    return False
