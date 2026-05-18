"""
输出格式化模块

管理所有输出模板，支持变量替换
"""

from typing import Any


# 全局配置引用
_config: dict[str, Any] = {}


def set_config(config: Any) -> None:
    """设置配置引用"""
    global _config
    _config = config


def get_config(path: str, default: Any = None) -> Any:
    """
    获取配置值
    
    Args:
        path: 配置路径，用 . 分隔，如 "output.roll_result"
        default: 默认值
    
    Returns:
        配置值
    """
    keys = path.split('.')
    value = _config
    
    for key in keys:
        if isinstance(value, dict):
            value = value.get(key)
        elif hasattr(value, key):
            value = getattr(value, key)
        else:
            return default
        
        if value is None:
            return default
    
    return value


def get_output(template_name: str, **kwargs) -> str:
    """
    获取格式化的输出文本
    
    Args:
        template_name: 模板名称，如 "output.roll_result"
        **kwargs: 模板变量
    
    Returns:
        格式化后的文本
    """
    template = get_config(template_name, "")
    
    if not template:
        return str(kwargs)
    
    try:
        return template.format(**kwargs)
    except KeyError as e:
        return f"模板变量缺失: {e}"


# 预定义模板
TEMPLATES = {
    # 掷骰相关
    "roll_result": "{nickname}掷骰 {expression} = {result}",
    "roll_detail": "{nickname}掷骰 {expression} = {result}\n{detail}",
    
    # 技能检定相关
    "skill_check_success": "{nickname}进行{skill_name}检定: {roll}/{skill_value} 成功！",
    "skill_check_fail": "{nickname}进行{skill_name}检定: {roll}/{skill_value} 失败！",
    "skill_critical_success": "{nickname}进行{skill_name}检定: {roll}/{skill_value} 大成功！",
    "skill_critical_fail": "{nickname}进行{skill_name}检定: {roll}/{skill_value} 大失败！",
    "skill_bonus_dice": "{nickname}进行{skill_name}检定(奖励骰x{dice_count}): {roll}/{skill_value} {result_type}！",
    "skill_penalty_dice": "{nickname}进行{skill_name}检定(惩罚骰x{dice_count}): {roll}/{skill_value} {result_type}！",
    
    # SAN Check 相关
    "san_success": "{nickname}进行理智检定: {roll}/{san_value} 成功！理智损失{loss}点。",
    "san_fail": "{nickname}进行理智检定: {roll}/{san_value} 失败！理智损失{loss}点。",
    
    # 人物卡相关
    "character_created": "人物卡「{name}」创建成功！",
    "character_switched": "已切换到人物卡「{name}」",
    "character_deleted": "人物卡「{name}」已删除",
    "character_not_found": "未找到人物卡「{name}」",
    "character_exists": "人物卡「{name}」已存在",
    "character_no_current": "当前没有选择人物卡，请先使用 .pc create 创建",
    
    # 先攻相关
    "initiative_roll": "{nickname}掷先攻: {roll}",
    "initiative_roll_adjust": "{nickname}掷先攻: {roll} (调整值{adjust:+d})",
    "initiative_list": "当前先攻顺序:\n{list}",
    "initiative_empty": "先攻列表为空",
    "initiative_turn_end": "当前回合结束，轮到 {next_char} 行动！",
    "initiative_turn_start": "新回合开始！{first_char} 先行动。",
    "initiative_deleted": "已从先攻列表中移除 {name}",
    "initiative_cleared": "先攻列表已清空",
    
    # 理智检定相关
    "san_check_success": "理智检定: {roll}/{san_value} 成功！理智损失 {loss} 点",
    "san_check_fail": "理智检定: {roll}/{san_value} 失败！理智损失 {loss} 点",
    "san_check_zero": "理智归零！调查员陷入永久疯狂！",
    
    # 临时疯狂
    "temporary_crazy": "【临时疯狂】\n{symptom}",
    
    # 长期疯狂
    "long_term_crazy": "【长期疯狂】\n{symptom}",
    
    # 技能成长
    "skill_growth_success": "技能「{skill_name}」成长检定: {roll}/{skill_value} 成功！技能值增加 {growth} 点，当前 {new_value}",
    "skill_growth_fail": "技能「{skill_name}」成长检定: {roll}/{skill_value} 失败，技能值不变",
    "skill_growth_max": "技能「{skill_name}」已达到上限",
    "skill_not_found": "未找到技能「{skill_name}」",
    
    # 日志相关
    "log_created": "日志「{log_name}」已创建并开始记录",
    "log_paused": "日志记录已暂停",
    "log_resumed": "日志记录已恢复",
    "log_ended": "日志记录已结束，共 {message_count} 条消息",
    "log_deleted": "日志「{log_name}」已删除",
    "log_not_found": "未找到日志「{log_name}」",
    "log_no_active": "当前没有活动的日志",
    "log_already_active": "日志记录已在进行中",
    
    # 角色生成相关
    "coc_character": "CoC 角色属性 #{index}:\n{stats}",
    "dnd_character": "DnD 角色属性 #{index}:\n{stats}",
    
    # 火球术
    "fireball": "{ring}环火球术: {dice_count}d6 = {damage} 火焰伤害",
    
    # 人品
    "jrrp": "今日人品: {rp}\n{desc}",
    
    # 错误提示
    "error_parse": "无法解析表达式: {expr}",
    "error_dice_count": "骰子数量不能超过 {max}",
    "error_dice_faces": "骰子面数不能超过 {max}",
    "error_invalid_command": "无效的命令格式",
    "error_permission_denied": "权限不足",
    
    # 帮助信息
    "help": """基础掷骰
`/r 1d100` - 掷 1 个 100 面骰
`/r 3d6+2d4-1d8` - 掷 3 个 6 面骰 + 2 个 4 面骰 - 1 个 8 面骰
`/r 3#1d20` - 掷 1d20 骰 3 次
`/r 10d6k5` - 掷 10 个 6 面骰，保留最高 5 个

人物卡管理
`/pc create 名称 属性值` - 创建人物卡
`/pc show` - 显示当前人物卡
`/pc list` - 列出所有人物卡
`/pc change 名称` - 切换当前人物卡
`/pc update 属性 值/公式` - 更新人物卡属性
`/pc delete 名称` - 删除人物卡

CoC 相关
`/coc x` - 生成 x 个 CoC 角色数据
`/ra 技能名` - 进行技能骰
`/rap n 技能名` - 带 n 个惩罚骰的技能骰
`/rab n 技能名` - 带 n 个奖励骰的技能骰
`/sc 1d6/1d10` - 进行 San Check
`/ti` - 生成临时疯狂症状
`/li` - 生成长期疯狂症状
`/en 技能名 [技能值]` - 技能成长
`/setcoc 规则编号` - 设置COC规则

先攻系统
`/init` - 显示当前先攻列表
`/init clr` - 清空先攻列表
`/init del [角色名]` - 删除角色先攻（默认为用户名）
`/ri +/- x` - 以x的调整值投掷先攻
`/ri x [角色名]` - 将角色（默认为用户名）的先攻设置为x
`/ed` - 结束当前回合

日志管理
`/log new <日志名>` - 开始新的日志会话
`/log off` - 暂停当前的日志会话
`/log on` - 开始当前的日志会话
`/log end` - 结束当前的日志会话
`/log del <日志名>` - 删除日志会话
`/log get <日志名>` - 获取日志会话
`/log stat <日志名>` - 获取日志会话统计信息""",
}


def get_default_output(template_name: str, **kwargs) -> str:
    """
    获取默认模板的格式化输出
    
    Args:
        template_name: 模板名称
        **kwargs: 模板变量
    
    Returns:
        格式化后的文本
    """
    # 先尝试从配置获取
    config_template = get_config(f"output.{template_name}")
    if config_template:
        try:
            return config_template.format(**kwargs)
        except KeyError:
            pass
    
    # 使用默认模板
    template = TEMPLATES.get(template_name, "")
    if template:
        try:
            return template.format(**kwargs)
        except KeyError:
            pass
    
    # 兜底
    return str(kwargs)
