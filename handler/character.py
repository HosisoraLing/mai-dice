"""人物卡命令处理器"""

from ..component.dice import roll
from ..component.character import roll_character, format_character, roll_dnd_character, format_dnd_character
from ..component.output import get_default_output


class CharacterHandler:
    """人物卡命令混合类"""
    
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
            return False, "缺少参数", 0
        
        action = args[0].lower()
        
        try:
            if action == "create":
                if len(args) < 2:
                    await self.ctx.send.text("用法: .pc create <名称>", stream_id)
                    return False, "缺少名称", 0
                name = args[1]
                existing = await self.storage.get_character(user_id, group_id, name)
                if existing:
                    text = get_default_output("character.exists", name=name)
                else:
                    await self.storage.save_character(
                        name=name, user_id=user_id, group_id=group_id,
                        attributes={}, skills={}, extras={}, is_current=True,
                    )
                    text = get_default_output("character.created", name=name)
                
            elif action == "show":
                char = await self.storage.get_character(user_id, group_id)
                if not char:
                    text = get_default_output("character.no_current")
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
                    return False, "缺少名称", 0
                name = args[1]
                char = await self.storage.get_character(user_id, group_id, name)
                if char:
                    await self.storage.switch_character(user_id, group_id, name)
                    text = get_default_output("character.switched", name=name)
                else:
                    text = get_default_output("character.not_found", name=name)
                    
            elif action == "delete":
                if len(args) < 2:
                    await self.ctx.send.text("用法: .pc delete <名称>", stream_id)
                    return False, "缺少名称", 0
                name = args[1]
                char = await self.storage.get_character(user_id, group_id, name)
                if char:
                    await self.storage.delete_character(user_id, group_id, name)
                    text = get_default_output("character.deleted", name=name)
                else:
                    text = get_default_output("character.not_found", name=name)
                    
            elif action == "update":
                if len(args) < 3:
                    await self.ctx.send.text("用法: .pc update <属性> <值/公式>", stream_id)
                    return False, "缺少参数", 0
                
                char = await self.storage.get_character(user_id, group_id)
                if not char:
                    text = get_default_output("character.no_current")
                else:
                    attr_name = args[1]
                    value_str = args[2]
                    
                    if 'd' in value_str.lower():
                        result = roll(value_str)
                        value = result.total if not isinstance(result, list) else result[0].total
                    else:
                        value = int(value_str)
                    
                    attributes = char["attributes"]
                    attributes[attr_name] = value
                    
                    await self.storage.save_character(
                        name=char["name"], user_id=user_id, group_id=group_id,
                        attributes=attributes, skills=char["skills"], extras=char["extras"], is_current=True,
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
            await self.ctx.send.text(get_default_output("character.no_current"), stream_id)
            return False, "没有人物卡", 0
        
        try:
            if 'd' in value_str.lower():
                result = roll(value_str)
                value = result.total if not isinstance(result, list) else result[0].total
            else:
                if value_str.startswith('+') or value_str.startswith('-'):
                    current = char["attributes"].get(attr_name, 0)
                    value = current + int(value_str)
                else:
                    value = int(value_str)
            
            attributes = char["attributes"]
            attributes[attr_name] = value
            
            await self.storage.save_character(
                name=char["name"], user_id=user_id, group_id=group_id,
                attributes=attributes, skills=char["skills"], extras=char["extras"], is_current=True,
            )
            
            await self.ctx.send.text(f"已更新 {char['name']} 的 {attr_name} 为 {value}", stream_id)
            return True, f"已更新 {attr_name}", 1
            
        except Exception as e:
            await self.ctx.send.text(f"设置属性失败: {e}", stream_id)
            return False, str(e), 0
    
    async def coc_character_cmd(self, **kwargs):
        """生成 CoC 角色"""
        matched = kwargs.get("matched_groups", {})
        count = int(matched.get("count") or "1")
        stream_id = kwargs.get("stream_id", "")
        
        count = min(count, 10)
        
        characters = [roll_character() for _ in range(count)]
        results = [format_character(char, index=i+1) for i, char in enumerate(characters)]
        
        text = results[0] if count == 1 else "\n\n".join(results)
        text = await self._beautify(text, stream_id)
        await self.ctx.send.text(text, stream_id)
        return True, text, 1
    
    async def dnd_character_cmd(self, **kwargs):
        """生成 DnD 角色"""
        matched = kwargs.get("matched_groups", {})
        count = int(matched.get("count") or "1")
        stream_id = kwargs.get("stream_id", "")
        
        count = min(count, 10)
        
        characters = [roll_dnd_character() for _ in range(count)]
        results = [format_dnd_character(char, index=i+1) for i, char in enumerate(characters)]
        
        text = results[0] if count == 1 else "\n\n".join(results)
        text = await self._beautify(text, stream_id)
        await self.ctx.send.text(text, stream_id)
        return True, text, 1
