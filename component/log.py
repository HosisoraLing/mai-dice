"""
日志模块

支持:
- 创建/暂停/恢复/结束日志
- 记录消息
- 导出日志
"""

import json
import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class LogMessage:
    """日志消息"""
    timestamp: int
    user_id: str
    nickname: str
    content: str
    is_dice: bool = False
    
    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "user_id": self.user_id,
            "nickname": self.nickname,
            "content": self.content,
            "is_dice": self.is_dice,
        }


@dataclass
class LogSession:
    """日志会话"""
    name: str
    group_id: str
    created_at: int
    is_active: bool = True
    messages: list[LogMessage] = field(default_factory=list)
    paused_at: Optional[int] = None
    
    def add_message(self, message: LogMessage) -> None:
        """添加消息"""
        if self.is_active:
            self.messages.append(message)
    
    def pause(self) -> None:
        """暂停日志"""
        self.is_active = False
        self.paused_at = int(time.time())
    
    def resume(self) -> None:
        """恢复日志"""
        self.is_active = True
        self.paused_at = None
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "name": self.name,
            "group_id": self.group_id,
            "created_at": self.created_at,
            "is_active": self.is_active,
            "message_count": len(self.messages),
            "messages": [msg.to_dict() for msg in self.messages],
        }
    
    def to_json(self, indent: int = 2) -> str:
        """导出为 JSON"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)


class JSONLoggerCore:
    """日志管理核心"""
    
    def __init__(self):
        # group_id -> LogSession
        self._sessions: dict[str, LogSession] = {}
        # group_id -> str (session name)
        self._saved_sessions: dict[str, dict[str, LogSession]] = {}
    
    async def initialize(self) -> None:
        """初始化"""
        pass
    
    def create_session(self, group_id: str, name: str) -> LogSession:
        """创建新的日志会话"""
        # 如果有活动的会话，先结束
        if group_id in self._sessions:
            old_session = self._sessions[group_id]
            self._save_session(group_id, old_session)
        
        session = LogSession(
            name=name,
            group_id=group_id,
            created_at=int(time.time()),
        )
        
        self._sessions[group_id] = session
        return session
    
    def get_session(self, group_id: str) -> Optional[LogSession]:
        """获取当前活动的日志会话"""
        return self._sessions.get(group_id)
    
    def pause_session(self, group_id: str) -> bool:
        """暂停日志"""
        session = self._sessions.get(group_id)
        if session:
            session.pause()
            return True
        return False
    
    def resume_session(self, group_id: str) -> bool:
        """恢复日志"""
        session = self._sessions.get(group_id)
        if session:
            session.resume()
            return True
        return False
    
    def end_session(self, group_id: str) -> Optional[LogSession]:
        """结束日志会话"""
        session = self._sessions.get(group_id)
        if session:
            session.pause()
            self._save_session(group_id, session)
            del self._sessions[group_id]
            return session
        return None
    
    def _save_session(self, group_id: str, session: LogSession) -> None:
        """保存会话到已保存列表"""
        if group_id not in self._saved_sessions:
            self._saved_sessions[group_id] = {}
        self._saved_sessions[group_id][session.name] = session
    
    def get_saved_session(self, group_id: str, name: str) -> Optional[LogSession]:
        """获取已保存的日志会话"""
        sessions = self._saved_sessions.get(group_id, {})
        return sessions.get(name)
    
    def list_sessions(self, group_id: str) -> list[str]:
        """列出群组的所有日志会话"""
        sessions = self._saved_sessions.get(group_id, {})
        names = list(sessions.keys())
        
        # 添加当前活动的会话
        current = self._sessions.get(group_id)
        if current and current.name not in names:
            names.append(current.name)
        
        return names
    
    def delete_session(self, group_id: str, name: str) -> bool:
        """删除日志会话"""
        sessions = self._saved_sessions.get(group_id, {})
        if name in sessions:
            del sessions[name]
            return True
        return False
    
    async def add_message(
        self,
        group_id: str,
        user_id: str,
        nickname: str,
        text: str,
        is_dice: bool = False,
    ) -> None:
        """添加消息到当前会话"""
        session = self._sessions.get(group_id)
        if session and session.is_active:
            message = LogMessage(
                timestamp=int(time.time()),
                user_id=user_id,
                nickname=nickname,
                content=text,
                is_dice=is_dice,
            )
            session.add_message(message)
    
    def get_session_stats(self, group_id: str, name: Optional[str] = None) -> Optional[dict]:
        """获取会话统计信息"""
        if name:
            session = self.get_saved_session(group_id, name)
        else:
            session = self.get_session(group_id)
        
        if not session:
            return None
        
        user_counts: dict[str, int] = {}
        dice_count = 0
        
        for msg in session.messages:
            user_counts[msg.user_id] = user_counts.get(msg.user_id, 0) + 1
            if msg.is_dice:
                dice_count += 1
        
        return {
            "name": session.name,
            "message_count": len(session.messages),
            "dice_count": dice_count,
            "user_count": len(user_counts),
            "created_at": session.created_at,
            "is_active": session.is_active,
        }


# 疯狂症状数据
TEMPORARY_CRAZY_SYMPTOMS = [
    "失忆症：调查员忘记自己是谁，正在做什么",
    "假性残疾：调查员出现心因性的失明或失聪",
    "暴力倾向：调查员变得极具攻击性，可能会攻击附近的人",
    "偏执妄想：调查员陷入严重的偏执，认为有人在监视或迫害自己",
    "人际依赖：调查员过度依赖他人，无法独立行动",
    "昏厥：调查员失去意识，持续数分钟到数小时",
    "逃避行为：调查员试图逃离现场，可能会使用任何方式",
    "歇斯底里：调查员陷入狂笑或痛哭，无法控制情绪",
    "恐惧症：调查员产生强烈的恐惧，可能是对特定物体或情境",
    "躁狂症：调查员陷入异常兴奋，可能会做出危险行为",
]

LONG_TERM_CRAZY_SYMPTOMS = [
    "健忘症：调查员忘记部分重要记忆，可能是最近的事件",
    "反社会行为：调查员表现出反社会倾向，不再关心道德或法律",
    "恐惧症：调查员产生新的持久恐惧，如恐高、幽闭恐惧等",
    "躁狂/抑郁：调查员情绪波动剧烈，时而亢奋时而低落",
    "偏执狂：调查员持续多疑，认为周围的人都在针对自己",
    "敏感化：调查员对某些刺激过度敏感，如噪音、光线等",
    "性功能障碍：调查员出现性功能问题，可能是心理因素导致",
    "躯体转换障碍：调查员出现身体症状，但没有生理原因",
    "强迫行为：调查员出现无法控制的重复行为",
    "分离性障碍：调查员出现人格分裂或身份认同问题",
]


def get_temporary_crazy_symptom() -> str:
    """获取随机临时疯狂症状"""
    import random
    return random.choice(TEMPORARY_CRAZY_SYMPTOMS)


def get_long_term_crazy_symptom() -> str:
    """获取随机长期疯狂症状"""
    import random
    return random.choice(LONG_TERM_CRAZY_SYMPTOMS)
