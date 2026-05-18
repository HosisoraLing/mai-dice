"""
NapCat WebSocket 监听模块

监听消息撤回事件，自动从日志中删除对应消息
"""

import asyncio
import json
import time
from typing import Any, Optional, Callable, Awaitable

try:
    import websockets
    HAS_WEBSOCKETS = True
except ImportError:
    HAS_WEBSOCKETS = False


class RecallListener:
    """消息撤回监听器"""
    
    def __init__(
        self,
        ws_url: str = "ws://127.0.0.1:3001",
        token: str = "",
        on_recall: Optional[Callable[[str, str], Awaitable[None]]] = None,
    ):
        self.ws_url = ws_url
        self.token = token
        self.on_recall = on_recall
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._ws = None
    
    async def start(self) -> bool:
        """启动监听"""
        if not HAS_WEBSOCKETS:
            return False
        
        if self._running:
            return True
        
        self._running = True
        self._task = asyncio.create_task(self._listen_loop())
        return True
    
    async def stop(self) -> None:
        """停止监听"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        if self._ws:
            await self._ws.close()
    
    async def _listen_loop(self) -> None:
        """监听循环"""
        while self._running:
            try:
                await self._connect_and_listen()
            except Exception as e:
                await asyncio.sleep(5)  # 重连等待
    
    async def _connect_and_listen(self) -> None:
        """连接并监听"""
        headers = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        
        async with websockets.connect(
            self.ws_url,
            additional_headers=headers,
            ping_interval=30,
        ) as ws:
            self._ws = ws
            async for message in ws:
                if not self._running:
                    break
                await self._handle_message(message)
    
    async def _handle_message(self, raw_message: str) -> None:
        """处理消息"""
        try:
            data = json.loads(raw_message)
            
            # 检查是否是撤回事件
            post_type = data.get("post_type")
            notice_type = data.get("notice_type")
            
            if post_type == "notice" and notice_type == "group_recall":
                group_id = str(data.get("group_id", ""))
                message_id = str(data.get("message_id", ""))
                
                if group_id and message_id and self.on_recall:
                    await self.on_recall(group_id, message_id)
                    
        except json.JSONDecodeError:
            pass
        except Exception:
            pass


def create_recall_listener(
    ws_url: str = "ws://127.0.0.1:3001",
    token: str = "",
    on_recall: Optional[Callable[[str, str], Awaitable[None]]] = None,
) -> Optional[RecallListener]:
    """创建撤回监听器"""
    if not HAS_WEBSOCKETS:
        return None
    
    return RecallListener(ws_url=ws_url, token=token, on_recall=on_recall)
