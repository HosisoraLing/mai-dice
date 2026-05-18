"""
存储管理模块

使用 MaiBot 的 ctx.db 进行数据持久化
"""

import json
import time
from typing import Any, Optional


class StorageManager:
    """存储管理器"""
    
    def __init__(self, ctx):
        self.ctx = ctx
        self.logger = ctx.logger
    
    async def initialize(self) -> None:
        """初始化数据库表"""
        try:
            # 创建人物卡表
            await self.ctx.db.execute("""
                CREATE TABLE IF NOT EXISTS trpg_characters (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    group_id TEXT NOT NULL,
                    attributes TEXT DEFAULT '{}',
                    skills TEXT DEFAULT '{}',
                    extras TEXT DEFAULT '{}',
                    is_current INTEGER DEFAULT 0,
                    created_at INTEGER NOT NULL,
                    updated_at INTEGER NOT NULL,
                    UNIQUE(user_id, group_id, name)
                )
            """)
            
            # 创建日志表
            await self.ctx.db.execute("""
                CREATE TABLE IF NOT EXISTS trpg_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    group_id TEXT NOT NULL,
                    is_active INTEGER DEFAULT 0,
                    created_at INTEGER NOT NULL,
                    updated_at INTEGER NOT NULL,
                    UNIQUE(group_id, name)
                )
            """)
            
            # 创建日志消息表
            await self.ctx.db.execute("""
                CREATE TABLE IF NOT EXISTS trpg_log_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    log_id INTEGER NOT NULL,
                    timestamp INTEGER NOT NULL,
                    user_id TEXT NOT NULL,
                    nickname TEXT NOT NULL,
                    content TEXT NOT NULL,
                    is_dice INTEGER DEFAULT 0,
                    FOREIGN KEY (log_id) REFERENCES trpg_logs(id)
                )
            """)
            
            # 创建群组配置表
            await self.ctx.db.execute("""
                CREATE TABLE IF NOT EXISTS trpg_group_config (
                    group_id TEXT PRIMARY KEY,
                    coc_rule INTEGER DEFAULT 1,
                    updated_at INTEGER NOT NULL
                )
            """)
            
            self.logger.info("数据库表初始化完成")
            
        except Exception as e:
            self.logger.error(f"数据库初始化失败: {e}")
    
    # ==================== 人物卡操作 ====================
    
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
            now = int(time.time())
            
            # 如果设为当前人物卡，先清除同用户同群组的其他当前标记
            if is_current:
                await self.ctx.db.execute(
                    "UPDATE trpg_characters SET is_current = 0 WHERE user_id = ? AND group_id = ?",
                    (user_id, group_id),
                )
            
            await self.ctx.db.execute("""
                INSERT OR REPLACE INTO trpg_characters 
                (name, user_id, group_id, attributes, skills, extras, is_current, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                name,
                user_id,
                group_id,
                json.dumps(attributes, ensure_ascii=False),
                json.dumps(skills, ensure_ascii=False),
                json.dumps(extras, ensure_ascii=False),
                1 if is_current else 0,
                now,
                now,
            ))
            
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
                row = await self.ctx.db.fetchone(
                    "SELECT * FROM trpg_characters WHERE user_id = ? AND group_id = ? AND name = ?",
                    (user_id, group_id, name),
                )
            else:
                # 获取当前人物卡
                row = await self.ctx.db.fetchone(
                    "SELECT * FROM trpg_characters WHERE user_id = ? AND group_id = ? AND is_current = 1",
                    (user_id, group_id),
                )
            
            if row:
                return {
                    "name": row[1],
                    "user_id": row[2],
                    "group_id": row[3],
                    "attributes": json.loads(row[4]),
                    "skills": json.loads(row[5]),
                    "extras": json.loads(row[6]),
                    "is_current": bool(row[7]),
                    "created_at": row[8],
                    "updated_at": row[9],
                }
            
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
            await self.ctx.db.execute(
                "DELETE FROM trpg_characters WHERE user_id = ? AND group_id = ? AND name = ?",
                (user_id, group_id, name),
            )
            return True
            
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
            # 先清除当前标记
            await self.ctx.db.execute(
                "UPDATE trpg_characters SET is_current = 0 WHERE user_id = ? AND group_id = ?",
                (user_id, group_id),
            )
            
            # 设置新的当前人物卡
            await self.ctx.db.execute(
                "UPDATE trpg_characters SET is_current = 1 WHERE user_id = ? AND group_id = ? AND name = ?",
                (user_id, group_id, name),
            )
            
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
            rows = await self.ctx.db.fetchall(
                "SELECT * FROM trpg_characters WHERE user_id = ? AND group_id = ?",
                (user_id, group_id),
            )
            
            return [
                {
                    "name": row[1],
                    "user_id": row[2],
                    "group_id": row[3],
                    "attributes": json.loads(row[4]),
                    "skills": json.loads(row[5]),
                    "is_current": bool(row[7]),
                }
                for row in rows
            ]
            
        except Exception as e:
            self.logger.error(f"列出人物卡失败: {e}")
            return []
    
    # ==================== 日志操作 ====================
    
    async def create_log(self, group_id: str, name: str) -> Optional[int]:
        """创建日志"""
        try:
            # 先结束当前活动的日志
            await self.ctx.db.execute(
                "UPDATE trpg_logs SET is_active = 0 WHERE group_id = ? AND is_active = 1",
                (group_id,),
            )
            
            now = int(time.time())
            
            # 创建新日志
            cursor = await self.ctx.db.execute("""
                INSERT OR REPLACE INTO trpg_logs (name, group_id, is_active, created_at, updated_at)
                VALUES (?, ?, 1, ?, ?)
            """, (name, group_id, now, now))
            
            return cursor.lastrowid
            
        except Exception as e:
            self.logger.error(f"创建日志失败: {e}")
            return None
    
    async def get_active_log(self, group_id: str) -> Optional[dict[str, Any]]:
        """获取当前活动的日志"""
        try:
            row = await self.ctx.db.fetchone(
                "SELECT * FROM trpg_logs WHERE group_id = ? AND is_active = 1",
                (group_id,),
            )
            
            if row:
                return {
                    "id": row[0],
                    "name": row[1],
                    "group_id": row[2],
                    "is_active": bool(row[3]),
                    "created_at": row[4],
                    "updated_at": row[5],
                }
            
            return None
            
        except Exception as e:
            self.logger.error(f"获取活动日志失败: {e}")
            return None
    
    async def pause_log(self, group_id: str) -> bool:
        """暂停日志"""
        try:
            await self.ctx.db.execute(
                "UPDATE trpg_logs SET is_active = 0, updated_at = ? WHERE group_id = ? AND is_active = 1",
                (int(time.time()), group_id),
            )
            return True
            
        except Exception as e:
            self.logger.error(f"暂停日志失败: {e}")
            return False
    
    async def resume_log(self, group_id: str) -> bool:
        """恢复日志"""
        try:
            await self.ctx.db.execute(
                "UPDATE trpg_logs SET is_active = 1, updated_at = ? WHERE group_id = ? AND is_active = 0 ORDER BY updated_at DESC LIMIT 1",
                (int(time.time()), group_id),
            )
            return True
            
        except Exception as e:
            self.logger.error(f"恢复日志失败: {e}")
            return False
    
    async def end_log(self, group_id: str) -> Optional[dict[str, Any]]:
        """结束日志"""
        try:
            log = await self.get_active_log(group_id)
            if log:
                await self.ctx.db.execute(
                    "UPDATE trpg_logs SET is_active = 0, updated_at = ? WHERE id = ?",
                    (int(time.time()), log["id"]),
                )
                return log
            return None
            
        except Exception as e:
            self.logger.error(f"结束日志失败: {e}")
            return None
    
    async def delete_log(self, group_id: str, name: str) -> bool:
        """删除日志"""
        try:
            # 获取日志 ID
            log = await self.ctx.db.fetchone(
                "SELECT id FROM trpg_logs WHERE group_id = ? AND name = ?",
                (group_id, name),
            )
            
            if log:
                # 删除日志消息
                await self.ctx.db.execute(
                    "DELETE FROM trpg_log_messages WHERE log_id = ?",
                    (log[0],),
                )
                # 删除日志
                await self.ctx.db.execute(
                    "DELETE FROM trpg_logs WHERE id = ?",
                    (log[0],),
                )
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
            log = await self.get_active_log(group_id)
            if log and log["is_active"]:
                await self.ctx.db.execute("""
                    INSERT INTO trpg_log_messages (log_id, timestamp, user_id, nickname, content, is_dice)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    log["id"],
                    int(time.time()),
                    user_id,
                    nickname,
                    content,
                    1 if is_dice else 0,
                ))
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
                log = await self.ctx.db.fetchone(
                    "SELECT id FROM trpg_logs WHERE group_id = ? AND name = ?",
                    (group_id, name),
                )
            else:
                log = await self.ctx.db.fetchone(
                    "SELECT id FROM trpg_logs WHERE group_id = ? ORDER BY updated_at DESC LIMIT 1",
                    (group_id,),
                )
            
            if log:
                rows = await self.ctx.db.fetchall(
                    "SELECT * FROM trpg_log_messages WHERE log_id = ? ORDER BY timestamp",
                    (log[0],),
                )
                
                return [
                    {
                        "id": row[0],
                        "timestamp": row[2],
                        "user_id": row[3],
                        "nickname": row[4],
                        "content": row[5],
                        "is_dice": bool(row[6]),
                    }
                    for row in rows
                ]
            
            return []
            
        except Exception as e:
            self.logger.error(f"获取日志消息失败: {e}")
            return []
    
    async def list_logs(self, group_id: str) -> list[dict[str, Any]]:
        """列出日志"""
        try:
            rows = await self.ctx.db.fetchall(
                "SELECT * FROM trpg_logs WHERE group_id = ? ORDER BY created_at DESC",
                (group_id,),
            )
            
            result = []
            for row in rows:
                # 获取消息数量
                count = await self.ctx.db.fetchone(
                    "SELECT COUNT(*) FROM trpg_log_messages WHERE log_id = ?",
                    (row[0],),
                )
                
                result.append({
                    "id": row[0],
                    "name": row[1],
                    "is_active": bool(row[3]),
                    "created_at": row[4],
                    "message_count": count[0] if count else 0,
                })
            
            return result
            
        except Exception as e:
            self.logger.error(f"列出日志失败: {e}")
            return []
    
    # ==================== 群组配置操作 ====================
    
    async def get_group_config(self, group_id: str) -> dict[str, Any]:
        """获取群组配置"""
        try:
            row = await self.ctx.db.fetchone(
                "SELECT * FROM trpg_group_config WHERE group_id = ?",
                (group_id,),
            )
            
            if row:
                return {
                    "group_id": row[0],
                    "coc_rule": row[1],
                }
            
            return {"group_id": group_id, "coc_rule": 1}
            
        except Exception as e:
            self.logger.error(f"获取群组配置失败: {e}")
            return {"group_id": group_id, "coc_rule": 1}
    
    async def set_coc_rule(self, group_id: str, rule: int) -> bool:
        """设置 CoC 规则"""
        try:
            await self.ctx.db.execute("""
                INSERT OR REPLACE INTO trpg_group_config (group_id, coc_rule, updated_at)
                VALUES (?, ?, ?)
            """, (group_id, rule, int(time.time())))
            
            return True
            
        except Exception as e:
            self.logger.error(f"设置 CoC 规则失败: {e}")
            return False
