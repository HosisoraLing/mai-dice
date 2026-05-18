# MaiBot 插件开发指南

## 目录

1. [架构概览](#架构概览)
2. [快速开始](#快速开始)
3. [核心概念](#核心概念)
4. [组件装饰器](#组件装饰器)
5. [能力代理 API](#能力代理-api)
6. [配置管理](#配置管理)
7. [最佳实践](#最佳实践)

## 架构概览

MaiBot 插件系统采用 Host/Runner IPC 架构，插件代码运行在独立的子进程中，通过 msgpack 编码的 RPC 协议与主进程通信。

### Host（主进程侧）

- **PluginRuntimeManager**: 单例管理器，管理 Builtin 和 Third-party 两个 Supervisor
- **PluginSupervisor**: 负责 Runner 子进程的启动、停止、健康检查和插件热重载
- **ComponentRegistry**: 组件注册表，管理所有插件声明的 Tool、Command 等组件
- **HookDispatcher**: Hook 分发器，将命名 Hook 调用分发到对应 Supervisor

### Runner（子进程侧）

- 每种 Supervisor 各自管理一个独立的 Runner 子进程
- 通过 `PluginLoader` 发现和加载插件
- 通过 `RPCClient` 与 Host 通信
- 在插件加载后注入 `PluginContext`，再调用 `on_load()` 生命周期方法

### 通信协议

- **编解码**: 使用 msgpack 格式进行二进制序列化（`MsgPackCodec`）
- **传输层**: 支持 Unix Domain Socket、TCP、Named Pipe 三种传输方式
- **RPC 模型**:
  - Host → Runner: 通过 `invoke_plugin()` 调用插件组件（Tool、Command 等）
  - Runner → Host: 插件通过 `self.ctx` 的能力代理发起 RPC 回调

## 快速开始

### 1. 安装 SDK

```bash
pip install maibot-plugin-sdk
```

### 2. 创建插件目录

```
plugins/
└── my-plugin/
    ├── _manifest.json
    ├── plugin.py
    └── config.toml          # 可选
```

### 3. 编写 Manifest

在 `_manifest.json` 中声明插件元信息：

```json
{
  "manifest_version": 2,
  "id": "com.example.my-plugin",
  "version": "1.0.0",
  "name": "我的插件",
  "description": "一个示例插件",
  "author": {
    "name": "开发者",
    "url": "https://github.com/developer"
  },
  "license": "MIT",
  "urls": {
    "repository": "https://github.com/developer/my-plugin"
  },
  "host_application": {
    "min_version": "1.0.0",
    "max_version": "1.99.99"
  },
  "sdk": {
    "min_version": "1.0.0",
    "max_version": "2.99.99"
  },
  "capabilities": ["send_message"]
}
```

### 4. 编写插件代码

在 `plugin.py` 中继承 `MaiBotPlugin`：

```python
from maibot_sdk import MaiBotPlugin, Command, Tool
from maibot_sdk.types import ToolParameterInfo, ToolParamType


class MyPlugin(MaiBotPlugin):
    async def on_load(self) -> None:
        self.ctx.logger.info("插件已加载")

    async def on_unload(self) -> None:
        self.ctx.logger.info("插件已卸载")

    async def on_config_update(self, scope: str, config_data: dict, version: str) -> None:
        if scope == "self":
            self.ctx.logger.info("插件配置已更新: version=%s", version)

    @Tool(
        "greet",
        description="向用户打招呼",
        parameters=[
            ToolParameterInfo(
                name="stream_id",
                param_type=ToolParamType.STRING,
                description="当前聊天流 ID",
                required=True,
            ),
        ],
    )
    async def handle_greet(self, stream_id: str, **kwargs):
        await self.ctx.send.text("你好！", stream_id)
        return {"success": True, "message": "已回复"}

    @Command("hello", pattern=r"^/hello")
    async def handle_hello(self, **kwargs):
        await self.ctx.send.text("Hello!", kwargs["stream_id"])
        return True, "Hello!", 2


def create_plugin():
    return MyPlugin()
```

## 核心概念

### 插件基类

所有插件必须继承 `MaiBotPlugin`，通过类属性和装饰器声明插件能力：

```python
from maibot_sdk import MaiBotPlugin, Tool, Command
from typing import ClassVar


class MyPlugin(MaiBotPlugin):
    # 订阅全局配置热重载
    config_reload_subscriptions: ClassVar[tuple[str, ...]] = ("bot", "model")

    @Tool("my_tool", description="示例工具")
    async def handle_tool(self, **kwargs):
        ...

    @Command("my_cmd", pattern=r"^/my_cmd")
    async def handle_cmd(self, **kwargs):
        ...
```

### 生命周期方法

SDK 要求所有插件实现三个生命周期方法：

1. **on_load()**: 插件加载完成后的回调
2. **on_unload()**: 插件卸载前的回调
3. **on_config_update()**: 配置热重载回调

### 能力代理

通过 `self.ctx` 访问 15 种能力代理：

- `self.ctx.logger`: 日志记录器
- `self.ctx.send`: 消息发送
- `self.ctx.db`: 数据库操作
- `self.ctx.llm`: LLM 调用
- `self.ctx.config`: 配置读取
- `self.ctx.api`: 插件 API 调用
- `self.ctx.gateway`: 消息网关
- `self.ctx.emoji`: 表情包管理
- `self.ctx.message`: 历史消息查询
- `self.ctx.frequency`: 发言频率控制
- `self.ctx.component`: 插件与组件管理
- `self.ctx.chat`: 聊天流查询
- `self.ctx.person`: 用户信息查询
- `self.ctx.render`: HTML 渲染
- `self.ctx.knowledge`: 知识库搜索
- `self.ctx.tool`: LLM 工具定义查询

## 组件装饰器

### @Tool - LLM 工具组件

最常用的组件类型，允许插件向 LLM 暴露可调用的工具函数。

```python
from maibot_sdk import Tool
from maibot_sdk.types import ToolParameterInfo, ToolParamType

@Tool(
    name="search",
    description="搜索互联网获取信息",
    parameters=[
        ToolParameterInfo(
            name="query",
            param_type=ToolParamType.STRING,
            description="搜索关键词",
            required=True,
        ),
    ],
)
async def handle_search(self, query: str, **kwargs):
    results = await self._do_search(query)
    return {"results": results}
```

### @Command - 斜杠命令组件

基于正则匹配的命令组件。

```python
from maibot_sdk import Command

@Command("hello", pattern=r"^/hello", aliases=["/hi"])
async def handle_hello(self, **kwargs):
    await self.ctx.send.text("Hello!", kwargs["stream_id"])
    return True, "Hello!", 2
```

### @HookHandler - Hook 处理器

订阅命名 Hook 点，支持 blocking/observe 模式。

```python
from maibot_sdk import HookHandler
from maibot_sdk.types import HookMode, HookOrder, ErrorPolicy

@HookHandler(
    "chat.receive.before_process",
    name="message_filter",
    mode=HookMode.BLOCKING,
    order=HookOrder.EARLY,
    error_policy=ErrorPolicy.ABORT,
)
async def handle_message_filter(self, **kwargs):
    # 消息过滤逻辑
    return {"action": "continue", "modified_kwargs": kwargs}
```

### @EventHandler - 事件处理器

监听消息、LLM 生成等生命周期事件。

```python
from maibot_sdk import EventHandler
from maibot_sdk.types import EventType

@EventHandler(
    "message_counter",
    event_type=EventType.ON_MESSAGE,
    intercept_message=True,
    weight=100,
)
async def count_message(self, message, **kwargs):
    # 消息计数逻辑
    return {"intercepted": False}
```

### @API - 插件 API

暴露可被其他插件调用的 API。

```python
from maibot_sdk import API

@API(
    "render_html",
    description="将 HTML 渲染为图片",
    version="1",
    public=True,
)
async def handle_render_html(self, html: str, **kwargs):
    result = await self.ctx.render.html2png(html)
    return {"success": True, "image_path": result}
```

### @MessageGateway - 消息网关

将外部平台接入 MaiBot。

```python
from maibot_sdk import MessageGateway

@MessageGateway(
    route_type="duplex",
    name="qq_gateway",
    platform="qq",
)
async def handle_gateway(self, message, **kwargs):
    # 消息路由逻辑
    return {"success": True}
```

### @LLMProvider - LLM Provider

声明新 LLM 模型接入点。

```python
from maibot_sdk import LLMProvider, LLMProviderBase

class MyProvider(LLMProviderBase):
    async def get_response(self, request):
        return {"content": "来自自定义 Provider 的响应"}

@LLMProvider("my.provider", name="My Provider")
async def handle_llm(self, operation, request):
    return await self.provider.dispatch(operation, request)
```

## 能力代理 API

### ctx.send - 消息发送

```python
# 发送文本消息
await self.ctx.send.text("你好！", stream_id)

# 发送图片
await self.ctx.send.image(image_bytes, stream_id)
```

### ctx.db - 数据库操作

```python
# 查询数据
result = await self.ctx.db.query("SELECT * FROM users")

# 插入数据
await self.ctx.db.insert("users", {"name": "张三", "age": 25})
```

### ctx.llm - LLM 调用

```python
# 文本生成
response = await self.ctx.llm.generate("请解释量子计算")

# 工具调用
result = await self.ctx.llm.call_tool("search", query="AI最新进展")
```

### ctx.config - 配置读取

```python
# 读取插件配置
value = await self.ctx.config.get("plugin.greeting")

# 读取全局配置
all_config = await self.ctx.config.get_all()
```

### ctx.api - 插件 API 调用

```python
# 调用其他插件的 API
result = await self.ctx.api.call(
    "com.example.translate",
    "translate",
    text="Hello",
    target_lang="zh"
)
```

### ctx.gateway - 消息网关

```python
# 更新网关状态
await self.ctx.gateway.update_state(
    gateway_name="my_gateway",
    ready=True,
    platform="qq"
)

# 注入入站消息
await self.ctx.gateway.route_message(
    gateway_name="my_gateway",
    message_dict={...}
)
```

## 配置管理

### 配置模型

```python
from maibot_sdk import MaiBotPlugin, PluginConfigBase, Field


class MyPluginConfig(PluginConfigBase):
    __ui_label__ = "插件配置"
    
    enabled: bool = Field(default=True, description="是否启用插件")
    greeting: str = Field(default="你好！", description="默认问候语")
    max_retries: int = Field(default=3, description="最大重试次数")


class MyPlugin(MaiBotPlugin):
    config_model = MyPluginConfig
    
    async def on_load(self):
        # 访问强类型配置
        self.ctx.logger.info("问候语: %s", self.config.greeting)
```

### 嵌套配置

```python
class PluginSection(PluginConfigBase):
    __ui_label__ = "基础设置"
    enabled: bool = Field(default=True, description="是否启用插件")


class AdvancedSection(PluginConfigBase):
    __ui_label__ = "高级设置"
    timeout: float = Field(default=30.0, description="超时时间")


class MyPluginConfig(PluginConfigBase):
    plugin: PluginSection = Field(default_factory=PluginSection)
    advanced: AdvancedSection = Field(default_factory=AdvancedSection)
```

### 配置热重载

```python
class MyPlugin(MaiBotPlugin):
    config_reload_subscriptions = ("bot", "model")
    
    async def on_config_update(self, scope, config_data, version):
        if scope == "self":
            # 插件自身配置变化
            self.ctx.logger.info("配置已更新")
        elif scope == "bot":
            # 全局 Bot 配置变化
            bot_name = config_data.get("bot_name")
```

## 最佳实践

### 1. 插件命名规范

- 插件 ID 使用反向域名格式：`com.example.my-plugin`
- 版本号使用三段式语义版本：`1.0.0`
- 组件名称使用小写字母和下划线：`my_tool`

### 2. 错误处理

- Tool 组件应返回结构化错误信息
- Command 组件返回三元组表示执行状态
- Hook 处理器根据 error_policy 处理异常

### 3. 性能优化

- 避免在 Tool 处理函数中执行耗时操作
- 使用 observe 模式的 Hook 处理器处理非关键逻辑
- 合理使用 `core_tool=True` 标记高频工具

### 4. 安全性

- 验证所有外部输入参数
- 不要在日志中输出敏感信息
- 使用 capabilities 声明最小权限集

### 5. 配置管理

- 始终使用 `config_model` 声明配置模型
- 为所有配置字段提供合理默认值
- 使用 `__ui_label__` 改善 WebUI 体验

### 6. 测试与调试

- 使用 `self.ctx.logger` 记录调试信息
- 在 `on_load()` 中验证依赖和配置
- 实现 `on_unload()` 清理资源

## 目录结构约定

```
my-plugin/
├── _manifest.json       # 必需：插件清单
├── plugin.py            # 必需：插件入口，包含 create_plugin()
├── config.toml          # 可选：插件配置
├── i18n/                # 可选：国际化资源
│   ├── zh-CN.json
│   └── en-US.json
└── assets/              # 可选：静态资源
```

## 内置插件与第三方插件

MaiBot 维护两个独立的 Runner 子进程：

- **内置插件**: 位于 `src/plugins/built_in/`，运行在 Builtin Supervisor 下
- **第三方插件**: 位于 `plugins/`，运行在 Third-party Supervisor 下

两者使用相同的通信协议和组件注册机制。