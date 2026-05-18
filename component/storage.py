"""
存储管理模块

参考 astrbot_plugin_trpgdice_rerolled 的日志实现
"""

import os
import json
import time
import re
import uuid
from typing import Any, Optional


class StorageManager:
    """存储管理器"""
    
    def __init__(self, ctx, data_dir: str = ""):
        self.ctx = ctx
        self.logger = ctx.logger
        self.data_dir = data_dir
        # 内存缓存
        self._characters: dict[str, dict] = {}
        self._group_configs: dict[str, dict] = {}
        # 日志会话缓存: group_id -> {name: session_data}
        self._sessions: dict[str, dict[str, dict]] = {}
    
    async def initialize(self) -> None:
        """初始化存储目录并加载数据"""
        try:
            os.makedirs(self.data_dir, exist_ok=True)
            self._load_characters()
            self._load_group_configs()
            self.logger.info("存储管理器初始化完成")
        except Exception as e:
            self.logger.error(f"存储初始化失败: {e}")
    
    # ==================== 路径相关 ====================
    
    def _get_logs_dir(self) -> str:
        """获取日志根目录"""
        return os.path.join(self.data_dir, "group_logs")
    
    def _get_group_dir(self, group_id: str) -> str:
        """获取群组日志目录"""
        return os.path.join(self._get_logs_dir(), str(group_id))
    
    def _get_index_path(self, group_id: str) -> str:
        """获取索引文件路径"""
        return os.path.join(self._get_group_dir(group_id), "index.json")
    
    @staticmethod
    def _sanitize_name(name: str) -> str:
        """清理会话名称，防止路径穿越和非法字符"""
        name = re.sub(r'[/\\:*?"<>|\x00-\x1f]', '', name)
        name = name.replace('..', '')
        name = name[:64].strip()
        return name or uuid.uuid4().hex[:8]
    
    def _get_session_path(self, group_id: str, session_name: str) -> str:
        """获取会话文件路径"""
        return os.path.join(self._get_group_dir(group_id), f"{self._sanitize_name(session_name)}.json")
    
    # ==================== 人物卡操作 ====================
    
    def _load_characters(self) -> None:
        """加载人物卡数据"""
        char_file = os.path.join(self.data_dir, "characters.json")
        if os.path.exists(char_file):
            with open(char_file, "r", encoding="utf-8") as f:
                self._characters = json.load(f)
    
    def _save_characters(self) -> None:
        """保存人物卡数据"""
        char_file = os.path.join(self.data_dir, "characters.json")
        tmp = char_file + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self._characters, f, ensure_ascii=False, indent=2)
        os.replace(tmp, char_file)
    
    def _char_key(self, user_id: str, group_id: str, name: str) -> str:
        return f"{user_id}:{group_id}:{name}"
    
    async def save_character(
        self,
        name: str,
        user_id: str,
        group_id: str,
        attributes: dict[str, int],
        skills: dict[str, int],
        extras: dict[str, Any],
        is_current: bool = False,
    ) -> bool:
        """保存人物卡"""
        try:
            key = self._char_key(user_id, group_id, name)
            
            if is_current:
                for k, v in self._characters.items():
                    if k.startswith(f"{user_id}:{group_id}:"):
                        v["is_current"] = False
            
            now = int(time.time())
            self._characters[key] = {
                "name": name,
                "user_id": user_id,
                "group_id": group_id,
                "attributes": attributes,
                "skills": skills,
                "extras": extras,
                "is_current": is_current,
                "created_at": self._characters.get(key, {}).get("created_at", now),
                "updated_at": now,
            }
            
            self._save_characters()
            return True
        except Exception as e:
            self.logger.error(f"保存人物卡失败: {e}")
            return False
    
    async def get_character(
        self,
        user_id: str,
        group_id: str,
        name: Optional[str] = None,
    ) -> Optional[dict[str, Any]]:
        """获取人物卡"""
        try:
            if name:
                key = self._char_key(user_id, group_id, name)
                return self._characters.get(key)
            else:
                for k, v in self._characters.items():
                    if k.startswith(f"{user_id}:{group_id}:") and v.get("is_current"):
                        return v
                return None
        except Exception as e:
            self.logger.error(f"获取人物卡失败: {e}")
            return None
    
    async def delete_character(self, user_id: str, group_id: str, name: str) -> bool:
        """删除人物卡"""
        try:
            key = self._char_key(user_id, group_id, name)
            if key in self._characters:
                del self._characters[key]
                self._save_characters()
                return True
            return False
        except Exception as e:
            self.logger.error(f"删除人物卡失败: {e}")
            return False
    
    async def switch_character(self, user_id: str, group_id: str, name: str) -> bool:
        """切换当前人物卡"""
        try:
            key = self._char_key(user_id, group_id, name)
            if key not in self._characters:
                return False
            
            for k, v in self._characters.items():
                if k.startswith(f"{user_id}:{group_id}:"):
                    v["is_current"] = False
            
            self._characters[key]["is_current"] = True
            self._save_characters()
            return True
        except Exception as e:
            self.logger.error(f"切换人物卡失败: {e}")
            return False
    
    async def list_characters(self, user_id: str, group_id: str) -> list[dict[str, Any]]:
        """列出用户的所有人物卡"""
        try:
            prefix = f"{user_id}:{group_id}:"
            return [v for k, v in self._characters.items() if k.startswith(prefix)]
        except Exception as e:
            self.logger.error(f"列出人物卡失败: {e}")
            return []
    
    # ==================== 日志操作 ====================
    
    async def _load_group(self, group_id: str) -> dict[str, dict]:
        """加载群组日志"""
        if group_id in self._sessions:
            return self._sessions[group_id]
        
        grp_dir = self._get_group_dir(group_id)
        idx_path = self._get_index_path(group_id)
        grp: dict[str, dict] = {}
        
        if os.path.isfile(idx_path):
            try:
                with open(idx_path, "r", encoding="utf-8") as f:
                    index = json.load(f)
            except Exception:
                index = {}
        else:
            index = {}
        
        for name, meta in index.items():
            sess_path = self._get_session_path(group_id, name)
            if not os.path.isfile(sess_path):
                continue
            try:
                with open(sess_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                data.setdefault("start_time", meta.get("start_time", 0))
                data.setdefault("end_time", meta.get("end_time", None))
                data.setdefault("messages", [])
                data.setdefault("finished", meta.get("finished", False))
                grp[name] = data
            except Exception:
                pass
        
        self._sessions[group_id] = grp
        return grp
    
    async def _persist_group(self, group_id: str) -> None:
        """持久化群组日志"""
        grp = self._sessions.get(group_id, {})
        grp_dir = self._get_group_dir(group_id)
        os.makedirs(grp_dir, exist_ok=True)
        
        # 会话文件
        for name, sec in grp.items():
            path = self._get_session_path(group_id, name)
            tmp = path + ".tmp"
            try:
                with open(tmp, "w", encoding="utf-8") as f:
                    json.dump(sec, f, ensure_ascii=False, indent=2)
                os.replace(tmp, path)
            except Exception:
                if os.path.exists(tmp):
                    os.remove(tmp)
        
        # index.json
        index = {
            name: {
                "start_time": sec.get("start_time", 0),
                "end_time": sec.get("end_time"),
                "finished": bool(sec.get("finished", False))
            }
            for name, sec in grp.items()
        }
        
        idx_path = self._get_index_path(group_id)
        idx_tmp = idx_path + ".tmp"
        try:
            with open(idx_tmp, "w", encoding="utf-8") as f:
                json.dump(index, f, ensure_ascii=False, indent=2)
            os.replace(idx_tmp, idx_path)
        except Exception:
            if os.path.exists(idx_tmp):
                os.remove(idx_tmp)
    
    async def create_log(self, group_id: str, name: str) -> tuple[bool, str]:
        """创建日志会话"""
        grp = await self._load_group(group_id)
        
        # 检查是否有未完成的会话
        unfinished = [n for n, s in grp.items() if not s.get("finished", False)]
        if unfinished:
            return False, f"有未完成的会话「{unfinished[-1]}」，请先结束或删除"
        
        name = self._sanitize_name(name)
        grp[name] = {
            "start_time": int(time.time()),
            "end_time": None,
            "messages": [],
            "finished": False
        }
        
        await self._persist_group(group_id)
        return True, f"日志「{name}」已创建"
    
    async def get_active_log(self, group_id: str) -> Optional[dict[str, Any]]:
        """获取当前活动的日志"""
        grp = await self._load_group(group_id)
        active = [
            (n, s) for n, s in grp.items()
            if s.get("end_time") is None and not s.get("finished", False)
        ]
        if active:
            return active[-1][1]
        return None
    
    async def pause_log(self, group_id: str) -> tuple[bool, str]:
        """暂停日志"""
        grp = await self._load_group(group_id)
        
        active = [
            n for n, s in grp.items()
            if s.get("end_time") is None and not s.get("finished", False)
        ]
        if not active:
            return False, "没有活动的日志会话"
        
        name = active[-1]
        grp[name]["end_time"] = int(time.time())
        
        await self._persist_group(group_id)
        return True, f"日志「{name}」已暂停"
    
    async def resume_log(self, group_id: str, name: Optional[str] = None) -> tuple[bool, str]:
        """恢复日志"""
        grp = await self._load_group(group_id)
        
        if name:
            sec = grp.get(name)
            if not sec:
                return False, f"未找到日志「{name}」"
            if sec.get("finished"):
                return False, f"日志「{name}」已结束"
            if sec.get("end_time") is None:
                return False, f"日志「{name}」正在进行中"
            sec["end_time"] = None
            await self._persist_group(group_id)
            return True, f"日志「{name}」已恢复"
        
        paused = [
            n for n, s in grp.items()
            if s.get("end_time") is not None and not s.get("finished", False)
        ]
        if not paused:
            return False, "没有已暂停的日志会话"
        
        grp[paused[-1]]["end_time"] = None
        await self._persist_group(group_id)
        return True, f"日志「{paused[-1]}」已恢复"
    
    async def end_log(self, group_id: str) -> tuple[bool, str, Optional[dict]]:
        """结束日志"""
        grp = await self._load_group(group_id)
        
        active = [
            n for n, s in grp.items()
            if s.get("end_time") is None and not s.get("finished", False)
        ]
        if not active:
            return False, "没有活动的日志会话", None
        
        name = active[-1]
        sec = grp[name]
        sec["end_time"] = int(time.time())
        sec["finished"] = True
        
        await self._persist_group(group_id)
        return True, f"日志「{name}」已结束，共 {len(sec.get('messages', []))} 条消息", sec
    
    async def halt_log(self, group_id: str) -> tuple[bool, str]:
        """强制删除未完成的日志"""
        grp = await self._load_group(group_id)
        
        unfinished = [n for n, s in grp.items() if not s.get("finished", False)]
        if not unfinished:
            return False, "没有未完成的日志会话"
        
        name = unfinished[-1]
        
        try:
            os.remove(self._get_session_path(group_id, name))
        except Exception:
            pass
        
        del grp[name]
        await self._persist_group(group_id)
        return True, f"日志「{name}」已删除"
    
    async def delete_log(self, group_id: str, name: str) -> tuple[bool, str]:
        """删除日志"""
        grp = await self._load_group(group_id)
        
        if name not in grp:
            return False, f"未找到日志「{name}」"
        
        try:
            os.remove(self._get_session_path(group_id, name))
        except Exception:
            pass
        
        del grp[name]
        await self._persist_group(group_id)
        return True, f"日志「{name}」已删除"
    
    async def add_log_message(
        self,
        group_id: str,
        user_id: str,
        nickname: str,
        content: str,
        is_dice: bool = False,
        message_id: str = "",
    ) -> bool:
        """添加日志消息"""
        try:
            # 过滤第一个非空格字符是 ( 或 （ 的消息
            stripped = content.lstrip() if content else ""
            if stripped and (stripped.startswith("(") or stripped.startswith("（")):
                return False
            
            # 清理 CQ 码
            text_clean = re.sub(r'\[CQ:image,.*?\]', '', content).strip()
            if not text_clean:
                return False
            
            grp = await self._load_group(group_id)
            active = [
                n for n, s in grp.items()
                if s.get("end_time") is None and not s.get("finished", False)
            ]
            
            if not active:
                return False
            
            sec = grp[active[-1]]
            
            sec.setdefault("messages", []).append({
                "timestamp": int(time.time()),
                "user_id": user_id,
                "nickname": nickname,
                "text": text_clean,
                "isDice": is_dice,
                "message_id": message_id,
            })
            
            await self._persist_group(group_id)
            return True
            
        except Exception as e:
            self.logger.error(f"添加日志消息失败: {e}")
            return False
    
    async def delete_message_by_id(self, group_id: str, message_id: str) -> bool:
        """根据消息 ID 删除日志中的消息"""
        try:
            grp = await self._load_group(group_id)
            active = [
                n for n, s in grp.items()
                if s.get("end_time") is None and not s.get("finished", False)
            ]
            
            if not active:
                return False
            
            sec = grp[active[-1]]
            messages = sec.get("messages", [])
            original_count = len(messages)
            
            # 过滤掉匹配的消息
            sec["messages"] = [
                msg for msg in messages
                if str(msg.get("message_id", "")) != str(message_id)
            ]
            
            if len(sec["messages"]) < original_count:
                await self._persist_group(group_id)
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"删除消息失败: {e}")
            return False
    
    async def list_logs(self, group_id: str) -> list[str]:
        """列出日志"""
        grp = await self._load_group(group_id)
        if not grp:
            return ["还没有日志记录"]
        
        lines = []
        for name, sec in grp.items():
            st = time.strftime(
                "%Y-%m-%d %H:%M:%S",
                time.localtime(sec.get("start_time", 0))
            )
            status = (
                "已结束" if sec.get("finished")
                else "进行中" if sec.get("end_time") is None
                else "已暂停"
            )
            lines.append(f"- {name} ({st}, {status}, {len(sec.get('messages', []))}条)")
        
        return lines
    
    async def export_log(self, group_id: str, name: str) -> tuple[bool, str, Optional[bytes]]:
        """导出日志为染色器格式，返回 (成功, 消息, 文件内容)"""
        grp = await self._load_group(group_id)
        
        if name not in grp:
            return False, f"未找到日志「{name}」", None
        
        sec = grp[name]
        export_data = {"version": 1, "items": []}
        
        for m in sec.get("messages", []):
            ts = int(m.get("timestamp", time.time()))
            time_str = time.strftime("%Y/%m/%d %H:%M:%S", time.localtime(ts))
            export_data["items"].append({
                "nickname": m.get("nickname", ""),
                "IMUserId": str(m.get("user_id", "")),
                "time": time_str,
                "message": m.get("text", ""),
                "images": m.get("images", []),
                "isDice": m.get("isDice", False)
            })
        
        exports_dir = os.path.join(self._get_logs_dir(), "exports")
        os.makedirs(exports_dir, exist_ok=True)
        
        file_path = os.path.join(exports_dir, f"{group_id}_{name}.json")
        
        try:
            content = json.dumps(export_data, ensure_ascii=False, indent=2).encode("utf-8")
            with open(file_path, "wb") as f:
                f.write(content)
            return True, f"日志「{name}」已导出，共 {len(export_data['items'])} 条记录", content
        except Exception as e:
            return False, str(e), None
    
    # ==================== 群组配置操作 ====================
    
    def _load_group_configs(self) -> None:
        """加载群组配置"""
        config_file = os.path.join(self.data_dir, "group_configs.json")
        if os.path.exists(config_file):
            with open(config_file, "r", encoding="utf-8") as f:
                self._group_configs = json.load(f)
    
    def _save_group_configs(self) -> None:
        """保存群组配置"""
        config_file = os.path.join(self.data_dir, "group_configs.json")
        tmp = config_file + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self._group_configs, f, ensure_ascii=False, indent=2)
        os.replace(tmp, config_file)
    
    async def get_group_config(self, group_id: str) -> dict[str, Any]:
        """获取群组配置"""
        return self._group_configs.get(group_id, {"group_id": group_id, "coc_rule": 1})
    
    async def set_coc_rule(self, group_id: str, rule: int) -> bool:
        """设置 CoC 规则"""
        try:
            if group_id not in self._group_configs:
                self._group_configs[group_id] = {"group_id": group_id}
            
            self._group_configs[group_id]["coc_rule"] = rule
            self._group_configs[group_id]["updated_at"] = int(time.time())
            self._save_group_configs()
            return True
        except Exception as e:
            self.logger.error(f"设置 CoC 规则失败: {e}")
            return False
