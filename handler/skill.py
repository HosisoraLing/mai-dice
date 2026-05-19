"""技能检定命令处理器"""

from ..component.dice import skill_check, sanity_check
from ..component.log import get_temporary_crazy_symptom, get_long_term_crazy_symptom
from ..component.output import get_default_output


class SkillHandler:
    """技能检定命令混合类"""
    
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
            
            if result_type == "大成功":
                text = get_default_output("skill_check.critical_success", nickname=nickname, skill_name=skill_name, roll=roll_value, skill_value=skill_value)
            elif result_type == "大失败":
                text = get_default_output("skill_check.critical_fail", nickname=nickname, skill_name=skill_name, roll=roll_value, skill_value=skill_value)
            elif result_type == "成功":
                text = get_default_output("skill_check.success", nickname=nickname, skill_name=skill_name, roll=roll_value, skill_value=skill_value)
            else:
                text = get_default_output("skill_check.fail", nickname=nickname, skill_name=skill_name, roll=roll_value, skill_value=skill_value)
            
            text = await self._beautify(text, stream_id)
            await self._log_dice(group_id, nickname, text)
            await self.ctx.send.text(text, stream_id)
            return True, text, 1
            
        except Exception as e:
            await self.ctx.send.text(f"检定失败: {e}", stream_id)
            return False, str(e), 0
    
    async def bonus_dice_cmd(self, **kwargs):
        """奖励骰检定"""
        matched = kwargs.get("matched_groups", {})
        dice_count = int(matched.get("dice") or "1")
        skill_name = (matched.get("skill") or "").strip()
        stream_id = kwargs.get("stream_id", "")
        user_id = kwargs.get("message", {}).get("user_info", {}).get("user_id", "")
        nickname = kwargs.get("message", {}).get("user_info", {}).get("user_nickname", "调查员")
        group_id = kwargs.get("message", {}).get("group_id", "")
        
        char = await self.storage.get_character(user_id, group_id)
        skill_value = char["skills"].get(skill_name, 50) if char else 50
        
        try:
            roll_value, result_type = skill_check(skill_value, bonus_dice=dice_count)
            text = get_default_output(
                "skill_check.bonus_dice",
                nickname=nickname, skill_name=skill_name, dice_count=dice_count,
                roll=roll_value, skill_value=skill_value, result_type=result_type,
            )
            
            text = await self._beautify(text, stream_id)
            await self._log_dice(group_id, nickname, text)
            await self.ctx.send.text(text, stream_id)
            return True, text, 1
            
        except Exception as e:
            await self.ctx.send.text(f"检定失败: {e}", stream_id)
            return False, str(e), 0
    
    async def penalty_dice_cmd(self, **kwargs):
        """惩罚骰检定"""
        matched = kwargs.get("matched_groups", {})
        dice_count = int(matched.get("dice") or "1")
        skill_name = (matched.get("skill") or "").strip()
        stream_id = kwargs.get("stream_id", "")
        user_id = kwargs.get("message", {}).get("user_info", {}).get("user_id", "")
        nickname = kwargs.get("message", {}).get("user_info", {}).get("user_nickname", "调查员")
        group_id = kwargs.get("message", {}).get("group_id", "")
        
        char = await self.storage.get_character(user_id, group_id)
        skill_value = char["skills"].get(skill_name, 50) if char else 50
        
        try:
            roll_value, result_type = skill_check(skill_value, penalty_dice=dice_count)
            text = get_default_output(
                "skill_check.penalty_dice",
                nickname=nickname, skill_name=skill_name, dice_count=dice_count,
                roll=roll_value, skill_value=skill_value, result_type=result_type,
            )
            
            text = await self._beautify(text, stream_id)
            await self._log_dice(group_id, nickname, text)
            await self.ctx.send.text(text, stream_id)
            return True, text, 1
            
        except Exception as e:
            await self.ctx.send.text(f"检定失败: {e}", stream_id)
            return False, str(e), 0
    
    async def sanity_check_cmd(self, **kwargs):
        """理智检定"""
        matched = kwargs.get("matched_groups", {})
        success_formula = (matched.get("success") or "").strip()
        fail_formula = (matched.get("fail") or "").strip()
        stream_id = kwargs.get("stream_id", "")
        nickname = kwargs.get("message", {}).get("user_info", {}).get("user_nickname", "调查员")
        user_id = kwargs.get("message", {}).get("user_info", {}).get("user_id", "")
        group_id = kwargs.get("message", {}).get("group_id", "")
        
        char = await self.storage.get_character(user_id, group_id)
        current_san = char["attributes"].get("san", 50) if char else 50
        
        try:
            roll_value, loss, result_type = sanity_check(current_san, success_formula, fail_formula)
            new_san = max(0, current_san - loss)
            
            if char:
                attributes = char["attributes"]
                attributes["san"] = new_san
                await self.storage.save_character(
                    name=char["name"], user_id=user_id, group_id=group_id,
                    attributes=attributes, skills=char["skills"], extras=char["extras"], is_current=True,
                )
            
            if result_type == "成功":
                text = get_default_output("san_check.success", nickname=nickname, roll=roll_value, san_value=current_san, loss=loss)
            else:
                text = get_default_output("san_check.fail", nickname=nickname, roll=roll_value, san_value=current_san, loss=loss)
            
            if new_san == 0:
                text += "\n" + get_default_output("san_check.zero")
            
            text = await self._beautify(text, stream_id)
            await self._log_dice(group_id, nickname, text)
            await self.ctx.send.text(text, stream_id)
            return True, text, 1
            
        except Exception as e:
            await self.ctx.send.text(f"理智检定失败: {e}", stream_id)
            return False, str(e), 0
    
    async def temporary_crazy_cmd(self, **kwargs):
        """临时疯狂"""
        stream_id = kwargs.get("stream_id", "")
        nickname = kwargs.get("message", {}).get("user_info", {}).get("user_nickname", "调查员")
        group_id = kwargs.get("message", {}).get("group_id", "")
        
        symptom = get_temporary_crazy_symptom()
        text = get_default_output("crazy.temporary", symptom=symptom)
        text = f"{nickname}\n" + text
        
        text = await self._beautify(text, stream_id)
        await self._log_dice(group_id, nickname, text)
        await self.ctx.send.text(text, stream_id)
        return True, text, 1
    
    async def long_term_crazy_cmd(self, **kwargs):
        """长期疯狂"""
        stream_id = kwargs.get("stream_id", "")
        nickname = kwargs.get("message", {}).get("user_info", {}).get("user_nickname", "调查员")
        group_id = kwargs.get("message", {}).get("group_id", "")
        
        symptom = get_long_term_crazy_symptom()
        text = get_default_output("crazy.long_term", symptom=symptom)
        text = f"{nickname}\n" + text
        
        text = await self._beautify(text, stream_id)
        await self._log_dice(group_id, nickname, text)
        await self.ctx.send.text(text, stream_id)
        return True, text, 1
    
    async def skill_growth_cmd(self, **kwargs):
        """技能成长"""
        import random
        
        matched = kwargs.get("matched_groups", {})
        skill_name = (matched.get("skill") or "").strip()
        skill_value = int(matched.get("value") or "0")
        stream_id = kwargs.get("stream_id", "")
        user_id = kwargs.get("message", {}).get("user_info", {}).get("user_id", "")
        group_id = kwargs.get("message", {}).get("group_id", "")
        
        char = await self.storage.get_character(user_id, group_id)
        if not char:
            await self.ctx.send.text(get_default_output("character.no_current"), stream_id)
            return False, "没有人物卡", 0
        
        if skill_value == 0:
            skill_value = char["skills"].get(skill_name, 0)
        
        try:
            roll_value = random.randint(1, 100)
            
            if roll_value > skill_value:
                growth_roll = random.randint(1, 10)
                new_value = min(99, skill_value + growth_roll)
                
                skills = char["skills"]
                skills[skill_name] = new_value
                await self.storage.save_character(
                    name=char["name"], user_id=user_id, group_id=group_id,
                    attributes=char["attributes"], skills=skills, extras=char["extras"], is_current=True,
                )
                
                text = get_default_output(
                    "skill_growth.success",
                    skill_name=skill_name, roll=roll_value, skill_value=skill_value,
                    growth=growth_roll, new_value=new_value,
                )
            else:
                text = get_default_output(
                    "skill_growth.fail",
                    skill_name=skill_name, roll=roll_value, skill_value=skill_value,
                )
            
            text = await self._beautify(text, stream_id)
            await self.ctx.send.text(text, stream_id)
            return True, text, 1
            
        except Exception as e:
            await self.ctx.send.text(f"技能成长检定失败: {e}", stream_id)
            return False, str(e), 0
