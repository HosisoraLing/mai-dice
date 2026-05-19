# MaiDice

MaiBot TRPG 骰娘插件 - 星星骰娘-重骰版！

基于 [astrbot_plugin_trpgdice_rerolled](https://github.com/HosisoraLing/astrbot_plugin_trpgdice_rerolled) 移植。

## 功能

### 基础掷骰
- `.r 1d100` - 掷 1 个 100 面骰
- `.r 3d6+5` - 掷 3 个 6 面骰 + 5
- `.r 10d6k5` - 掷 10 个 d6，保留最高 5 个
- `.r 3#1d20` - 掷 1d20 三次
- `.dh 1d100` - 暗骰，结果私聊发送

### 技能检定
- `.ra 侦查 50` - 技能检定
- `.rab 2 射击` - 带 2 个奖励骰的检定
- `.rap 1 闪避` - 带 1 个惩罚骰的检定
- `.sc 1d6/1d10` - 理智检定
- `.ti` - 临时疯狂
- `.li` - 长期疯狂
- `.en 技能名 [技能值]` - 技能成长

### 人物卡
- `.pc create <名称>` - 创建人物卡
- `.pc show` - 显示当前人物卡
- `.pc list` - 列出所有人物卡
- `.pc change <名称>` - 切换人物卡
- `.pc update <属性> <值>` - 更新属性
- `.pc delete <名称>` - 删除人物卡
- `.st san-5` - 设置属性（支持 +/-）

### 先攻系统
- `.ri` - 掷先攻
- `.ri +3` - 带调整值掷先攻
- `.init` - 查看先攻列表
- `.init clr` - 清空先攻列表
- `.ed` - 结束当前回合

### 角色生成
- `.coc` - 生成 CoC 角色属性
- `.dnd` - 生成 DnD 角色属性

### 日志管理
- `.log new <名称>` - 创建日志
- `.log on` - 恢复日志
- `.log off` - 暂停日志
- `.log end` - 结束日志
- `.log del <名称>` - 删除日志
- `.log list` - 列出日志
- `.log export <名称>` - 导出日志（JSON 格式，兼容染色器）

### 其他
- `.fireball 5` - 火球术伤害
- `.jrrp` - 今日人品
- `.setcoc 1` - 设置 CoC 规则（1-5）
- `.dicehelp` - 显示帮助

## 安装

1. 将 `mai-dice` 目录放入 MaiBot 的 `plugins/` 目录
2. 重启 MaiBot

## 配置

编辑 `config.toml` 自定义插件行为：

```toml
[plugin]
enabled = true

[dice]
default_faces = 100    # 默认骰子面数
max_dice_count = 100   # 最大骰子数量
max_faces = 10000      # 最大骰子面数

[output.dice]
success = "{name}掷骰 {result} = {total}"
critical_success = "{name}掷骰 {result} = {total} 大成功！"
critical_fail = "{name}掷骰 {result} = {total} 大失败！"

[output.skill]
success = "{nickname}进行{skill_name}检定: {roll}/{skill_value} 成功！"
fail = "{nickname}进行{skill_name}检定: {roll}/{skill_value} 失败！"
critical_success = "{nickname}进行{skill_name}检定: {roll}/{skill_value} 大成功！"
critical_fail = "{nickname}进行{skill_name}检定: {roll}/{skill_value} 大失败！"

[llm_mode]
enabled = false
system_prompt = "你是一个跑团骰娘，风格活泼可爱。请用简短生动的语言描述掷骰结果。"

[napcat]
enable_recall_listener = false
ws_url = "ws://127.0.0.1:3001"
token = ""
```

### 文案变量

| 变量 | 说明 |
|------|------|
| `{name}` / `{nickname}` | 用户昵称 |
| `{result}` | 掷骰详情 |
| `{total}` | 总值 |
| `{skill_name}` | 技能名称 |
| `{roll}` | 掷骰值 |
| `{skill_value}` | 技能值 |

## 大成功/大失败规则

- d100 掷出 1 → 大成功
- d100 掷出 100 → 大失败

## 项目结构

```
mai-dice/
├── plugin.py              # 插件入口
├── _manifest.json         # 插件清单
├── config.toml            # 配置文件
├── README.md
├── component/             # 核心组件
│   ├── character.py       # 人物卡数据模型
│   ├── dice.py            # 掷骰引擎
│   ├── log.py             # 疯狂症状
│   ├── output.py          # 输出模板
│   ├── recall_listener.py # 撤回监听
│   ├── rules.py           # CoC 规则
│   └── storage.py         # 存储管理
├── handler/               # 命令处理器
│   ├── character.py       # 人物卡命令
│   ├── dice.py            # 掷骰命令
│   ├── log.py             # 日志命令
│   ├── misc.py            # 杂项命令
│   ├── skill.py           # 技能检定命令
│   └── tool.py            # LLM 工具函数
└── data/                  # 数据目录
```

## 许可证

MIT License
