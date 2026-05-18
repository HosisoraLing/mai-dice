# MaiBot 骰娘插件开发计划

基于 [astrbot_plugin_trpgdice_rerolled](https://github.com/HosisoraLing/astrbot_plugin_trpgdice_rerolled) 移植

## 项目概述

将星星骰娘（重骰版）从 AstrBot 平台迁移到 MaiBot 平台，保留核心 TRPG 骰子功能，适配 MaiBot 插件架构。

---

## 功能模块清单

### 1. 基础掷骰模块

| 功能 | 说明 | 指令示例 |
|------|------|----------|
| 基本掷骰 | 支持 `NdM` 格式 | `.r 1d100` |
| 复杂算式 | 支持加减混合运算 | `.r 3d6+2d4-1d8` |
| 保留最高骰 | `NdMkX` 保留最高X个 | `.r 10d6k5` |
| 重复掷骰 | `N#MdS` 重复N次 | `.r 3#1d20` |

### 2. 技能检定模块

| 功能 | 说明 | 指令示例 |
|------|------|----------|
| 普通检定 | CoC 风格技能判定 | `.ra 侦查 50` |
| 奖励骰检定 | 带奖励骰的检定 | `.rab 2 射击` |
| 惩罚骰检定 | 带惩罚骰的检定 | `.rap 1 闪避` |

### 3. 人物卡管理模块

| 功能 | 说明 | 指令示例 |
|------|------|----------|
| 创建人物卡 | 创建新角色 | `.pc create 名称` |
| 显示人物卡 | 查看当前角色 | `.pc show` |
| 切换人物卡 | 切换当前角色 | `.pc change 名称` |
| 更新属性 | 修改角色属性 | `.pc update 属性 值` |
| 删除人物卡 | 删除指定角色 | `.pc delete 名称` |
| 列出人物卡 | 显示所有角色 | `.pc list` |

### 4. 理智检定模块

| 功能 | 说明 | 指令示例 |
|------|------|----------|
| SAN Check | 理智检定 | `.sc 1d6/1d10` |
| 临时疯狂 | 生成临时疯狂症状 | `.ti` |
| 长期疯狂 | 生成长期疯狂症状 | `.li` |

### 5. 先攻系统模块

| 功能 | 说明 | 指令示例 |
|------|------|----------|
| 掷先攻 | 投掷先攻骰 | `.ri` |
| 调整先攻 | 带调整值的先攻 | `.ri +3` |
| 查看先攻列表 | 显示先攻顺序 | `.init` |
| 结束回合 | 推进到下一回合 | `.ed` |
| 清空先攻 | 清除所有先攻 | `.init clr` |

### 6. 日志系统模块

| 功能 | 说明 | 指令示例 |
|------|------|----------|
| 新建日志 | 开始记录日志 | `.log new 日志名` |
| 暂停日志 | 暂停记录 | `.log off` |
| 恢复日志 | 继续记录 | `.log on` |
| 结束日志 | 结束并导出 | `.log end` |
| 删除日志 | 删除指定日志 | `.log del 日志名` |

### 7. 角色生成模块

| 功能 | 说明 | 指令示例 |
|------|------|----------|
| CoC 角色生成 | 生成 CoC 角色属性 | `.coc` |
| DnD 角色生成 | 生成 DnD 角色属性 | `.dnd` |
| 技能成长 | 技能成长判定 | `.en 技能名` |

### 8. LLM 美化模块

| 功能 | 说明 |
|------|------|
| 美化模式开关 | 可配置开启/关闭 |
| 自定义提示词 | 支持自定义系统提示 |
| 自动降级 | LLM 不可用时使用模板 |

### 9. 杂项功能

| 功能 | 说明 | 指令示例 |
|------|------|----------|
| 火球术 | 计算火球伤害 | `.fireball 5` |
| 今日人品 | 随机人品值 | `.jrrp` |
| CoC 规则设置 | 设置大成功/大失败规则 | `.setcoc 1` |
| 帮助信息 | 显示帮助 | `.dicehelp` |

---

## MaiBot 插件架构设计

### 目录结构

```
maibot_trpg_dice/
├── _manifest.json          # 插件清单
├── plugin.py               # 插件入口
├── config.toml             # 配置文件
├── component/              # 核心组件
│   ├── __init__.py
│   ├── dice.py             # 掷骰引擎
│   ├── character.py        # 人物卡管理
│   ├── sanity.py           # 理智检定
│   ├── rules.py            # 规则引擎
│   ├── log.py              # 日志系统
│   ├── output.py           # 输出格式化
│   └── utils.py            # 工具函数
├── handler/                # 命令处理器
│   ├── __init__.py
│   ├── dice_handler.py     # 掷骰命令
│   ├── character_handler.py # 人物卡命令
│   ├── coc_handler.py      # CoC 命令
│   ├── initiative_handler.py # 先攻命令
│   └── log_handler.py      # 日志命令
└── data/                   # 数据文件
    ├── crazy_symptoms.json # 疯狂症状数据
    └── skill_templates.json # 技能模板
```

### Manifest 设计

```json
{
  "manifest_version": 2,
  "id": "com.hosisora.trpg-dice",
  "version": "1.0.0",
  "name": "TRPG 骰娘",
  "description": "TRPG 跑团骰子插件，支持掷骰、技能检定、人物卡管理",
  "author": {
    "name": "HosisoraLing",
    "url": "https://github.com/HosisoraLing"
  },
  "license": "MIT",
  "urls": {
    "repository": "https://github.com/HosisoraLing/maibot_trpg_dice"
  },
  "host_application": {
    "min_version": "1.0.0",
    "max_version": "2.99.99"
  },
  "sdk": {
    "min_version": "1.0.0",
    "max_version": "2.99.99"
  },
  "capabilities": ["send_message"]
}
```

### 配置模型设计

```python
from maibot_sdk import PluginConfigBase, Field

class DiceConfig(PluginConfigBase):
    __ui_label__ = "骰子设置"
    default_faces: int = Field(default=100, description="默认骰子面数")
    max_dice_count: int = Field(default=100, description="最大骰子数量")
    max_faces: int = Field(default=10000, description="最大骰子面数")

class OutputConfig(PluginConfigBase):
    __ui_label__ = "输出模板"
    roll_result: str = Field(
        default="{nickname}掷骰{expression}={result}",
        description="掷骰结果模板"
    )
    skill_check_success: str = Field(
        default="{nickname}进行{skill_name}检定: {roll}/{skill_value} 成功！",
        description="技能检定成功模板"
    )
    skill_check_fail: str = Field(
        default="{nickname}进行{skill_name}检定: {roll}/{skill_value} 失败！",
        description="技能检定失败模板"
    )

class LLMConfig(PluginConfigBase):
    __ui_label__ = "LLM 美化"
    enabled: bool = Field(default=False, description="是否启用 LLM 美化模式")
    system_prompt: str = Field(
        default="你是一个跑团骰娘，风格活泼可爱。请用简短生动的语言描述掷骰结果。",
        description="LLM 系统提示词"
    )

class TRPGDiceConfig(PluginConfigBase):
    dice: DiceConfig = Field(default_factory=DiceConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
```

---

## 开发阶段规划

### 第一阶段：基础框架（1-2天）

1. **创建插件骨架**
   - 编写 `_manifest.json`
   - 创建 `plugin.py` 入口文件
   - 实现 `on_load`、`on_unload`、`on_config_update` 生命周期

2. **配置系统**
   - 定义 `PluginConfigBase` 配置模型
   - 创建 `config.toml` 默认配置

3. **基础掷骰引擎**
   - 移植 `dice.py` 核心掷骰逻辑
   - 实现 `NdM` 解析器
   - 实现算式求值器

### 第二阶段：核心功能（3-5天）

4. **掷骰命令处理器**
   - `.r` 基本掷骰命令
   - 支持复杂算式、保留骰、重复掷骰

5. **技能检定系统**
   - `.ra` 普通检定
   - `.rab` 奖励骰检定
   - `.rap` 惩罚骰检定

6. **人物卡管理**
   - 移植 `character.py`
   - 实现 `.pc` 系列命令
   - 数据持久化（使用 `ctx.db`）

### 第三阶段：扩展功能（5-7天）

7. **理智检定系统**
   - 移植 `sanity.py`
   - 实现 `.sc` 命令
   - 实现 `.ti`、`.li` 疯狂症状

8. **先攻系统**
   - 实现 `.ri` 先攻掷骰
   - 实现 `.init` 先攻列表管理
   - 实现 `.ed` 回合推进

9. **CoC/DnD 角色生成**
   - 移植角色生成逻辑
   - 实现 `.coc`、`.dnd` 命令

### 第四阶段：高级功能（7-10天）

10. **日志系统**
    - 移植 `log.py`
    - 使用 `ctx.db` 存储日志
    - 实现 `.log` 系列命令
    - JSON 格式导出

11. **LLM 美化模式**
    - 集成 `ctx.llm` 能力代理
    - 实现美化开关
    - 自动降级机制

12. **LLM 工具函数**
    - 注册 `@Tool` 掷骰工具
    - 注册 `@Tool` 技能检定工具
    - 支持 Function Calling

### 第五阶段：优化完善（10-12天）

13. **输出模板系统**
    - 移植 `output.py`
    - 支持变量占位符
    - 配置热重载

14. **错误处理与边界情况**
    - 输入验证
    - 异常处理
    - 友好的错误提示

15. **测试与文档**
    - 编写测试用例
    - 完善帮助文档
    - 更新 README

---

## 核心代码映射

### AstrBot → MaiBot API 映射

| AstrBot | MaiBot | 说明 |
|---------|--------|------|
| `@filter.command("r")` | `@Command("r", pattern=r"^\\.r")` | 命令装饰器 |
| `yield event.plain_result(text)` | `await self.ctx.send.text(text, stream_id)` | 发送文本 |
| `AstrBotConfig` | `PluginConfigBase` | 配置管理 |
| `self.context.get_using_provider()` | `self.ctx.llm` | LLM 调用 |
| 文件存储 | `self.ctx.db` | 数据持久化 |

### 核心模块移植

#### dice.py（掷骰引擎）
- 保留核心解析逻辑
- 替换随机数生成为 Python 标准库
- 适配 MaiBot 的异步调用

#### character.py（人物卡）
- 使用 `ctx.db` 替代文件存储
- 适配新的配置系统

#### log.py（日志系统）
- 使用 `ctx.db` 存储日志数据
- 保留 JSON 导出格式

---

## 测试计划

### 单元测试
- 掷骰引擎测试（各种算式组合）
- 技能检定测试（成功/失败判定）
- 人物卡 CRUD 测试

### 集成测试
- 命令解析测试
- 配置热重载测试
- 日志记录测试

### 用户验收测试
- 群聊场景测试
- 多用户并发测试
- LLM 美化模式测试

---

## 风险与挑战

1. **API 差异**：AstrBot 和 MaiBot 的事件模型不同，需要仔细映射
2. **数据迁移**：原插件使用文件存储，需要迁移到数据库
3. **异步适配**：确保所有 I/O 操作正确使用异步
4. **配置兼容**：保持配置项与原插件一致

---

## 参考资料

- [原插件仓库](https://github.com/HosisoraLing/astrbot_plugin_trpgdice_rerolled)
- [MaiBot 插件开发文档](https://docs.mai-mai.org/develop/plugin-dev/)
- [Dice! 参考实现](https://forum.kokona.tech/)
- [海豹骰娘参考](https://dice.weizaima.com/)