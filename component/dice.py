"""
掷骰引擎模块

支持:
- 基本掷骰: NdM
- 复杂算式: 3d6+2d4-1d8
- 保留最高骰: NdMkX
- 重复掷骰: N#MdS
"""

import re
import random
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class DiceResult:
    """掷骰结果"""
    expression: str  # 原始表达式
    total: int  # 总值
    detail: str  # 详细过程
    rolls: list[list[int]] = field(default_factory=list)  # 每次掷骰的详细结果


@dataclass
class SingleDiceResult:
    """单次掷骰结果"""
    count: int  # 骰子数量
    faces: int  # 骰子面数
    keep: Optional[int] = None  # 保留最高几个
    results: list[int] = field(default_factory=list)  # 每个骰子的结果
    total: int = 0  # 计算后的总值


def roll_dice(count: int, faces: int, keep: Optional[int] = None) -> SingleDiceResult:
    """
    掷骰子
    
    Args:
        count: 骰子数量
        faces: 骰子面数
        keep: 保留最高几个（可选）
    
    Returns:
        SingleDiceResult: 掷骰结果
    """
    if count < 1 or faces < 1:
        raise ValueError("骰子数量和面数必须大于0")
    
    if count > 100:
        raise ValueError("骰子数量不能超过100")
    
    if faces > 10000:
        raise ValueError("骰子面数不能超过10000")
    
    # 掷骰
    results = [random.randint(1, faces) for _ in range(count)]
    results_sorted = sorted(results, reverse=True)
    
    # 计算保留的骰子
    if keep is not None:
        if keep < 1 or keep > count:
            raise ValueError("保留数量必须在1到骰子数量之间")
        kept = results_sorted[:keep]
        total = sum(kept)
    else:
        kept = results
        total = sum(results)
    
    return SingleDiceResult(
        count=count,
        faces=faces,
        keep=keep,
        results=results,
        total=total
    )


def format_dice_detail(result: SingleDiceResult) -> str:
    """格式化掷骰详细信息"""
    if result.keep is not None:
        # 有保留骰的情况
        sorted_results = sorted(result.results, reverse=True)
        kept = sorted_results[:result.keep]
        dropped = sorted_results[result.keep:]
        
        detail_parts = []
        for r in result.results:
            if r in kept:
                detail_parts.append(str(r))
                kept.remove(r)
            else:
                detail_parts.append(f"~{r}~")
        
        return f"{result.count}d{result.faces}k{result.keep}([{', '.join(detail_parts)}] = {result.total})"
    else:
        # 普通掷骰
        results_str = ', '.join(str(r) for r in result.results)
        if result.count == 1:
            return f"d{result.faces}({result.total})"
        return f"{result.count}d{result.faces}([{results_str}] = {result.total})"


def parse_dice_expression(expr: str) -> list[tuple[int, int, Optional[int]]]:
    """
    解析掷骰表达式
    
    支持格式:
    - NdM: 掷N个M面骰
    - NdMkX: 掷N个M面骰，保留最高X个
    - +NdM / -NdM: 加减运算
    
    Returns:
        list of (count, faces, keep): 每个骰子的参数
    """
    # 移除空格
    expr = expr.replace(' ', '')
    
    # 匹配模式: [+-]?NdM[kK]X?
    pattern = r'([+-]?)(\d*)d(\d+)(?:[kK](\d+))?'
    matches = re.findall(pattern, expr, re.IGNORECASE)
    
    if not matches:
        raise ValueError(f"无效的掷骰表达式: {expr}")
    
    dice_list = []
    for sign, count, faces, keep in matches:
        count = int(count) if count else 1
        faces = int(faces)
        keep = int(keep) if keep else None
        
        # 处理负号
        if sign == '-':
            count = -count
        
        dice_list.append((count, faces, keep))
    
    return dice_list


def roll_expression(expr: str) -> DiceResult:
    """
    执行掷骰表达式
    
    Args:
        expr: 掷骰表达式，如 "1d100", "3d6+2d4-1d8", "10d6k5"
    
    Returns:
        DiceResult: 掷骰结果
    """
    try:
        dice_list = parse_dice_expression(expr)
    except ValueError:
        # 尝试作为纯数字处理
        try:
            num = int(expr)
            return DiceResult(
                expression=expr,
                total=num,
                detail=str(num)
            )
        except ValueError:
            raise ValueError(f"无法解析表达式: {expr}")
    
    total = 0
    details = []
    all_rolls = []
    
    for count, faces, keep in dice_list:
        actual_count = abs(count)
        result = roll_dice(actual_count, faces, keep)
        
        # 处理负号
        if count < 0:
            total -= result.total
            detail = format_dice_detail(result)
            details.append(f"-{detail}")
        else:
            total += result.total
            detail = format_dice_detail(result)
            if len(dice_list) > 1 and count == dice_list[0][0]:
                details.append(detail)
            elif count < 0:
                details.append(f"-{detail}")
            else:
                if details:
                    details.append(f"+{detail}")
                else:
                    details.append(detail)
        
        all_rolls.append(result.results)
    
    return DiceResult(
        expression=expr,
        total=total,
        detail=' '.join(details),
        rolls=all_rolls
    )


def roll_repeat(times: int, expr: str) -> list[DiceResult]:
    """
    重复掷骰
    
    Args:
        times: 重复次数
        expr: 掷骰表达式
    
    Returns:
        list[DiceResult]: 每次掷骰的结果
    """
    if times < 1 or times > 20:
        raise ValueError("重复次数必须在1到20之间")
    
    return [roll_expression(expr) for _ in range(times)]


def parse_repeat_expression(expr: str) -> tuple[Optional[int], str]:
    """
    解析重复掷骰表达式
    
    格式: N#expr 或 expr
    
    Returns:
        (times, inner_expr): 重复次数和内部表达式
    """
    # 检查是否有重复标记
    if '#' in expr:
        parts = expr.split('#', 1)
        try:
            times = int(parts[0])
            return times, parts[1]
        except ValueError:
            raise ValueError(f"无效的重复次数: {parts[0]}")
    
    return None, expr


def roll(expr: str) -> DiceResult | list[DiceResult]:
    """
    统一掷骰入口
    
    支持:
    - 基本掷骰: 1d100
    - 复杂表达式: 3d6+2d4
    - 保留骰: 10d6k5
    - 重复掷骰: 3#1d20
    
    Args:
        expr: 掷骰表达式
    
    Returns:
        单次掷骰返回 DiceResult，多次掷骰返回 list[DiceResult]
    """
    times, inner_expr = parse_repeat_expression(expr)
    
    if times is not None:
        return roll_repeat(times, inner_expr)
    else:
        return roll_expression(inner_expr)


def skill_check(skill_value: int, bonus_dice: int = 0, penalty_dice: int = 0) -> tuple[int, str]:
    """
    CoC 技能检定
    
    Args:
        skill_value: 技能值
        bonus_dice: 奖励骰数量
        penalty_dice: 惩罚骰数量
    
    Returns:
        (roll_value, result_type): 掷骰值和结果类型
        result_type: "大成功" / "成功" / "失败" / "大失败"
    """
    if bonus_dice < 0 or penalty_dice < 0:
        raise ValueError("奖励骰和惩罚骰数量不能为负数")
    
    if bonus_dice > 0 and penalty_dice > 0:
        raise ValueError("奖励骰和惩罚骰不能同时使用")
    
    # 基础掷骰
    base_roll = random.randint(1, 100)
    
    if bonus_dice == 0 and penalty_dice == 0:
        # 普通检定
        roll_value = base_roll
    else:
        # 有奖励骰或惩罚骰
        extra_rolls = [random.randint(1, 100) for _ in range(bonus_dice + penalty_dice)]
        all_rolls = [base_roll] + extra_rolls
        
        if bonus_dice > 0:
            # 奖励骰取最低
            roll_value = min(all_rolls)
        else:
            # 惩罚骰取最高
            roll_value = max(all_rolls)
    
    # 判断结果
    result_type = _check_result(roll_value, skill_value)
    
    return roll_value, result_type


def _check_result(roll_value: int, skill_value: int) -> str:
    """判断检定结果类型"""
    # 大成功/大失败规则（使用默认规则1）
    if roll_value == 1:
        return "大成功"
    if roll_value >= 96 and skill_value < 50:
        return "大失败"
    if roll_value == 100:
        return "大失败"
    
    # 普通成功/失败
    if roll_value <= skill_value:
        return "成功"
    else:
        return "失败"


def skill_check_with_rule(roll_value: int, skill_value: int, rule_type: int = 1) -> str:
    """
    使用指定规则判断检定结果
    
    Args:
        roll_value: 掷骰值
        skill_value: 技能值
        rule_type: 规则类型 (1-5)
    
    Returns:
        结果类型: "大成功" / "成功" / "失败" / "大失败"
    """
    rules = {
        1: {"critical_success": [1], "critical_fail": list(range(96, 101))},
        2: {"critical_success": list(range(1, 6)), "critical_fail": list(range(96, 101))},
        3: {"critical_success": [1], "critical_fail": [100]},
        4: {"critical_success": list(range(1, 6)), "critical_fail": [100]},
        5: {"critical_success": [1], "critical_fail": [99, 100]},
    }
    
    rule = rules.get(rule_type, rules[1])
    
    if roll_value in rule["critical_success"]:
        return "大成功"
    if roll_value in rule["critical_fail"]:
        if roll_value > skill_value or skill_value < 50:
            return "大失败"
    
    if roll_value <= skill_value:
        return "成功"
    else:
        return "失败"


def sanity_check(current_san: int, success_formula: str, fail_formula: str) -> tuple[int, int, str]:
    """
    理智检定 (SAN Check)
    
    Args:
        current_san: 当前理智值
        success_formula: 成功损失公式 (如 "1d6")
        fail_formula: 失败损失公式 (如 "1d10")
    
    Returns:
        (roll_value, loss, result_type): 掷骰值、损失值、结果类型
    """
    roll_value = random.randint(1, 100)
    
    if roll_value <= current_san:
        # 成功
        result = roll_expression(success_formula)
        loss = result.total
        return roll_value, loss, "成功"
    else:
        # 失败
        result = roll_expression(fail_formula)
        loss = result.total
        return roll_value, loss, "失败"


def roll_initiative(faces: int = 20, adjust: int = 0) -> int:
    """
    掷先攻
    
    Args:
        faces: 骰子面数
        adjust: 调整值
    
    Returns:
        先攻值
    """
    return random.randint(1, faces) + adjust


def fireball(ring: int) -> str:
    """
    火球术伤害计算
    
    Args:
        ring: 法术环数 (3-20)
    
    Returns:
        伤害结果描述
    """
    ring = max(3, min(ring, 20))
    dice_count = ring * 2  # 每环2d6
    
    result = roll_dice(dice_count, 6)
    damage = result.total
    
    return f"{ring}环火球术: {dice_count}d6 = {damage} 火焰伤害"


def roll_RP(user_id: str) -> str:
    """
    今日人品
    
    Args:
        user_id: 用户ID
    
    Returns:
        人品值描述
    """
    # 使用用户ID作为种子，确保同一天同一用户结果相同
    import hashlib
    import datetime
    
    today = datetime.date.today().isoformat()
    seed = f"{user_id}_{today}"
    seed_hash = int(hashlib.md5(seed.encode()).hexdigest(), 16)
    
    random.seed(seed_hash)
    rp = random.randint(1, 100)
    random.seed()  # 重置随机种子
    
    # 人品描述
    if rp >= 90:
        desc = "今天运气爆棚！"
    elif rp >= 70:
        desc = "今天运气不错哦！"
    elif rp >= 50:
        desc = "今天运气一般般~"
    elif rp >= 30:
        desc = "今天可能要小心一点..."
    else:
        desc = "今天建议不要出门..."
    
    return f"今日人品: {rp}\n{desc}"
