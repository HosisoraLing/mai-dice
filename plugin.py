"""
MaiDice - MaiBot TRPG 骰娘插件

支持:
- 基础掷骰 (NdM, 复杂算式, 保留骰, 重复掷骰, 暗骰)
- 技能检定 (普通/奖励骰/惩罚骰)
- 人物卡管理
- 理智检定 (SAN Check)
- 先攻系统
- 日志系统
- CoC/DnD 角色生成
- LLM 美化模式
"""

import time
from pathlib import Path

from maibot_sdk import MaiBotPlugin, Command, Tool, PluginConfigBase, Field, CONFIG_RELOAD_SCOPE_SELF
from maibot_sdk.types import ToolParameterInfo, ToolParamType

from .component.dice import roll_RP
from .component.output import set_config, get_default_output
from .component.storage import StorageManager
from .handler.dice import DiceHandler
from .handler.skill import SkillHandler
from .handler.character import CharacterHandler
from .handler.log import LogHandler
from .handler.misc import MiscHandler
from .handler.tool import ToolHandler


# ==================== 配置模型 ====================

class PluginSectionConfig(PluginConfigBase):
    """插件基础配置"""

    __ui_label__ = "插件"
    __ui_icon__ = "package"
    __ui_order__ = 0

    config_version: str = Field(default="1.0.0", description="配置版本号")
    enabled: bool = Field(default=True, description="是否启用插件")


class DiceConfig(PluginConfigBase):
    """骰子设置"""

    __ui_label__ = "骰子设置"
    __ui_icon__ = "dice"
    __ui_order__ = 1

    default_faces: int = Field(default=100, description="默认骰子面数")
    max_dice_count: int = Field(default=100, description="最大骰子数量")
    max_faces: int = Field(default=10000, description="最大骰子面数")


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


class DiceOutputConfig(PluginConfigBase):
    """掷骰输出模板"""

    __ui_label__ = "掷骰输出"
    __ui_icon__ = "message-square"
    __ui_order__ = 2

    success: str = Field(
        default="{name}掷骰 {result} = {total}",
        description="掷骰成功模板",
        json_schema_extra={"placeholder": "可用变量: {name} {result} {total}"}
    )
    critical_success: str = Field(
        default="{name}掷骰 {result} = {total} 大成功！",
        description="大成功模板"
    )
    critical_fail: str = Field(
        default="{name}掷骰 {result} = {total} 大失败！",
        description="大失败模板"
    )


class SkillOutputConfig(PluginConfigBase):
    """技能检定输出模板"""

    __ui_label__ = "技能检定输出"
    __ui_icon__ = "check-circle"
    __ui_order__ = 2

    success: str = Field(
        default="{nickname}进行{skill_name}检定: {roll}/{skill_value} 成功！",
        description="检定成功模板"
    )
    fail: str = Field(
        default="{nickname}进行{skill_name}检定: {roll}/{skill_value} 失败！",
        description="检定失败模板"
    )
    critical_success: str = Field(
        default="{nickname}进行{skill_name}检定: {roll}/{skill_value} 大成功！",
        description="大成功模板"
    )
    critical_fail: str = Field(
        default="{nickname}进行{skill_name}检定: {roll}/{skill_value} 大失败！",
        description="大失败模板"
    )


class OutputConfig(PluginConfigBase):
    """输出模板配置"""

    __ui_label__ = "文案设置"
    __ui_icon__ = "edit"
    __ui_order__ = 2

    dice: DiceOutputConfig = Field(default_factory=DiceOutputConfig)
    skill: SkillOutputConfig = Field(default_factory=SkillOutputConfig)


class MaiDiceConfig(PluginConfigBase):
    """MaiDice 配置"""

    plugin: PluginSectionConfig = Field(default_factory=PluginSectionConfig)
    dice: DiceConfig = Field(default_factory=DiceConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)
    llm_mode: LLMConfig = Field(default_factory=LLMConfig)
    napcat: NapCatConfig = Field(default_factory=NapCatConfig)


# ==================== 插件主类 ====================

class MaiDicePlugin(
    MaiBotPlugin,
    DiceHandler,
    SkillHandler,
    CharacterHandler,
    LogHandler,
    MiscHandler,
    ToolHandler,
):
    """MaiDice 插件"""
    
    config_model = MaiDiceConfig
    
    def __init__(self):
        super().__init__()
        self.storage: StorageManager | None = None
        self.recall_listener = None
        self._initiatives: dict[str, list[tuple[str, int, bool]]] = {}
    
    async def on_load(self) -> None:
        """插件加载"""
        plugin_dir = Path(__file__).parent
        data_dir = str(plugin_dir / "data" / "storage")
        
        self.storage = StorageManager(self.ctx, data_dir)
        await self.storage.initialize()
        set_config(self.get_plugin_config_data())
        
        await self._start_recall_listener()
        
        self.ctx.logger.info("MaiDice 插件已加载")
    
    async def on_unload(self) -> None:
        """插件卸载"""
        await self._stop_recall_listener()
        self.ctx.logger.info("MaiDice 插件已卸载")
    
    async def on_config_update(self, scope: str, config_data: dict, version: str) -> None:
        """配置更新"""
        if scope == CONFIG_RELOAD_SCOPE_SELF:
            set_config(config_data)
            self.ctx.logger.info("配置已更新")
    
    # ==================== 辅助方法 ====================
    
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
                self.ctx.logger.warning("撤回监听器启动失败，请安装 websockets")
                
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
    
    async def _beautify(self, raw_text: str, stream_id: str = "") -> str:
        """LLM 美化"""
        if not self.config.llm_mode.enabled:
            return raw_text
        
        try:
            prov = self.ctx.llm
            if not prov:
                return raw_text
            
            system_prompt = self.config.llm_mode.system_prompt or "你是一个跑团骰娘，风格活泼可爱。请用简短生动的语言描述掷骰结果。"
            
            result = await prov.generate(prompt=raw_text, system_prompt=system_prompt)
            if isinstance(result, dict) and result.get("success"):
                return result.get("response", raw_text)
            return raw_text
        except Exception:
            return raw_text
    
    async def _log_dice(self, group_id: str, nickname: str, text: str) -> None:
        """记录骰子结果到日志"""
        if group_id and self.storage:
            await self.storage.add_log_message(
                group_id=group_id, user_id="Bot", nickname=nickname, content=text, is_dice=True,
            )
    
    # ==================== 掷骰命令 ====================
    
    @Command("r", pattern=r"^[。.](?:r|R)\s*(?P<expr>.*)?$", aliases=["。r", "/r"])
    async def roll_cmd(self, **kwargs):
        return await DiceHandler.roll_cmd(self, **kwargs)
    
    @Command("dh", pattern=r"^[。.](?:dh|DH)\s*(?P<expr>.*)?$", aliases=["。dh", "/dh"])
    async def hidden_roll_cmd(self, **kwargs):
        return await DiceHandler.hidden_roll_cmd(self, **kwargs)
    
    @Command("ri", pattern=r"^[。.](?:ri|RI)(?:\s+(?P<args>.+))?$", aliases=["。ri", "/ri"])
    async def initiative_cmd(self, **kwargs):
        return await DiceHandler.initiative_cmd(self, **kwargs)
    
    @Command("init", pattern=r"^[。.](?:init|INIT)(?:\s+(?P<args>.+))?$", aliases=["。init", "/init"])
    async def init_list_cmd(self, **kwargs):
        return await DiceHandler.init_list_cmd(self, **kwargs)
    
    @Command("ed", pattern=r"^[。.](?:ed|ED)$", aliases=["。ed", "/ed"])
    async def end_turn_cmd(self, **kwargs):
        return await DiceHandler.end_turn_cmd(self, **kwargs)
    
    @Command("fireball", pattern=r"^[。.](?:fireball|FIREBALL)(?:\s+(?P<ring>\d+))?$", aliases=["。fireball", "/fireball"])
    async def fireball_cmd(self, **kwargs):
        return await DiceHandler.fireball_cmd(self, **kwargs)
    
    @Command("jrrp", pattern=r"^[。.](?:jrrp|JRRP)$", aliases=["。jrrp", "/jrrp"])
    async def jrrp_cmd(self, **kwargs):
        return await DiceHandler.jrrp_cmd(self, **kwargs)
    
    # ==================== 技能检定命令 ====================
    
    @Command("ra", pattern=r"^[。.](?:ra|RA)\s+(?P<skill>.+?)(?:\s+(?P<value>\d+))?$", aliases=["。ra", "/ra"])
    async def skill_check_cmd(self, **kwargs):
        return await SkillHandler.skill_check_cmd(self, **kwargs)
    
    @Command("rab", pattern=r"^[。.](?:rab|RAB)\s+(?P<dice>\d+)\s+(?P<skill>.+)$", aliases=["。rab", "/rab"])
    async def bonus_dice_cmd(self, **kwargs):
        return await SkillHandler.bonus_dice_cmd(self, **kwargs)
    
    @Command("rap", pattern=r"^[。.](?:rap|RAP)\s+(?P<dice>\d+)\s+(?P<skill>.+)$", aliases=["。rap", "/rap"])
    async def penalty_dice_cmd(self, **kwargs):
        return await SkillHandler.penalty_dice_cmd(self, **kwargs)
    
    @Command("sc", pattern=r"^[。.](?:sc|SC)\s+(?P<success>.+?)/(?P<fail>.+)$", aliases=["。sc", "/sc"])
    async def sanity_check_cmd(self, **kwargs):
        return await SkillHandler.sanity_check_cmd(self, **kwargs)
    
    @Command("ti", pattern=r"^[。.](?:ti|TI)$", aliases=["。ti", "/ti"])
    async def temporary_crazy_cmd(self, **kwargs):
        return await SkillHandler.temporary_crazy_cmd(self, **kwargs)
    
    @Command("li", pattern=r"^[。.](?:li|LI)$", aliases=["。li", "/li"])
    async def long_term_crazy_cmd(self, **kwargs):
        return await SkillHandler.long_term_crazy_cmd(self, **kwargs)
    
    @Command("en", pattern=r"^[。.](?:en|EN)\s+(?P<skill>.+?)(?:\s+(?P<value>\d+))?$", aliases=["。en", "/en"])
    async def skill_growth_cmd(self, **kwargs):
        return await SkillHandler.skill_growth_cmd(self, **kwargs)
    
    # ==================== 人物卡命令 ====================
    
    @Command("pc", pattern=r"^[。.](?:pc|PC)\s+(?P<args>.+)$", aliases=["。pc", "/pc"])
    async def character_cmd(self, **kwargs):
        return await CharacterHandler.character_cmd(self, **kwargs)
    
    @Command("st", pattern=r"^[。.](?:st|ST)\s+(?P<attr>.+?)[\s\-]+(?P<value>.+)$", aliases=["。st", "/st"])
    async def set_attr_cmd(self, **kwargs):
        return await CharacterHandler.set_attr_cmd(self, **kwargs)
    
    @Command("coc", pattern=r"^[。.](?:coc|COC)(?:\s+(?P<count>\d+))?$", aliases=["。coc", "/coc"])
    async def coc_character_cmd(self, **kwargs):
        return await CharacterHandler.coc_character_cmd(self, **kwargs)
    
    @Command("dnd", pattern=r"^[。.](?:dnd|DND)(?:\s+(?P<count>\d+))?$", aliases=["。dnd", "/dnd"])
    async def dnd_character_cmd(self, **kwargs):
        return await CharacterHandler.dnd_character_cmd(self, **kwargs)
    
    # ==================== 日志命令 ====================
    
    @Command("log", pattern=r"^[。.](?:log|LOG)\s*(?P<args>.*)?$", aliases=["。log", "/log"])
    async def log_cmd(self, **kwargs):
        return await LogHandler.log_cmd(self, **kwargs)
    
    # ==================== 杂项命令 ====================
    
    @Command("setcoc", pattern=r"^[。.](?:setcoc|SETCOC)(?:\s+(?P<args>.+))?$", aliases=["。setcoc", "/setcoc"])
    async def setcoc_cmd(self, **kwargs):
        return await MiscHandler.setcoc_cmd(self, **kwargs)
    
    @Command("dicehelp", pattern=r"^[。.](?:dicehelp|help|DICEHELP|HELP)$", aliases=["。dicehelp", "/dicehelp", ".help", "/help"])
    async def help_cmd(self, **kwargs):
        return await MiscHandler.help_cmd(self, **kwargs)
    
    # ==================== LLM 工具 ====================
    
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
        return await ToolHandler.roll_dice_tool(self, expression, stream_id, **kwargs)
    
    @Tool(
        "skill_check",
        description="进行技能检定",
        parameters=[
            ToolParameterInfo(name="skill_name", param_type=ToolParamType.STRING, description="技能名称", required=True),
            ToolParameterInfo(name="skill_value", param_type=ToolParamType.INTEGER, description="技能值", required=False, default=50),
            ToolParameterInfo(name="bonus_dice", param_type=ToolParamType.INTEGER, description="奖励骰数量", required=False, default=0),
            ToolParameterInfo(name="penalty_dice", param_type=ToolParamType.INTEGER, description="惩罚骰数量", required=False, default=0),
            ToolParameterInfo(name="stream_id", param_type=ToolParamType.STRING, description="聊天流ID", required=True),
        ],
    )
    async def skill_check_tool(self, skill_name: str, skill_value: int, bonus_dice: int, penalty_dice: int, stream_id: str, **kwargs):
        return await ToolHandler.skill_check_tool(self, skill_name, skill_value, bonus_dice, penalty_dice, stream_id, **kwargs)


def create_plugin():
    return MaiDicePlugin()
