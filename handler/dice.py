"""掷骰命令处理器"""

from ..component.dice import roll, roll_initiative, fireball, roll_RP
from ..component.output import get_default_output


class DiceHandler:
    """掷骰命令混合类"""
    
    async def roll_cmd(self, **kwargs):
        """基础掷骰"""
        matched = kwargs.get("matched_groups", {})
        expr = (matched.get("expr") or "").strip()
        stream_id = kwargs.get("stream_id", "")
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
                text = f"{nickname}掷骰 {expr}:\n" + '\n'.join(lines)
            else:
                # 判断大成功/大失败（针对 d100）
                is_d100 = "d100" in expr.lower() or "d%" in expr.lower()
                is_single_dice = result.total <= 100  # 单次掷骰结果
                
                if is_d100 and is_single_dice:
                    if result.total == 1:
                        text = get_default_output(
                            "dice.critical_success",
                            name=nickname,
                            result=result.detail,
                            total=result.total,
                        )
                    elif result.total == 100:
                        text = get_default_output(
                            "dice.critical_fail",
                            name=nickname,
                            result=result.detail,
                            total=result.total,
                        )
                    else:
                        text = get_default_output(
                            "dice.success",
                            name=nickname,
                            result=result.detail,
                            total=result.total,
                        )
                else:
                    text = get_default_output(
                        "dice.success",
                        name=nickname,
                        result=result.detail,
                        total=result.total,
                    )
            
            text = await self._beautify(text, stream_id)
            await self._log_dice(group_id, nickname, text)
            await self.ctx.send.text(text, stream_id)
            return True, text, 1
            
        except ValueError as e:
            await self.ctx.send.text(f"掷骰失败: {e}", stream_id)
            return False, str(e), 0
    
    async def hidden_roll_cmd(self, **kwargs):
        """暗骰"""
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
            
            await self.ctx.send.text("进行了一次暗骰", stream_id)
            
            try:
                private_stream = await self.ctx.chat.get_stream_by_user_id(user_id)
                if private_stream:
                    private_stream_id = private_stream.get("stream_id", "")
                    if private_stream_id:
                        await self.ctx.send.text(text, private_stream_id)
                    else:
                        await self.ctx.send.text("私聊发送失败", stream_id)
                else:
                    await self.ctx.send.text("请先与机器人私聊", stream_id)
            except Exception as e:
                await self.ctx.send.text(f"私聊发送失败: {e}", stream_id)
            
            return True, "暗骰已发送", 1
            
        except ValueError as e:
            await self.ctx.send.text(f"掷骰失败: {e}", stream_id)
            return False, str(e), 0
    
    async def initiative_cmd(self, **kwargs):
        """掷先攻"""
        matched = kwargs.get("matched_groups", {})
        args_str = (matched.get("args") or "").strip()
        stream_id = kwargs.get("stream_id", "")
        nickname = kwargs.get("message", {}).get("user_info", {}).get("user_nickname", "调查员")
        group_id = kwargs.get("message", {}).get("group_id", "")
        
        if group_id not in self._initiatives:
            self._initiatives[group_id] = []
        
        try:
            if not args_str:
                value = roll_initiative()
                adjust = 0
            else:
                if args_str.startswith('+') or args_str.startswith('-'):
                    adjust = int(args_str)
                    value = roll_initiative(adjust=adjust)
                else:
                    try:
                        value = int(args_str)
                        adjust = 0
                    except ValueError:
                        value = roll_initiative()
                        adjust = 0
                        nickname = args_str
            
            self._initiatives[group_id].append((nickname, value, False))
            self._initiatives[group_id].sort(key=lambda x: x[1], reverse=True)
            
            if adjust != 0:
                text = get_default_output(
                    "initiative.roll_adjust",
                    nickname=nickname,
                    roll=value,
                    adjust=adjust,
                )
            else:
                text = get_default_output(
                    "initiative.roll",
                    nickname=nickname,
                    roll=value,
                )
            
            text = await self._beautify(text, stream_id)
            await self.ctx.send.text(text, stream_id)
            return True, text, 1
            
        except Exception as e:
            await self.ctx.send.text(f"先攻掷骰失败: {e}", stream_id)
            return False, str(e), 0
    
    async def init_list_cmd(self, **kwargs):
        """先攻列表管理"""
        matched = kwargs.get("matched_groups", {})
        args_str = (matched.get("args") or "").strip()
        stream_id = kwargs.get("stream_id", "")
        nickname = kwargs.get("message", {}).get("user_info", {}).get("user_nickname", "调查员")
        group_id = kwargs.get("message", {}).get("group_id", "")
        
        if group_id not in self._initiatives:
            self._initiatives[group_id] = []
        
        if not args_str:
            if not self._initiatives[group_id]:
                text = get_default_output("initiative.empty")
            else:
                lines = []
                for i, (name, value, acted) in enumerate(self._initiatives[group_id], 1):
                    status = "✓" if acted else "→"
                    lines.append(f"{i}. {status} {name} (先攻: {value})")
                text = get_default_output("initiative.list", list='\n'.join(lines))
                
        elif args_str == "clr":
            self._initiatives[group_id] = []
            text = get_default_output("initiative.cleared")
            
        elif args_str.startswith("del"):
            parts = args_str.split()
            name = parts[1] if len(parts) > 1 else nickname
            self._initiatives[group_id] = [
                (n, v, a) for n, v, a in self._initiatives[group_id] if n != name
            ]
            text = get_default_output("initiative.deleted", name=name)
            
        else:
            text = "用法: .init [clr|del 角色名]"
        
        await self.ctx.send.text(text, stream_id)
        return True, text, 1
    
    async def end_turn_cmd(self, **kwargs):
        """结束当前回合"""
        stream_id = kwargs.get("stream_id", "")
        group_id = kwargs.get("message", {}).get("group_id", "")
        
        if group_id not in self._initiatives or not self._initiatives[group_id]:
            await self.ctx.send.text(get_default_output("initiative.empty"), stream_id)
            return False, "先攻列表为空", 0
        
        for i, (name, value, acted) in enumerate(self._initiatives[group_id]):
            if not acted:
                self._initiatives[group_id][i] = (name, value, True)
                break
        
        all_acted = all(acted for _, _, acted in self._initiatives[group_id])
        
        if all_acted:
            self._initiatives[group_id] = [
                (name, value, False) for name, value, _ in self._initiatives[group_id]
            ]
            first_name = self._initiatives[group_id][0][0]
            text = get_default_output("initiative.turn_start", first_char=first_name)
        else:
            for name, value, acted in self._initiatives[group_id]:
                if not acted:
                    text = get_default_output("initiative.turn_end", next_char=name)
                    break
        
        text = await self._beautify(text, stream_id)
        await self.ctx.send.text(text, stream_id)
        return True, text, 1
    
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
    
    async def jrrp_cmd(self, **kwargs):
        """今日人品"""
        stream_id = kwargs.get("stream_id", "")
        user_id = kwargs.get("message", {}).get("user_info", {}).get("user_id", "")
        
        result = roll_RP(user_id)
        result = await self._beautify(result, stream_id)
        await self.ctx.send.text(result, stream_id)
        return True, result, 1
