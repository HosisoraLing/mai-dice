"""LLM 工具函数处理器"""

from ..component.dice import roll, skill_check


class ToolHandler:
    """LLM 工具函数混合类"""
    
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
