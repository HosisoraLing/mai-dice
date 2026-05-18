"""
工具函数模块

包含角色生成等辅助功能
"""

import random
from typing import Any


def roll_character() -> dict[str, int]:
    """
    生成 CoC 角色属性
    
    Returns:
        属性字典
    """
    def roll_3d6():
        return (random.randint(1, 6) + random.randint(1, 6) + random.randint(1, 6)) * 5
    
    def roll_2d6_plus_6():
        return (random.randint(1, 6) + random.randint(1, 6) + 6) * 5
    
    attributes = {
        "力量": roll_3d6(),
        "体质": roll_3d6(),
        "体型": roll_2d6_plus_6(),
        "敏捷": roll_3d6(),
        "外貌": roll_3d6(),
        "智力": roll_2d6_plus_6(),
        "意志": roll_3d6(),
        "教育": roll_2d6_plus_6(),
        "幸运": roll_3d6(),
    }
    
    # 计算衍生属性
    attributes["生命值"] = (attributes["体质"] + attributes["体型"]) // 10
    attributes["魔法值"] = attributes["意志"] // 5
    attributes["理智"] = attributes["意志"]
    attributes["体力"] = (attributes["力量"] + attributes["敏捷"] + attributes["体型"]) // 3
    
    return attributes


def format_character(char: dict[str, int], index: int = 1) -> str:
    """格式化 CoC 角色属性"""
    lines = []
    lines.append(f"【{index}】")
    lines.append(f"力量:{char['力量']} 体质:{char['体质']} 体型:{char['体型']}")
    lines.append(f"敏捷:{char['敏捷']} 外貌:{char['外貌']} 智力:{char['智力']}")
    lines.append(f"意志:{char['意志']} 教育:{char['教育']} 幸运:{char['幸运']}")
    lines.append(f"HP:{char['生命值']} MP:{char['魔法值']} SAN:{char['理智']} MOV:{char['体力']}")
    lines.append(f"DB:{_calc_damage_bonus(char['力量'], char['体型'])}")
    
    return '\n'.join(lines)


def _calc_damage_bonus(str_val: int, siz_val: int) -> str:
    """计算伤害加成"""
    total = str_val + siz_val
    if total <= 64:
        return "-2"
    elif total <= 84:
        return "-1"
    elif total <= 124:
        return "0"
    elif total <= 164:
        return "+1d4"
    elif total <= 204:
        return "+1d6"
    elif total <= 284:
        return "+2d6"
    elif total <= 364:
        return "+3d6"
    else:
        return "+4d6"


def roll_dnd_attribute() -> int:
    """
    生成 DnD 单个属性（4d6取最高3个）
    """
    rolls = [random.randint(1, 6) for _ in range(4)]
    rolls.sort(reverse=True)
    return sum(rolls[:3])


def roll_dnd_character() -> dict[str, int]:
    """
    生成 DnD 角色属性
    
    Returns:
        属性字典
    """
    attributes = {
        "力量": roll_dnd_attribute(),
        "敏捷": roll_dnd_attribute(),
        "体质": roll_dnd_attribute(),
        "智力": roll_dnd_attribute(),
        "感知": roll_dnd_attribute(),
        "魅力": roll_dnd_attribute(),
    }
    return attributes


def format_dnd_character(char: dict[str, int], index: int = 1) -> str:
    """格式化 DnD 角色属性"""
    lines = []
    lines.append(f"【{index}】")
    lines.append(f"力量:{char['力量']}({(char['力量']-10)//2:+d})")
    lines.append(f"敏捷:{char['敏捷']}({(char['敏捷']-10)//2:+d})")
    lines.append(f"体质:{char['体质']}({(char['体质']-10)//2:+d})")
    lines.append(f"智力:{char['智力']}({(char['智力']-10)//2:+d})")
    lines.append(f"感知:{char['感知']}({(char['感知']-10)//2:+d})")
    lines.append(f"魅力:{char['魅力']}({(char['魅力']-10)//2:+d})")
    
    return '\n'.join(lines)


def parse_command_args(args_str: str) -> list[str]:
    """
    解析命令参数
    
    Args:
        args_str: 参数字符串
    
    Returns:
        参数列表
    """
    if not args_str:
        return []
    
    # 简单的空格分割
    return args_str.strip().split()


def format_initiative_list(initiatives: list[tuple[str, int, bool]]) -> str:
    """
    格式化先攻列表
    
    Args:
        initiatives: [(名称, 先攻值, 是否已行动), ...]
    
    Returns:
        格式化后的列表
    """
    if not initiatives:
        return "先攻列表为空"
    
    lines = []
    for i, (name, value, acted) in enumerate(initiatives, 1):
        status = "✓" if acted else "→"
        lines.append(f"{i}. {status} {name} (先攻: {value})")
    
    return '\n'.join(lines)
