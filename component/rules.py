"""
规则模块

包含:
- CoC 大成功/大失败规则
- 理智检定规则
- 技能成长规则
"""

import random
from typing import Optional


# CoC 大成功/大失败规则
COC_RULES = {
    1: {
        "name": "规则1（默认）",
        "critical_success": lambda roll: roll == 1,
        "critical_fail": lambda roll, skill: roll >= 96 and skill < 50 or roll == 100,
    },
    2: {
        "name": "规则2",
        "critical_success": lambda roll: 1 <= roll <= 5,
        "critical_fail": lambda roll, skill: roll >= 96 and skill < 50 or roll == 100,
    },
    3: {
        "name": "规则3",
        "critical_success": lambda roll: roll == 1,
        "critical_fail": lambda roll, skill: roll == 100,
    },
    4: {
        "name": "规则4",
        "critical_success": lambda roll: 1 <= roll <= 5,
        "critical_fail": lambda roll, skill: roll == 100,
    },
    5: {
        "name": "规则5",
        "critical_success": lambda roll: roll == 1,
        "critical_fail": lambda roll, skill: roll >= 99 and skill < 50 or roll == 100,
    },
}


# 每群组的规则设置
_group_rules: dict[str, int] = {}


def get_group_rule(group_id: str) -> int:
    """获取群组的 CoC 规则类型"""
    return _group_rules.get(group_id, 1)


def set_group_rule(group_id: str, rule_type: int) -> None:
    """设置群组的 CoC 规则类型"""
    if rule_type not in COC_RULES:
        raise ValueError(f"无效的规则类型: {rule_type}，可选值: {list(COC_RULES.keys())}")
    _group_rules[group_id] = rule_type


def check_skill_result(roll_value: int, skill_value: int, group_id: Optional[str] = None) -> str:
    """
    判断技能检定结果
    
    Args:
        roll_value: 掷骰值 (1-100)
        skill_value: 技能值
        group_id: 群组ID（用于获取规则设置）
    
    Returns:
        结果类型: "大成功" / "成功" / "失败" / "大失败"
    """
    rule_type = get_group_rule(group_id) if group_id else 1
    rule = COC_RULES[rule_type]
    
    # 检查大成功
    if rule["critical_success"](roll_value):
        return "大成功"
    
    # 检查大失败
    if rule["critical_fail"](roll_value, skill_value):
        return "大失败"
    
    # 普通成功/失败
    if roll_value <= skill_value:
        return "成功"
    else:
        return "失败"


def modify_coc_great_sf_rule_command(group_id: str, command: str) -> str:
    """
    处理 setcoc 命令
    
    Args:
        group_id: 群组ID
        command: 命令参数
    
    Returns:
        响应消息
    """
    command = command.strip()
    
    if not command or command == " ":
        # 显示当前规则
        current = get_group_rule(group_id)
        return f"当前使用规则{current}（{COC_RULES[current]['name']}）\n可选规则: 1-5"
    
    try:
        rule_type = int(command)
        set_group_rule(group_id, rule_type)
        return f"已切换到规则{rule_type}（{COC_RULES[rule_type]['name']}）"
    except ValueError:
        return "规则编号必须是1-5的数字"
    except Exception as e:
        return str(e)


# 理智检定相关
SANITY_THRESHOLDS = {
    "temporary_crazy": 5,  # 单次损失5点以上触发临时疯狂
    "long_term_crazy": 20,  # 累计损失20点以上触发长期疯狂
}

# 临时疯狂症状
TEMPORARY_CRAZY_SYMPTOMS = [
    "失忆症：调查员忘记自己是谁，正在做什么",
    "假性残疾：调查员出现心因性的失明或失聪",
    "暴力倾向：调查员变得极具攻击性，可能会攻击附近的人",
    "偏执妄想：调查员陷入严重的偏执，认为有人在监视或迫害自己",
    "人际依赖：调查员过度依赖他人，无法独立行动",
    "昏厥：调查员失去意识，持续数分钟到数小时",
    "逃避行为：调查员试图逃离现场，可能会使用任何方式",
    "歇斯底里：调查员陷入狂笑或痛哭，无法控制情绪",
    "恐惧症：调查员产生强烈的恐惧，可能是对特定物体或情境",
    "躁狂症：调查员陷入异常兴奋，可能会做出危险行为",
]

# 长期疯狂症状
LONG_TERM_CRAZY_SYMPTOMS = [
    "健忘症：调查员忘记部分重要记忆，可能是最近的事件",
    "反社会行为：调查员表现出反社会倾向，不再关心道德或法律",
    "恐惧症：调查员产生新的持久恐惧，如恐高、幽闭恐惧等",
    "躁狂/抑郁：调查员情绪波动剧烈，时而亢奋时而低落",
    "偏执狂：调查员持续多疑，认为周围的人都在针对自己",
    "敏感化：调查员对某些刺激过度敏感，如噪音、光线等",
    "性功能障碍：调查员出现性功能问题，可能是心理因素导致",
    "躯体转换障碍：调查员出现身体症状，但没有生理原因",
    "强迫行为：调查员出现无法控制的重复行为",
    "分离性障碍：调查员出现人格分裂或身份认同问题",
]


def get_temporary_crazy_symptom() -> str:
    """获取随机临时疯狂症状"""
    return random.choice(TEMPORARY_CRAZY_SYMPTOMS)


def get_long_term_crazy_symptom() -> str:
    """获取随机长期疯狂症状"""
    return random.choice(LONG_TERM_CRAZY_SYMPTOMS)


# 技能成长相关
DEFAULT_GROWTH_CONFIG = {
    "threshold": 0,  # 检定成功且掷骰大于技能值时成长
    "dice": "1d10",  # 成长骰
    "max": 99,  # 技能上限
}


def check_skill_growth(
    roll_value: int,
    skill_value: int,
    config: Optional[dict] = None,
) -> tuple[bool, int]:
    """
    检查技能成长
    
    Args:
        roll_value: 掷骰值
        skill_value: 当前技能值
        config: 成长配置
    
    Returns:
        (是否成长, 增长值)
    """
    if config is None:
        config = DEFAULT_GROWTH_CONFIG
    
    threshold = config.get("threshold", DEFAULT_GROWTH_CONFIG["threshold"])
    max_value = config.get("max", DEFAULT_GROWTH_CONFIG["max"])
    dice_expr = config.get("dice", DEFAULT_GROWTH_CONFIG["dice"])
    
    # 检查是否达到上限
    if skill_value >= max_value:
        return False, 0
    
    # 检查是否可以成长
    if roll_value <= skill_value and roll_value > threshold:
        # 技能检定失败，但掷骰大于阈值，可以成长
        from .dice import roll_expression
        result = roll_expression(dice_expr)
        growth = min(result.total, max_value - skill_value)
        return True, growth
    
    # 成功的情况：如果掷骰大于技能值
    if roll_value > skill_value:
        from .dice import roll_expression
        result = roll_expression(dice_expr)
        growth = min(result.total, max_value - skill_value)
        return True, growth
    
    return False, 0
