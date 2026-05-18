"""
存储管理模块

使用文件系统进行数据持久化（JSON 文件）
"""

import json
import os
import time
from typing import Any, Optional


class StorageManager:
    """存储管理器 - 使用 JSON 文件存储"""
    
    def __init__(self, ctx, data_dir: str = ""):
        self.ctx = ctx
        self.logger = ctx.logger
        self.data_dir = data_dir
        self._characters: dict[str, dict] = {}  # key: "user_id:group_id:name"
        self._logs: dict[str, dict] = {}  # key: "group_id:name"
        self._group_configs: dict[str, dict] = {}  # key: group_id
    
    async def initialize(self) -> None:
        """初始化存储目录并加载数据"""
        try:
            os.makedirs(self.data_dir, exist_ok=True)
            self._load_all_data()
            self.logger.info("存储管理器初始化完成")
        except Exception as e:
            self.logger.error(f"存储初始化失败: {e}")
    
    def _load_all_data(self) -> None:
        """加载所有数据"""
        # 加载人物卡
        char_file = os.path.join(self.data_dir, "characters.json")
        if os.path.exists(char_file):
            with open(char_file, "r", encoding="utf-8") as f:
                self._characters = json.load(f)
        
        # 加载日志
        log_file = os.path.join(self.data_dir, "logs.json")
        if os.path.exists(log_file):
            with open(log_file, "r", encoding="utf-8") as f:
                self._logs = json.load(f)
        
        # 加载群组配置
        config_file = os.path.join(self.data_dir, "group_configs.json")
        if os.path.exists(config_file):
            with open(config_file, "r", encoding="utf-8") as f:
                self._group_configs = json.load(f)
    
    def _save_characters(self) -> None:
        """保存人物卡数据"""
        char_file = os.path.join(self.data_dir, "characters.json")
        with open(char_file, "w", encoding="utf-8") as f:
            json.dump(self._characters, f, ensure_ascii=False, indent=2)
    
    def _save_logs(self) -> None:
        """保存日志数据"""
        log_file = os.path.join(self.data_dir, "logs.json")
        with open(log_file, "w", encoding="utf-8") as f:
            json.dump(self._logs, f, ensure_ascii=False, indent=2)
    
    def _save_group_configs(self) -> None:
        """保存群组配置"""
        config_file = os.path.join(self.data_dir, "group_configs.json")
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(self._group_configs, f, ensure_ascii=False, indent=2)
    
    # ==================== 人物卡操作 ====================
    
    def _char_key(self, user_id: str, group_id: str, name: str) -> str:
        """生成人物卡键"""
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
            
            # 如果设为当前人物卡，先清除同用户同群组的其他当前标记
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
                # 获取指定名称的人物卡
                key = self._char_key(user_id, group_id, name)
                return self._characters.get(key)
            else:
                # 获取当前人物卡
                for k, v in self._characters.items():
                    if k.startswith(f"{user_id}:{group_id}:") and v.get("is_current"):
                        return v
                return None
            
        except Exception as e:
            self.logger.error(f"获取人物卡失败: {e}")
            return None
    
    async def delete_character(
        self,
        user_id: str,
        group_id: str,
        name: str,
    ) -> bool:
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
    
    async def switch_character(
        self,
        user_id: str,
        group_id: str,
        name: str,
    ) -> bool:
        """切换当前人物卡"""
        try:
            key = self._char_key(user_id, group_id, name)
            if key not in self._characters:
                return False
            
            # 清除当前标记
            for k, v in self._characters.items():
                if k.startswith(f"{user_id}:{group_id}:"):
                    v["is_current"] = False
            
            # 设置新的当前人物卡
            self._characters[key]["is_current"] = True
            self._save_characters()
            return True
            
        except Exception as e:
            self.logger.error(f"切换人物卡失败: {e}")
            return False
    
    async def list_characters(
        self,
        user_id: str,
        group_id: str,
    ) -> list[dict[str, Any]]:
        """列出用户的所有人物卡"""
        try:
            prefix = f"{user_id}:{group_id}:"
            return [
                v for k, v in self._characters.items()
                if k.startswith(prefix)
            ]
            
        except Exception as e:
            self.logger.error(f"列出人物卡失败: {e}")
            return []
    
    # ==================== 日志操作 ====================
    
    def _log_key(self, group_id: str, name: str) -> str:
        """生成日志键"""
        return f"{group_id}:{name}"
    
    async def create_log(self, group_id: str, name: str) -> Optional[str]:
        """创建日志"""
        try:
            # 先结束当前活动的日志
            for k, v in self._logs.items():
                if k.startswith(f"{group_id}:") and v.get("is_active"):
                    v["is_active"] = False
            
            key = self._log_key(group_id, name)
            now = int(time.time())
            
            self._logs[key] = {
                "name": name,
                "group_id": group_id,
                "is_active": True,
                "messages": [],
                "created_at": now,
                "updated_at": now,
            }
            
            self._save_logs()
            return key
            
        except Exception as e:
            self.logger.error(f"创建日志失败: {e}")
            return None
    
    async def get_active_log(self, group_id: str) -> Optional[dict[str, Any]]:
        """获取当前活动的日志"""
        try:
            for k, v in self._logs.items():
                if k.startswith(f"{group_id}:") and v.get("is_active"):
                    return v
            return None
            
        except Exception as e:
            self.logger.error(f"获取活动日志失败: {e}")
            return None
    
    async def pause_log(self, group_id: str) -> bool:
        """暂停日志"""
        try:
            log = await self.get_active_log(group_id)
            if log:
                log["is_active"] = False
                log["updated_at"] = int(time.time())
                self._save_logs()
                return True
            return False
            
        except Exception as e:
            self.logger.error(f"暂停日志失败: {e}")
            return False
    
    async def resume_log(self, group_id: str) -> bool:
        """恢复日志"""
        try:
            # 找最近的日志
            recent_log = None
            recent_time = 0
            for k, v in self._logs.items():
                if k.startswith(f"{group_id}:") and v.get("updated_at", 0) > recent_time:
                    recent_log = v
                    recent_time = v.get("updated_at", 0)
            
            if recent_log:
                recent_log["is_active"] = True
                recent_log["updated_at"] = int(time.time())
                self._save_logs()
                return True
            return False
            
        except Exception as e:
            self.logger.error(f"恢复日志失败: {e}")
            return False
    
    async def end_log(self, group_id: str) -> Optional[dict[str, Any]]:
        """结束日志"""
        try:
            log = await self.get_active_log(group_id)
            if log:
                log["is_active"] = False
                log["updated_at"] = int(time.time())
                self._save_logs()
                return log
            return None
            
        except Exception as e:
            self.logger.error(f"结束日志失败: {e}")
            return None
    
    async def delete_log(self, group_id: str, name: str) -> bool:
        """删除日志"""
        try:
            key = self._log_key(group_id, name)
            if key in self._logs:
                del self._logs[key]
                self._save_logs()
                return True
            return False
            
        except Exception as e:
            self.logger.error(f"删除日志失败: {e}")
            return False
    
    async def add_log_message(
        self,
        group_id: str,
        user_id: str,
        nickname: str,
        content: str,
        is_dice: bool = False,
    ) -> bool:
        """添加日志消息"""
        try:
            # 过滤第一个非空格字符是 ( 或 （ 的消息
            stripped = content.lstrip() if content else ""
            if stripped and (stripped.startswith("(") or stripped.startswith("（")):
                return False
            
            log = await self.get_active_log(group_id)
            if log and log.get("is_active"):
                message = {
                    "timestamp": int(time.time()),
                    "user_id": user_id,
                    "nickname": nickname,
                    "content": content,
                    "is_dice": is_dice,
                }
                log["messages"].append(message)
                log["updated_at"] = int(time.time())
                self._save_logs()
                return True
            return False
            
        except Exception as e:
            self.logger.error(f"添加日志消息失败: {e}")
            return False
    
    async def get_log_messages(
        self,
        group_id: str,
        name: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """获取日志消息"""
        try:
            if name:
                key = self._log_key(group_id, name)
                log = self._logs.get(key)
            else:
                log = await self.get_active_log(group_id)
            
            if log:
                return log.get("messages", [])
            return []
            
        except Exception as e:
            self.logger.error(f"获取日志消息失败: {e}")
            return []
    
    async def list_logs(self, group_id: str) -> list[dict[str, Any]]:
        """列出日志"""
        try:
            prefix = f"{group_id}:"
            result = []
            for k, v in self._logs.items():
                if k.startswith(prefix):
                    result.append({
                        "name": v["name"],
                        "is_active": v.get("is_active", False),
                        "created_at": v.get("created_at", 0),
                        "message_count": len(v.get("messages", [])),
                    })
            return result
            
        except Exception as e:
            self.logger.error(f"列出日志失败: {e}")
            return []
    
    # ==================== 群组配置操作 ====================
    
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
