"""杂项命令处理器"""

from ..component.rules import COC_RULES
from ..component.output import get_default_output


class MiscHandler:
    """杂项命令混合类"""
    
    async def setcoc_cmd(self, **kwargs):
        """设置 CoC 规则"""
        matched = kwargs.get("matched_groups", {})
        command = (matched.get("args") or " ").strip()
        stream_id = kwargs.get("stream_id", "")
        group_id = kwargs.get("message", {}).get("group_id", "")
        
        try:
            if command.strip() == " ":
                config = await self.storage.get_group_config(group_id)
                current = config.get("coc_rule", 1)
                text = get_default_output("coc_rule.current", rule=current, rule_name=COC_RULES[current]["name"])
            else:
                rule_type = int(command)
                if rule_type < 1 or rule_type > 5:
                    text = "规则编号必须是1-5的数字"
                else:
                    await self.storage.set_coc_rule(group_id, rule_type)
                    text = get_default_output("coc_rule.switched", rule=rule_type, rule_name=COC_RULES[rule_type]["name"])
            
            await self.ctx.send.text(text, stream_id)
            return True, text, 1
            
        except ValueError:
            await self.ctx.send.text("规则编号必须是1-5的数字", stream_id)
            return False, "规则编号必须是1-5的数字", 0
        except Exception as e:
            await self.ctx.send.text(f"设置规则失败: {e}", stream_id)
            return False, str(e), 0
    
    async def help_cmd(self, **kwargs):
        """帮助信息"""
        stream_id = kwargs.get("stream_id", "")
        
        help_text = get_default_output("help")
        await self.ctx.send.text(help_text, stream_id)
        return True, help_text, 1
