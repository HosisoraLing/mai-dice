"""
MaiBot TRPG 骰娘插件

支持:
- 基础掷骰 (NdM, 复杂算式, 保留骰, 重复掷骰)
- 技能检定 (普通/奖励骰/惩罚骰)
- 人物卡管理
- 理智检定 (SAN Check)
- 先攻系统
- 日志系统
- CoC/DnD 角色生成
- LLM 美化模式
"""

import time
import random
from typing import Any, ClassVar

from maibot_sdk import MaiBotPlugin, Command, Tool, PluginConfigBase, Field, CONFIG_RELOAD_SCOPE_SELF
from maibot_sdk.types import ToolParameterInfo, ToolParamType

from .component.dice import roll, skill_check, sanity_check, roll_initiative, fireball, roll_RP
from .component.character import roll_character, format_character, roll_dnd_character, format_dnd_character
from .component.rules import COC_RULES
from .component.log import get_temporary_crazy_symptom, get_long_term_crazy_symptom
from .component.output import set_config, get_default_output
from .component.storage import StorageManager


# 配置模型
class PluginSectionConfig(PluginConfigBase):
    """插件基础配置"""

    __ui_label__ = "插件"
    __ui_icon__ = "package"
    __ui_order__ = 0

    enabled: bool = Field(default=True, description="是否启用插件")
    config_version: str = Field(default="1.0.0", description="配置版本")


class DiceConfig(PluginConfigBase):
    """骰子设置"""

    __ui_label__ = "骰子设置"
    __ui_icon__ = "dice"
    __ui_order__ = 1

    default_faces: int = Field(default=100, description="默认骰子面数")
    max_dice_count: int = Field(default=100, description="最大骰子数量")
    max_faces: int = Field(default=10000, description="最大骰子面数")


class OutputConfig(PluginConfigBase):
    """输出模板"""

    __ui_label__ = "输出模板"
    __ui_icon__ = "message-square"
    __ui_order__ = 2

    roll_result: str = Field(
        default="{nickname}掷骰 {expression} = {result}",
        description="掷骰结果模板"
    )


class LLMConfig(PluginConfigBase):
    """LLM 美化配置"""

    __ui_label__ = "LLM 美化"
    __ui_icon__ = "sparkles"
    __ui_order__ = 3

    enabled: bool = Field(default=False, description="是否启用 LLM 美化模式")
    system_prompt: str = Field(
        default="你是一个跑团骰娘，风格活泼可爱。请用简短生动的语言描述掷骰结果。",
        description="LLM 系统提示词"
    )


class NapCatConfig(PluginConfigBase):
    """NapCat 配置"""

    __ui_label__ = "NapCat 设置"
    __ui_icon__ = "webhook"
    __ui_order__ = 4

    enable_recall_listener: bool = Field(default=False, description="是否启用撤回监听")
    ws_url: str = Field(default="ws://127.0.0.1:3001", description="NapCat WebSocket 地址")
    token: str = Field(default="", description="NapCat WebSocket Token")


class TRPGDiceConfig(PluginConfigBase):
    """TRPG 骰娘配置"""

    plugin: PluginSectionConfig = Field(default_factory=PluginSectionConfig)
    dice: DiceConfig = Field(default_factory=DiceConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)
    llm_mode: LLMConfig = Field(default_factory=LLMConfig)
    napcat: NapCatConfig = Field(default_factory=NapCatConfig)


class TRPGDicePlugin(MaiBotPlugin):
    """TRPG 骰娘插件"""
    
    config_model = TRPGDiceConfig
    
    def __init__(self):
        super().__init__()
        self.storage: StorageManager | None = None
        self.recall_listener = None
        # 先攻列表: group_id -> [(name, value, acted), ...]
        self._initiatives: dict[str, list[tuple[str, int, bool]]] = {}
    
    async def on_load(self) -> None:
        """插件加载"""
        from pathlib import Path
        
        # 获取插件数据目录
        plugin_dir = Path(__file__).parent
        data_dir = str(plugin_dir / "data" / "storage")
        
        self.storage = StorageManager(self.ctx, data_dir)
        await self.storage.initialize()
        set_config(self.get_plugin_config_data())
        
        # 启动撤回监听器
        await self._start_recall_listener()
        
        self.ctx.logger.info("TRPG 骰娘插件已加载")
    
    async def on_unload(self) -> None:
        """插件卸载"""
        # 停止撤回监听器
        await self._stop_recall_listener()
        self.ctx.logger.info("TRPG 骰娘插件已卸载")
    
    async def _start_recall_listener(self) -> None:
        """启动撤回监听器"""
        if not self.config.napcat.enable_recall_listener:
            return
        
        try:
            from .component.recall_listener import create_recall_listener
            
            self.recall_listener = create_recall_listener(
                ws_url=self.config.napcat.ws_url,
                token=self.config.napcat.token,
                on_recall=self._on_message_recall,
            )
            
            if self.recall_listener:
                await self.recall_listener.start()
                self.ctx.logger.info(f"撤回监听器已启动: {self.config.napcat.ws_url}")
            else:
                self.ctx.logger.warning("撤回监听器启动失败，请安装 websockets: pip install websockets")
                
        except Exception as e:
            self.ctx.logger.error(f"启动撤回监听器失败: {e}")
    
    async def _stop_recall_listener(self) -> None:
        """停止撤回监听器"""
        if self.recall_listener:
            await self.recall_listener.stop()
            self.recall_listener = None
    
    async def _on_message_recall(self, group_id: str, message_id: str) -> None:
        """处理消息撤回事件"""
        try:
            if self.storage:
                deleted = await self.storage.delete_message_by_id(group_id, message_id)
                if deleted:
                    self.ctx.logger.info(f"已从日志中删除撤回的消息: group={group_id}, msg_id={message_id}")
        except Exception as e:
            self.ctx.logger.error(f"处理撤回事件失败: {e}")
    
    async def on_config_update(self, scope: str, config_data: dict, version: str) -> None:
        """配置更新"""
        if scope == CONFIG_RELOAD_SCOPE_SELF:
            set_config(config_data)
            self.ctx.logger.info("配置已更新")
    
    async def _beautify(self, raw_text: str, stream_id: str = "") -> str:
        """LLM 美化"""
        if not self.config.llm_mode.enabled:
            return raw_text
        
        try:
            prov = self.ctx.llm
            if not prov:
                return raw_text
            
            system_prompt = self.config.llm_mode.system_prompt or "你是一个跑团骰娘，风格活泼可爱。请用简短生动的语言描述掷骰结果。"
            
            result = await prov.generate(
                prompt=raw_text,
                system_prompt=system_prompt,
            )
            # generate 返回 dict: {"success": True, "response": "...", ...}
            if isinstance(result, dict) and result.get("success"):
                return result.get("response", raw_text)
            return raw_text
        except Exception:
            return raw_text
    
    async def _log_dice(self, group_id: str, nickname: str, text: str) -> None:
        """记录骰子结果到日志"""
        if group_id and self.storage:
            await self.storage.add_log_message(
                group_id=group_id,
                user_id="Bot",
                nickname=nickname,
                content=text,
                is_dice=True,
            )
    
    # ==================== 基础掷骰命令 ====================
    
    @Command("r", pattern=r"^[。.](?:r|R)\s*(?P<expr>.*)?$", aliases=["。r", "/r"])
    async def roll_cmd(self, **kwargs):
        """基础掷骰"""
        matched = kwargs.get("matched_groups", {})
        expr = (matched.get("expr") or "").strip()
        stream_id = kwargs.get("stream_id", "")
        nickname = kwargs.get("message", {}).get("user_info", {}).get("user_nickname", "调查员")
        group_id = kwargs.get("message", {}).get("group_id", "")
        
        if not expr:
            await self.ctx.send.text("用法: .r <表达式>\n示例: .r 1d100, .r 3d6+5", stream_id)
            return
        
        try:
            result = roll(expr)
            
            if isinstance(result, list):
                # 重复掷骰
                lines = []
                for i, r in enumerate(result, 1):
                    lines.append(f"第{i}次: {r.detail} = {r.total}")
                text = f"{nickname}掷骰 {expr}:\n" + '\n'.join(lines)
            else:
                # 单次掷骰
                text = get_default_output(
                    "roll_result",
                    nickname=nickname,
                    expression=expr,
                    result=result.total,
                    detail=result.detail,
                )
            
            text = await self._beautify(text, stream_id)
            await self._log_dice(group_id, nickname, text)
            await self.ctx.send.text(text, stream_id)
            return True, text, 1
            
        except ValueError as e:
            await self.ctx.send.text(f"掷骰失败: {e}", stream_id)
            return False, str(e), 0
    
    # ==================== 暗骰命令 ====================
    
    @Command("dh", pattern=r"^[。.](?:dh|DH)\s*(?P<expr>.*)?$", aliases=["。dh", "/dh"])
    async def hidden_roll_cmd(self, **kwargs):
        """暗骰 - 结果仅私聊发送"""
        matched = kwargs.get("matched_groups", {})
        expr = (matched.get("expr") or "").strip()
        stream_id = kwargs.get("stream_id", "")
        user_id = kwargs.get("message", {}).get("user_info", {}).get("user_id", "")
        nickname = kwargs.get("message", {}).get("user_info", {}).get("user_nickname", "调查员")
        group_id = kwargs.get("message", {}).get("group_id", "")
        
        if not expr:
            expr = "1d100"
        
        try:
            result = roll(expr)
            
            if isinstance(result, list):
                lines = []
                for i, r in enumerate(result, 1):
                    lines.append(f"第{i}次: {r.detail} = {r.total}")
                text = f"暗骰结果:\n" + '\n'.join(lines)
            else:
                text = f"暗骰结果: {expr} = {result.total}\n{result.detail}"
            
            # 在群里发送提示
            await self.ctx.send.text(f"{nickname} 进行了一次暗骰", stream_id)
            
            # 获取私聊流并发送结果
            try:
                private_stream = await self.ctx.chat.get_stream_by_user_id(user_id)
                if private_stream:
                    private_stream_id = private_stream.get("stream_id", "")
                    if private_stream_id:
                        await self.ctx.send.text(text, private_stream_id)
                    else:
                        await self.ctx.send.text("私聊发送失败，无法获取 stream_id", stream_id)
                else:
                    await self.ctx.send.text("私聊发送失败，请先与机器人私聊", stream_id)
            except Exception as e:
                await self.ctx.send.text(f"私聊发送失败: {e}", stream_id)
            
            return True, "暗骰已发送", 1
            
        except ValueError as e:
            await self.ctx.send.text(f"掷骰失败: {e}", stream_id)
            return False, str(e), 0
    
    # ==================== 技能检定命令 ====================
    
    @Command("ra", pattern=r"^[。.](?:ra|RA)\s+(?P<skill>.+?)(?:\s+(?P<value>\d+))?$", aliases=["。ra", "/ra"])
    async def skill_check_cmd(self, **kwargs):
        """技能检定"""
        matched = kwargs.get("matched_groups", {})
        skill_name = (matched.get("skill") or "").strip()
        skill_value = int(matched.get("value") or "50")
        stream_id = kwargs.get("stream_id", "")
        nickname = kwargs.get("message", {}).get("user_info", {}).get("user_nickname", "调查员")
        group_id = kwargs.get("message", {}).get("group_id", "")
        
        try:
            roll_value, result_type = skill_check(skill_value)
            text = get_default_output(
                f"skill_check_{'success' if '成功' in result_type else 'fail'}",
                nickname=nickname,
                skill_name=skill_name,
                roll=roll_value,
                skill_value=skill_value,
                result_type=result_type,
            )
            
            # 如果是大成功或大失败，使用对应的模板
            if result_type == "大成功":
                text = get_default_output(
                    "skill_critical_success",
                    nickname=nickname,
                    skill_name=skill_name,
                    roll=roll_value,
                    skill_value=skill_value,
                )
            elif result_type == "大失败":
                text = get_default_output(
                    "skill_critical_fail",
                    nickname=nickname,
                    skill_name=skill_name,
                    roll=roll_value,
                    skill_value=skill_value,
                )
            
            text = await self._beautify(text, stream_id)
            await self._log_dice(group_id, nickname, text)
            await self.ctx.send.text(text, stream_id)
            return True, text, 1
            
        except Exception as e:
            await self.ctx.send.text(f"检定失败: {e}", stream_id)
            return False, str(e), 0
    
    @Command("rab", pattern=r"^[。.](?:rab|RAB)\s+(?P<dice>\d+)\s+(?P<skill>.+)$", aliases=["。rab", "/rab"])
    async def bonus_dice_cmd(self, **kwargs):
        """奖励骰检定"""
        matched = kwargs.get("matched_groups", {})
        dice_count = int(matched.get("dice") or "1")
        skill_name = (matched.get("skill") or "").strip()
        stream_id = kwargs.get("stream_id", "")
        user_id = kwargs.get("message", {}).get("user_info", {}).get("user_id", "")
        nickname = kwargs.get("message", {}).get("user_info", {}).get("user_nickname", "调查员")
        group_id = kwargs.get("message", {}).get("group_id", "")
        
        # 从人物卡获取技能值，如果没有则使用默认值
        char = await self.storage.get_character(user_id, group_id)
        skill_value = char["skills"].get(skill_name, 50) if char else 50
        
        try:
            roll_value, result_type = skill_check(skill_value, bonus_dice=dice_count)
            text = get_default_output(
                "skill_bonus_dice",
                nickname=nickname,
                skill_name=skill_name,
                dice_count=dice_count,
                roll=roll_value,
                skill_value=skill_value,
                result_type=result_type,
            )
            
            text = await self._beautify(text, stream_id)
            await self._log_dice(group_id, nickname, text)
            await self.ctx.send.text(text, stream_id)
            return True, text, 1
            
        except Exception as e:
            await self.ctx.send.text(f"检定失败: {e}", stream_id)
            return False, str(e), 0
    
    @Command("rap", pattern=r"^[。.](?:rap|RAP)\s+(?P<dice>\d+)\s+(?P<skill>.+)$", aliases=["。rap", "/rap"])
    async def penalty_dice_cmd(self, **kwargs):
        """惩罚骰检定"""
        matched = kwargs.get("matched_groups", {})
        dice_count = int(matched.get("dice") or "1")
        skill_name = (matched.get("skill") or "").strip()
        stream_id = kwargs.get("stream_id", "")
        user_id = kwargs.get("message", {}).get("user_info", {}).get("user_id", "")
        nickname = kwargs.get("message", {}).get("user_info", {}).get("user_nickname", "调查员")
        group_id = kwargs.get("message", {}).get("group_id", "")
        
        # 从人物卡获取技能值
        char = await self.storage.get_character(user_id, group_id)
        skill_value = char["skills"].get(skill_name, 50) if char else 50
        
        try:
            roll_value, result_type = skill_check(skill_value, penalty_dice=dice_count)
            text = get_default_output(
                "skill_penalty_dice",
                nickname=nickname,
                skill_name=skill_name,
                dice_count=dice_count,
                roll=roll_value,
                skill_value=skill_value,
                result_type=result_type,
            )
            
            text = await self._beautify(text, stream_id)
            await self._log_dice(group_id, nickname, text)
            await self.ctx.send.text(text, stream_id)
            return True, text, 1
            
        except Exception as e:
            await self.ctx.send.text(f"检定失败: {e}", stream_id)
            return False, str(e), 0
    
    # ==================== 理智检定命令 ====================
    
    @Command("sc", pattern=r"^[。.](?:sc|SC)\s+(?P<success>.+?)/(?P<fail>.+)$", aliases=["。sc", "/sc"])
    async def sanity_check_cmd(self, **kwargs):
        """理智检定"""
        matched = kwargs.get("matched_groups", {})
        success_formula = (matched.get("success") or "").strip()
        fail_formula = (matched.get("fail") or "").strip()
        stream_id = kwargs.get("stream_id", "")
        nickname = kwargs.get("message", {}).get("user_info", {}).get("user_nickname", "调查员")
        user_id = kwargs.get("message", {}).get("user_info", {}).get("user_id", "")
        group_id = kwargs.get("message", {}).get("group_id", "")
        
        # 从人物卡获取当前 SAN 值
        char = await self.storage.get_character(user_id, group_id)
        current_san = char["attributes"].get("san", 50) if char else 50
        
        try:
            roll_value, loss, result_type = sanity_check(current_san, success_formula, fail_formula)
            
            # 计算新的 SAN 值
            new_san = max(0, current_san - loss)
            
            # 更新人物卡
            if char:
                attributes = char["attributes"]
                attributes["san"] = new_san
                await self.storage.save_character(
                    name=char["name"],
                    user_id=user_id,
                    group_id=group_id,
                    attributes=attributes,
                    skills=char["skills"],
                    extras=char["extras"],
                    is_current=True,
                )
            
            if result_type == "成功":
                text = get_default_output(
                    "san_success",
                    nickname=nickname,
                    roll=roll_value,
                    san_value=current_san,
                    loss=loss,
                )
            else:
                text = get_default_output(
                    "san_fail",
                    nickname=nickname,
                    roll=roll_value,
                    san_value=current_san,
                    loss=loss,
                )
            
            # 检查是否归零
            if new_san == 0:
                text += "\n" + get_default_output("san_check_zero")
            
            text = await self._beautify(text, stream_id)
            await self._log_dice(group_id, nickname, text)
            await self.ctx.send.text(text, stream_id)
            return True, text, 1
            
        except Exception as e:
            await self.ctx.send.text(f"理智检定失败: {e}", stream_id)
            return False, str(e), 0
    
    @Command("ti", pattern=r"^[。.](?:ti|TI)$", aliases=["。ti", "/ti"])
    async def temporary_crazy_cmd(self, **kwargs):
        """临时疯狂"""
        stream_id = kwargs.get("stream_id", "")
        nickname = kwargs.get("message", {}).get("user_info", {}).get("user_nickname", "调查员")
        group_id = kwargs.get("message", {}).get("group_id", "")
        
        symptom = get_temporary_crazy_symptom()
        text = get_default_output("temporary_crazy", symptom=symptom)
        text = f"{nickname}\n" + text
        
        text = await self._beautify(text, stream_id)
        await self._log_dice(group_id, nickname, text)
        await self.ctx.send.text(text, stream_id)
        return True, text, 1
    
    @Command("li", pattern=r"^[。.](?:li|LI)$", aliases=["。li", "/li"])
    async def long_term_crazy_cmd(self, **kwargs):
        """长期疯狂"""
        stream_id = kwargs.get("stream_id", "")
        nickname = kwargs.get("message", {}).get("user_info", {}).get("user_nickname", "调查员")
        group_id = kwargs.get("message", {}).get("group_id", "")
        
        symptom = get_long_term_crazy_symptom()
        text = get_default_output("long_term_crazy", symptom=symptom)
        text = f"{nickname}\n" + text
        
        text = await self._beautify(text, stream_id)
        await self._log_dice(group_id, nickname, text)
        await self.ctx.send.text(text, stream_id)
        return True, text, 1
    
    # ==================== 人物卡命令 ====================
    
    @Command("pc", pattern=r"^[。.](?:pc|PC)\s+(?P<args>.+)$", aliases=["。pc", "/pc"])
    async def character_cmd(self, **kwargs):
        """人物卡管理"""
        matched = kwargs.get("matched_groups", {})
        args_str = (matched.get("args") or "").strip()
        stream_id = kwargs.get("stream_id", "")
        user_id = kwargs.get("message", {}).get("user_info", {}).get("user_id", "")
        group_id = kwargs.get("message", {}).get("group_id", "")
        
        args = args_str.split()
        if not args:
            await self.ctx.send.text("用法: .pc <create|show|list|change|delete|update> [参数]", stream_id)
            return
        
        action = args[0].lower()
        
        try:
            if action == "create":
                if len(args) < 2:
                    await self.ctx.send.text("用法: .pc create <名称>", stream_id)
                    return
                name = args[1]
                
                # 检查是否已存在
                existing = await self.storage.get_character(user_id, group_id, name)
                if existing:
                    text = get_default_output("character_exists", name=name)
                else:
                    await self.storage.save_character(
                        name=name,
                        user_id=user_id,
                        group_id=group_id,
                        attributes={},
                        skills={},
                        extras={},
                        is_current=True,
                    )
                    text = get_default_output("character_created", name=name)
                
            elif action == "show":
                char = await self.storage.get_character(user_id, group_id)
                if not char:
                    text = get_default_output("character_no_current")
                else:
                    attrs = '\n'.join(f"{k}: {v}" for k, v in char["attributes"].items()) if char["attributes"] else "无"
                    skills = '\n'.join(f"{k}: {v}" for k, v in char["skills"].items()) if char["skills"] else "无"
                    text = f"【{char['name']}】\n属性:\n{attrs}\n技能:\n{skills}"
                    
            elif action == "list":
                chars = await self.storage.list_characters(user_id, group_id)
                if not chars:
                    text = "你还没有创建人物卡"
                else:
                    lines = []
                    for c in chars:
                        marker = " →" if c["is_current"] else ""
                        lines.append(f"- {c['name']}{marker}")
                    text = "你的人物卡:\n" + '\n'.join(lines)
                    
            elif action == "change":
                if len(args) < 2:
                    await self.ctx.send.text("用法: .pc change <名称>", stream_id)
                    return
                name = args[1]
                
                # 检查人物卡是否存在
                char = await self.storage.get_character(user_id, group_id, name)
                if char:
                    await self.storage.switch_character(user_id, group_id, name)
                    text = get_default_output("character_switched", name=name)
                else:
                    text = get_default_output("character_not_found", name=name)
                    
            elif action == "delete":
                if len(args) < 2:
                    await self.ctx.send.text("用法: .pc delete <名称>", stream_id)
                    return
                name = args[1]
                
                # 检查人物卡是否存在
                char = await self.storage.get_character(user_id, group_id, name)
                if char:
                    await self.storage.delete_character(user_id, group_id, name)
                    text = get_default_output("character_deleted", name=name)
                else:
                    text = get_default_output("character_not_found", name=name)
                    
            elif action == "update":
                if len(args) < 3:
                    await self.ctx.send.text("用法: .pc update <属性> <值/公式>", stream_id)
                    return
                
                char = await self.storage.get_character(user_id, group_id)
                if not char:
                    text = get_default_output("character_no_current")
                else:
                    attr_name = args[1]
                    value_str = args[2]
                    
                    # 支持骰子公式
                    if 'd' in value_str.lower():
                        result = roll(value_str)
                        value = result.total if not isinstance(result, list) else result[0].total
                    else:
                        value = int(value_str)
                    
                    # 更新属性
                    attributes = char["attributes"]
                    attributes[attr_name] = value
                    
                    await self.storage.save_character(
                        name=char["name"],
                        user_id=user_id,
                        group_id=group_id,
                        attributes=attributes,
                        skills=char["skills"],
                        extras=char["extras"],
                        is_current=True,
                    )
                    text = f"已更新 {char['name']} 的 {attr_name} 为 {value}"
                    
            else:
                text = "未知操作，可用: create, show, list, change, delete, update"
            
            text = await self._beautify(text, stream_id)
            await self.ctx.send.text(text, stream_id)
            return True, text, 1
            
        except Exception as e:
            await self.ctx.send.text(f"操作失败: {e}", stream_id)
            return False, str(e), 0
    
    @Command("st", pattern=r"^[。.](?:st|ST)\s+(?P<attr>.+?)[\s\-]+(?P<value>.+)$", aliases=["。st", "/st"])
    async def set_attr_cmd(self, **kwargs):
        """设置属性"""
        matched = kwargs.get("matched_groups", {})
        attr_name = (matched.get("attr") or "").strip()
        value_str = (matched.get("value") or "").strip()
        stream_id = kwargs.get("stream_id", "")
        user_id = kwargs.get("message", {}).get("user_info", {}).get("user_id", "")
        group_id = kwargs.get("message", {}).get("group_id", "")
        
        char = await self.storage.get_character(user_id, group_id)
        if not char:
            await self.ctx.send.text(get_default_output("character_no_current"), stream_id)
            return
        
        try:
            # 支持骰子公式
            if 'd' in value_str.lower():
                result = roll(value_str)
                value = result.total if not isinstance(result, list) else result[0].total
            else:
                # 支持 +/- 语法
                if value_str.startswith('+') or value_str.startswith('-'):
                    current = char["attributes"].get(attr_name, 0)
                    value = current + int(value_str)
                else:
                    value = int(value_str)
            
            # 更新属性
            attributes = char["attributes"]
            attributes[attr_name] = value
            
            await self.storage.save_character(
                name=char["name"],
                user_id=user_id,
                group_id=group_id,
                attributes=attributes,
                skills=char["skills"],
                extras=char["extras"],
                is_current=True,
            )
            
            await self.ctx.send.text(f"已更新 {char['name']} 的 {attr_name} 为 {value}", stream_id)
            return True, f"已更新 {attr_name}", 1
            
        except Exception as e:
            await self.ctx.send.text(f"设置属性失败: {e}", stream_id)
            return False, str(e), 0
    
    # ==================== 先攻系统命令 ====================
    
    @Command("ri", pattern=r"^[。.](?:ri|RI)(?:\s+(?P<args>.+))?$", aliases=["。ri", "/ri"])
    async def initiative_cmd(self, **kwargs):
        """掷先攻"""
        matched = kwargs.get("matched_groups", {})
        args_str = (matched.get("args") or "").strip()
        stream_id = kwargs.get("stream_id", "")
        user_id = kwargs.get("message", {}).get("user_info", {}).get("user_id", "")
        nickname = kwargs.get("message", {}).get("user_info", {}).get("user_nickname", "调查员")
        group_id = kwargs.get("message", {}).get("group_id", "")
        
        if group_id not in self._initiatives:
            self._initiatives[group_id] = []
        
        try:
            if not args_str:
                # 掷先攻
                value = roll_initiative()
                adjust = 0
            else:
                # 解析参数
                if args_str.startswith('+') or args_str.startswith('-'):
                    adjust = int(args_str)
                    value = roll_initiative(adjust=adjust)
                else:
                    try:
                        value = int(args_str)
                        adjust = 0
                    except ValueError:
                        # 可能是角色名
                        value = roll_initiative()
                        adjust = 0
                        nickname = args_str
            
            # 添加到先攻列表
            self._initiatives[group_id].append((nickname, value, False))
            self._initiatives[group_id].sort(key=lambda x: x[1], reverse=True)
            
            if adjust != 0:
                text = get_default_output(
                    "initiative_roll_adjust",
                    nickname=nickname,
                    roll=value,
                    adjust=adjust,
                )
            else:
                text = get_default_output(
                    "initiative_roll",
                    nickname=nickname,
                    roll=value,
                )
            
            text = await self._beautify(text, stream_id)
            await self.ctx.send.text(text, stream_id)
            return True, text, 1
            
        except Exception as e:
            await self.ctx.send.text(f"先攻掷骰失败: {e}", stream_id)
            return False, str(e), 0
    
    @Command("init", pattern=r"^[。.](?:init|INIT)(?:\s+(?P<args>.+))?$", aliases=["。init", "/init"])
    async def init_list_cmd(self, **kwargs):
        """先攻列表管理"""
        matched = kwargs.get("matched_groups", {})
        args_str = (matched.get("args") or "").strip()
        stream_id = kwargs.get("stream_id", "")
        user_id = kwargs.get("message", {}).get("user_info", {}).get("user_id", "")
        nickname = kwargs.get("message", {}).get("user_info", {}).get("user_nickname", "调查员")
        group_id = kwargs.get("message", {}).get("group_id", "")
        
        if group_id not in self._initiatives:
            self._initiatives[group_id] = []
        
        if not args_str:
            # 显示先攻列表
            if not self._initiatives[group_id]:
                text = get_default_output("initiative_empty")
            else:
                lines = []
                for i, (name, value, acted) in enumerate(self._initiatives[group_id], 1):
                    status = "✓" if acted else "→"
                    lines.append(f"{i}. {status} {name} (先攻: {value})")
                text = get_default_output("initiative_list", list='\n'.join(lines))
                
        elif args_str == "clr":
            # 清空先攻列表
            self._initiatives[group_id] = []
            text = get_default_output("initiative_cleared")
            
        elif args_str.startswith("del"):
            # 删除角色
            parts = args_str.split()
            if len(parts) > 1:
                name = parts[1]
            else:
                name = nickname
            
            self._initiatives[group_id] = [
                (n, v, a) for n, v, a in self._initiatives[group_id] if n != name
            ]
            text = get_default_output("initiative_deleted", name=name)
            
        else:
            text = "用法: .init [clr|del 角色名]"
        
        await self.ctx.send.text(text, stream_id)
        return True, text, 1
    
    @Command("ed", pattern=r"^[。.](?:ed|ED)$", aliases=["。ed", "/ed"])
    async def end_turn_cmd(self, **kwargs):
        """结束当前回合"""
        stream_id = kwargs.get("stream_id", "")
        group_id = kwargs.get("message", {}).get("group_id", "")
        
        if group_id not in self._initiatives or not self._initiatives[group_id]:
            await self.ctx.send.text(get_default_output("initiative_empty"), stream_id)
            return
        
        # 标记当前角色已行动
        for i, (name, value, acted) in enumerate(self._initiatives[group_id]):
            if not acted:
                self._initiatives[group_id][i] = (name, value, True)
                break
        
        # 检查是否所有人都行动了
        all_acted = all(acted for _, _, acted in self._initiatives[group_id])
        
        if all_acted:
            # 新回合
            self._initiatives[group_id] = [
                (name, value, False) for name, value, _ in self._initiatives[group_id]
            ]
            first_name = self._initiatives[group_id][0][0]
            text = get_default_output("initiative_turn_start", first_char=first_name)
        else:
            # 找到下一个未行动的角色
            for name, value, acted in self._initiatives[group_id]:
                if not acted:
                    text = get_default_output("initiative_turn_end", next_char=name)
                    break
        
        text = await self._beautify(text, stream_id)
        await self.ctx.send.text(text, stream_id)
        return True, text, 1
    
    # ==================== 角色生成命令 ====================
    
    @Command("coc", pattern=r"^[。.](?:coc|COC)(?:\s+(?P<count>\d+))?$", aliases=["。coc", "/coc"])
    async def coc_character_cmd(self, **kwargs):
        """生成 CoC 角色"""
        matched = kwargs.get("matched_groups", {})
        count = int(matched.get("count") or "1")
        stream_id = kwargs.get("stream_id", "")
        
        count = min(count, 10)  # 最多10个
        
        characters = [roll_character() for _ in range(count)]
        results = []
        for i, char in enumerate(characters):
            results.append(format_character(char, index=i+1))
        
        text = get_default_output("coc_character", index="", characters="\n\n".join(results))
        if count == 1:
            text = results[0]
        
        text = await self._beautify(text, stream_id)
        await self.ctx.send.text(text, stream_id)
        return True, text, 1
    
    @Command("dnd", pattern=r"^[。.](?:dnd|DND)(?:\s+(?P<count>\d+))?$", aliases=["。dnd", "/dnd"])
    async def dnd_character_cmd(self, **kwargs):
        """生成 DnD 角色"""
        matched = kwargs.get("matched_groups", {})
        count = int(matched.get("count") or "1")
        stream_id = kwargs.get("stream_id", "")
        
        count = min(count, 10)
        
        characters = [roll_dnd_character() for _ in range(count)]
        results = []
        for i, char in enumerate(characters):
            results.append(format_dnd_character(char, index=i+1))
        
        text = get_default_output("dnd_character", index="", characters="\n\n".join(results))
        if count == 1:
            text = results[0]
        
        text = await self._beautify(text, stream_id)
        await self.ctx.send.text(text, stream_id)
        return True, text, 1
    
    @Command("en", pattern=r"^[。.](?:en|EN)\s+(?P<skill>.+?)(?:\s+(?P<value>\d+))?$", aliases=["。en", "/en"])
    async def skill_growth_cmd(self, **kwargs):
        """技能成长"""
        matched = kwargs.get("matched_groups", {})
        skill_name = (matched.get("skill") or "").strip()
        skill_value = int(matched.get("value") or "0")
        stream_id = kwargs.get("stream_id", "")
        user_id = kwargs.get("message", {}).get("user_info", {}).get("user_id", "")
        group_id = kwargs.get("message", {}).get("group_id", "")
        
        char = await self.storage.get_character(user_id, group_id)
        if not char:
            await self.ctx.send.text(get_default_output("character_no_current"), stream_id)
            return
        
        # 如果没有指定技能值，从人物卡获取
        if skill_value == 0:
            skill_value = char["skills"].get(skill_name, 0)
        
        try:
            roll_value = random.randint(1, 100)
            
            if roll_value > skill_value:
                # 成长
                growth_roll = random.randint(1, 10)
                new_value = min(99, skill_value + growth_roll)
                
                # 更新技能
                skills = char["skills"]
                skills[skill_name] = new_value
                await self.storage.save_character(
                    name=char["name"],
                    user_id=user_id,
                    group_id=group_id,
                    attributes=char["attributes"],
                    skills=skills,
                    extras=char["extras"],
                    is_current=True,
                )
                
                text = get_default_output(
                    "skill_growth_success",
                    skill_name=skill_name,
                    roll=roll_value,
                    skill_value=skill_value,
                    growth=growth_roll,
                    new_value=new_value,
                )
            else:
                text = get_default_output(
                    "skill_growth_fail",
                    skill_name=skill_name,
                    roll=roll_value,
                    skill_value=skill_value,
                )
            
            text = await self._beautify(text, stream_id)
            await self.ctx.send.text(text, stream_id)
            return True, text, 1
            
        except Exception as e:
            await self.ctx.send.text(f"技能成长检定失败: {e}", stream_id)
            return False, str(e), 0
    
    # ==================== 日志管理命令 ====================
    
    @Command("log", pattern=r"^[。.](?:log|LOG)\s*(?P<args>.*)?$", aliases=["。log", "/log"])
    async def log_cmd(self, **kwargs):
        """日志管理"""
        matched = kwargs.get("matched_groups", {})
        args_str = (matched.get("args") or "").strip()
        stream_id = kwargs.get("stream_id", "")
        group_id = kwargs.get("message", {}).get("group_id", "")
        
        args = args_str.split()
        if not args:
            await self.ctx.send.text(
                "日志命令:\n"
                ".log new <名称> - 创建新日志\n"
                ".log on - 恢复日志\n"
                ".log off - 暂停日志\n"
                ".log end - 结束日志\n"
                ".log del <名称> - 删除日志\n"
                ".log list - 列出日志\n"
                ".log export [名称] - 导出日志",
                stream_id
            )
            return
        
        action = args[0].lower()
        
        try:
            if action == "new":
                if len(args) < 2:
                    await self.ctx.send.text("用法: .log new <日志名>", stream_id)
                    return
                log_name = args[1]
                success, msg = await self.storage.create_log(group_id, log_name)
                text = msg
                
            elif action == "on":
                name = args[1] if len(args) > 1 else None
                success, msg = await self.storage.resume_log(group_id, name)
                text = msg
                    
            elif action == "off":
                success, msg = await self.storage.pause_log(group_id)
                text = msg
                    
            elif action == "end":
                success, msg, log = await self.storage.end_log(group_id)
                text = msg
                    
            elif action in ("del", "delete", "halt"):
                if len(args) < 2:
                    # 如果没有指定名称，删除未完成的会话
                    success, msg = await self.storage.halt_log(group_id)
                    text = msg
                else:
                    log_name = args[1]
                    success, msg = await self.storage.delete_log(group_id, log_name)
                    text = msg
                    
            elif action == "list":
                lines = await self.storage.list_logs(group_id)
                text = "日志列表:\n" + '\n'.join(lines)
                    
            elif action in ("export", "get"):
                if len(args) < 2:
                    text = "用法: .log export <日志名>"
                    await self.ctx.send.text(text, stream_id)
                else:
                    log_name = args[1]
                    success, msg, content = await self.storage.export_log(group_id, log_name)
                    if success and content:
                        # 发送文件
                        import base64
                        file_b64 = base64.b64encode(content).decode("utf-8")
                        filename = f"{group_id}_{log_name}.json"
                        await self.ctx.send.custom(
                            "file",
                            {"file": file_b64, "filename": filename},
                            stream_id,
                        )
                        await self.ctx.send.text(msg, stream_id)
                    else:
                        await self.ctx.send.text(f"导出失败: {msg}", stream_id)
                return
                    
            else:
                text = "未知操作，可用: new, on, off, end, del, list, export"
            
            await self.ctx.send.text(text, stream_id)
            return True, text, 1
            
        except Exception as e:
            await self.ctx.send.text(f"日志操作失败: {e}", stream_id)
            return False, str(e), 0
    
    # ==================== 杂项命令 ====================
    
    @Command("setcoc", pattern=r"^[。.](?:setcoc|SETCOC)(?:\s+(?P<args>.+))?$", aliases=["。setcoc", "/setcoc"])
    async def setcoc_cmd(self, **kwargs):
        """设置 CoC 规则"""
        matched = kwargs.get("matched_groups", {})
        command = (matched.get("args") or " ").strip()
        stream_id = kwargs.get("stream_id", "")
        group_id = kwargs.get("message", {}).get("group_id", "")
        
        try:
            if command.strip() == " ":
                # 显示当前规则
                config = await self.storage.get_group_config(group_id)
                current = config.get("coc_rule", 1)
                text = f"当前使用规则{current}（{COC_RULES[current]['name']}）\n可选规则: 1-5"
            else:
                # 设置规则
                rule_type = int(command)
                if rule_type < 1 or rule_type > 5:
                    text = "规则编号必须是1-5的数字"
                else:
                    await self.storage.set_coc_rule(group_id, rule_type)
                    text = f"已切换到规则{rule_type}（{COC_RULES[rule_type]['name']}）"
            
            await self.ctx.send.text(text, stream_id)
            return True, text, 1
            
        except ValueError:
            await self.ctx.send.text("规则编号必须是1-5的数字", stream_id)
            return False, "规则编号必须是1-5的数字", 0
        except Exception as e:
            await self.ctx.send.text(f"设置规则失败: {e}", stream_id)
            return False, str(e), 0
    
    @Command("fireball", pattern=r"^[。.](?:fireball|FIREBALL)(?:\s+(?P<ring>\d+))?$", aliases=["。fireball", "/fireball"])
    async def fireball_cmd(self, **kwargs):
        """火球术"""
        matched = kwargs.get("matched_groups", {})
        ring = int(matched.get("ring") or "3")
        stream_id = kwargs.get("stream_id", "")
        
        ring = max(3, min(ring, 20))
        result = fireball(ring)
        result = await self._beautify(result, stream_id)
        await self.ctx.send.text(result, stream_id)
        return True, result, 1
    
    @Command("jrrp", pattern=r"^[。.](?:jrrp|JRRP)$", aliases=["。jrrp", "/jrrp"])
    async def jrrp_cmd(self, **kwargs):
        """今日人品"""
        stream_id = kwargs.get("stream_id", "")
        user_id = kwargs.get("message", {}).get("user_info", {}).get("user_id", "")
        
        result = roll_RP(user_id)
        result = await self._beautify(result, stream_id)
        await self.ctx.send.text(result, stream_id)
        return True, result, 1
    
    @Command("dicehelp", pattern=r"^[。.](?:dicehelp|help|DICEHELP|HELP)$", aliases=["。dicehelp", "/dicehelp", ".help", "/help"])
    async def help_cmd(self, **kwargs):
        """帮助信息"""
        stream_id = kwargs.get("stream_id", "")
        
        help_text = get_default_output("help")
        await self.ctx.send.text(help_text, stream_id)
        return True, help_text, 1
    
    # ==================== LLM 工具函数 ====================
    
    @Tool(
        "roll_dice",
        description="掷骰子，支持多种格式如 1d100、3d6+5、10d6k5 等",
        parameters=[
            ToolParameterInfo(
                name="expression",
                param_type=ToolParamType.STRING,
                description="掷骰表达式，如 1d100、3d6+2d4",
                required=True,
            ),
            ToolParameterInfo(
                name="stream_id",
                param_type=ToolParamType.STRING,
                description="聊天流ID",
                required=True,
            ),
        ],
    )
    async def roll_dice_tool(self, expression: str, stream_id: str, **kwargs):
        """掷骰工具"""
        del kwargs
        try:
            result = roll(expression)
            
            if isinstance(result, list):
                lines = []
                for i, r in enumerate(result, 1):
                    lines.append(f"第{i}次: {r.detail} = {r.total}")
                text = f"掷骰 {expression}:\n" + '\n'.join(lines)
            else:
                text = f"掷骰 {expression} = {result.total}\n{result.detail}"
            
            await self.ctx.send.text(text, stream_id)
            return {"success": True, "content": text}
            
        except Exception as e:
            return {"success": False, "content": f"掷骰失败: {e}"}
    
    @Tool(
        "skill_check",
        description="进行技能检定",
        parameters=[
            ToolParameterInfo(
                name="skill_name",
                param_type=ToolParamType.STRING,
                description="技能名称",
                required=True,
            ),
            ToolParameterInfo(
                name="skill_value",
                param_type=ToolParamType.INTEGER,
                description="技能值",
                required=False,
                default=50,
            ),
            ToolParameterInfo(
                name="bonus_dice",
                param_type=ToolParamType.INTEGER,
                description="奖励骰数量",
                required=False,
                default=0,
            ),
            ToolParameterInfo(
                name="penalty_dice",
                param_type=ToolParamType.INTEGER,
                description="惩罚骰数量",
                required=False,
                default=0,
            ),
            ToolParameterInfo(
                name="stream_id",
                param_type=ToolParamType.STRING,
                description="聊天流ID",
                required=True,
            ),
        ],
    )
    async def skill_check_tool(
        self,
        skill_name: str,
        skill_value: int,
        bonus_dice: int,
        penalty_dice: int,
        stream_id: str,
        **kwargs,
    ):
        """技能检定工具"""
        del kwargs
        try:
            roll_value, result_type = skill_check(skill_value, bonus_dice, penalty_dice)
            text = f"进行{skill_name}检定: {roll_value}/{skill_value} {result_type}！"
            
            await self.ctx.send.text(text, stream_id)
            return {"success": True, "content": text}
            
        except Exception as e:
            return {"success": False, "content": f"检定失败: {e}"}


def create_plugin():
    return TRPGDicePlugin()
