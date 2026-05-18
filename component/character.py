"""
人物卡管理模块

支持:
- 创建/删除/切换人物卡
- 查看/更新属性
- 列出所有人物卡
"""

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class Character:
    """人物卡"""
    name: str  # 角色名称
    user_id: str  # 用户ID
    group_id: str  # 群组ID
    attributes: dict[str, int] = field(default_factory=dict)  # 属性
    skills: dict[str, int] = field(default_factory=dict)  # 技能
    extras: dict[str, Any] = field(default_factory=dict)  # 其他信息
    created_at: int = 0  # 创建时间戳
    updated_at: int = 0  # 更新时间戳

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "name": self.name,
            "user_id": self.user_id,
            "group_id": self.group_id,
            "attributes": self.attributes,
            "skills": self.skills,
            "extras": self.extras,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Character':
        """从字典创建"""
        return cls(
            name=data.get("name", ""),
            user_id=data.get("user_id", ""),
            group_id=data.get("group_id", ""),
            attributes=data.get("attributes", {}),
            skills=data.get("skills", {}),
            extras=data.get("extras", {}),
            created_at=data.get("created_at", 0),
            updated_at=data.get("updated_at", 0),
        )

    def get_attr(self, name: str, default: int = 0) -> int:
        """获取属性值"""
        return self.attributes.get(name.lower(), default)

    def set_attr(self, name: str, value: int) -> None:
        """设置属性值"""
        self.attributes[name.lower()] = value

    def get_skill(self, name: str, default: int = 0) -> int:
        """获取技能值"""
        return self.skills.get(name.lower(), default)

    def set_skill(self, name: str, value: int) -> None:
        """设置技能值"""
        self.skills[name.lower()] = value


# CoC 标准属性名称
COC_ATTRIBUTES = {
    "力量": "str",
    "体质": "con",
    "体型": "siz",
    "敏捷": "dex",
    "外貌": "app",
    "智力": "int",
    "意志": "pow",
    "教育": "edu",
    "幸运": "luck",
    "san": "san",
    "理智": "san",
    "生命值": "hp",
    "魔法值": "mp",
    "体力": "mov",
}

# CoC 标准技能名称
COC_SKILLS = {
    "侦查": 25,
    "图书馆使用": 20,
    "聆听": 20,
    "医学": 1,
    "魅惑": 15,
    "恐吓": 15,
    "说服": 10,
    "话术": 5,
    "闪避": 0,
    "斗殴": 25,
    "手枪": 20,
    "步枪": 25,
    "急救": 30,
    "攀爬": 20,
    "跳跃": 20,
    "游泳": 20,
    "投掷": 20,
    "驾驶": 20,
    "导航": 10,
    "神秘学": 5,
    "历史": 5,
    "科学": 1,
    "法律": 5,
    "自然": 10,
    "计算机": 5,
    "艺术": 5,
    "手艺": 5,
    "母语": 0,
}


def normalize_attr_name(name: str) -> str:
    """标准化属性名称"""
    name_lower = name.lower()
    
    # 检查中文映射
    if name in COC_ATTRIBUTES:
        return COC_ATTRIBUTES[name]
    
    # 检查英文简写
    abbreviations = {
        "str": "str", "con": "con", "siz": "siz", "dex": "dex",
        "app": "app", "int": "int", "pow": "pow", "edu": "edu",
        "luck": "luck", "san": "san", "hp": "hp", "mp": "mp", "mov": "mov",
    }
    
    return abbreviations.get(name_lower, name_lower)


def roll_character() -> dict[str, int]:
    """
    生成 CoC 角色属性
    
    Returns:
        属性字典
    """
    import random
    
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
    import random
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


class CharacterManager:
    """人物卡管理器"""
    
    def __init__(self):
        self._characters: dict[str, Character] = {}
        self._current: dict[str, str] = {}  # user_id -> character_name
    
    def _get_key(self, user_id: str, group_id: str, name: str) -> str:
        """生成人物卡的唯一键"""
        return f"{user_id}:{group_id}:{name}"
    
    def create_character(self, name: str, user_id: str, group_id: str) -> Character:
        """创建人物卡"""
        key = self._get_key(user_id, group_id, name)
        
        if key in self._characters:
            raise ValueError(f"人物卡「{name}」已存在")
        
        import time
        char = Character(
            name=name,
            user_id=user_id,
            group_id=group_id,
            created_at=int(time.time()),
            updated_at=int(time.time()),
        )
        
        self._characters[key] = char
        
        # 自动切换到新创建的人物卡
        current_key = f"{user_id}:{group_id}"
        self._current[current_key] = name
        
        return char
    
    def get_character(self, user_id: str, group_id: str, name: Optional[str] = None) -> Optional[Character]:
        """获取人物卡"""
        if name is None:
            # 获取当前人物卡
            current_key = f"{user_id}:{group_id}"
            name = self._current.get(current_key)
            if name is None:
                return None
        
        key = self._get_key(user_id, group_id, name)
        return self._characters.get(key)
    
    def delete_character(self, user_id: str, group_id: str, name: str) -> bool:
        """删除人物卡"""
        key = self._get_key(user_id, group_id, name)
        
        if key not in self._characters:
            return False
        
        del self._characters[key]
        
        # 如果删除的是当前人物卡，清除当前选择
        current_key = f"{user_id}:{group_id}"
        if self._current.get(current_key) == name:
            del self._current[current_key]
        
        return True
    
    def switch_character(self, user_id: str, group_id: str, name: str) -> bool:
        """切换当前人物卡"""
        key = self._get_key(user_id, group_id, name)
        
        if key not in self._characters:
            return False
        
        current_key = f"{user_id}:{group_id}"
        self._current[current_key] = name
        return True
    
    def list_characters(self, user_id: str, group_id: str) -> list[Character]:
        """列出用户的所有人物卡"""
        prefix = f"{user_id}:{group_id}:"
        chars = []
        
        for key, char in self._characters.items():
            if key.startswith(prefix):
                chars.append(char)
        
        return chars
    
    def get_current_name(self, user_id: str, group_id: str) -> Optional[str]:
        """获取当前人物卡名称"""
        current_key = f"{user_id}:{group_id}"
        return self._current.get(current_key)
