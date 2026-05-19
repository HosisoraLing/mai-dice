"""日志管理命令处理器"""

from ..component.output import get_default_output


class LogHandler:
    """日志管理命令混合类"""
    
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
                ".log export <名称> - 导出日志",
                stream_id
            )
            return False, "显示帮助", 0
        
        action = args[0].lower()
        
        try:
            if action == "new":
                if len(args) < 2:
                    await self.ctx.send.text("用法: .log new <日志名>", stream_id)
                    return False, "缺少名称", 0
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
                    return False, "缺少名称", 0
                else:
                    log_name = args[1]
                    success, msg, content = await self.storage.export_log(group_id, log_name)
                    if success and content:
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
                    return True, msg, 1
                    
            else:
                text = "未知操作，可用: new, on, off, end, del, list, export"
            
            await self.ctx.send.text(text, stream_id)
            return True, text, 1
            
        except Exception as e:
            await self.ctx.send.text(f"日志操作失败: {e}", stream_id)
            return False, str(e), 0
