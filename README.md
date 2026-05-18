# MaiBot TRPG 骰娘插件

星星骰娘-重骰版！一个可自定义的 MaiBot 骰娘插件。

基于 [astrbot_plugin_trpgdice_rerolled](https://github.com/HosisoraLing/astrbot_plugin_trpgdice_rerolled) 移植。

## 功能

### 基础掷骰
- 支持 `NdM` 格式掷骰
- 支持复杂算式: `3d6+2d4-1d8`
- 支持保留最高骰: `10d6k5`
- 支持重复掷骰: `3#1d20`

### 技能检定
- 普通检定: `.ra 侦查 50`
- 奖励骰检定: `.rab 2 射击`
- 惩罚骰检定: `.rap 1 闪避`
- 支持 5 种 CoC 大成功/大失败规则

### 人物卡管理
- 创建/显示/切换/删除人物卡
- 支持属性和技能管理
- 数据持久化存储

### 理智检定
- SAN Check: `.sc 1d6/1d10`
- 临时疯狂: `.ti`
- 长期疯狂: `.li`

### 先攻系统
- 掷先攻: `.ri`
- 先攻列表管理: `.init`
- 回合推进: `.ed`

### 日志系统
- 创建/暂停/恢复/结束日志
- 支持导出和统计

### 角色生成
- CoC 角色属性生成: `.coc`
- DnD 角色属性生成: `.dnd`
- 技能成长检定: `.en`

### LLM 美化
- 可选的 LLM 风格化输出
- 支持自定义系统提示词

## 安装

1. 将 `maibot_trpg_dice` 目录放入 MaiBot 的 `plugins/` 目录
2. 启动 MaiBot，插件会自动加载
3. 使用 `.dicehelp` 查看帮助信息

## 命令列表

| 命令 | 说明 |
|------|------|
| `.r <表达式>` | 基础掷骰 |
| `.ra <技能名> [技能值]` | 技能检定 |
| `.rab <骰数> <技能名>` | 奖励骰检定 |
| `.rap <骰数> <技能名>` | 惩罚骰检定 |
| `.sc <成功公式>/<失败公式>` | 理智检定 |
| `.ti` | 临时疯狂 |
| `.li` | 长期疯狂 |
| `.pc <操作> [参数]` | 人物卡管理 |
| `.st <属性> <值>` | 设置属性 |
| `.ri [调整值]` | 掷先攻 |
| `.init [操作]` | 先攻列表 |
| `.ed` | 结束回合 |
| `.coc [数量]` | 生成 CoC 角色 |
| `.dnd [数量]` | 生成 DnD 角色 |
| `.en <技能名> [技能值]` | 技能成长 |
| `.log <操作> [参数]` | 日志管理 |
| `.setcoc [规则号]` | 设置 CoC 规则 |
| `.fireball [环数]` | 火球术伤害 |
| `.jrrp` | 今日人品 |
| `.dicehelp` | 帮助信息 |

支持 `.`, `。`, `/` 三种命令前缀。

## 配置

插件配置位于 `config.toml`，可通过 MaiBot WebUI 编辑。

### 主要配置项

- **plugin**: 插件基础设置
- **dice**: 骰子参数
- **output**: 输出模板
- **llm_mode**: LLM 美化设置

## 数据存储

插件使用 MaiBot 的 `ctx.db` 进行数据持久化：

- 人物卡数据
- 日志记录
- 群组配置

## 开发

### 目录结构

```
maibot_trpg_dice/
├── _manifest.json       # 插件清单
├── plugin.py            # 插件入口
├── config.toml          # 配置文件
├── component/           # 核心组件
│   ├── dice.py          # 掷骰引擎
│   ├── character.py     # 人物卡管理
│   ├── rules.py         # 规则引擎
│   ├── log.py           # 日志系统
│   ├── output.py        # 输出格式化
│   ├── utils.py         # 工具函数
│   └── storage.py       # 存储管理
└── data/                # 数据文件
    ├── crazy_symptoms.json
    └── skill_templates.json
```

## 许可证

MIT License
