# MaiDice

MaiBot TRPG 骰娘插件 - 星星骰娘-重骰版！

基于 [astrbot_plugin_trpgdice_rerolled](https://github.com/HosisoraLing/astrbot_plugin_trpgdice_rerolled) 移植。

## 功能

- **基础掷骰**: `.r 1d100`、`.r 3d6+5`、`.r 10d6k5`
- **暗骰**: `.dh 1d100`（结果私聊发送）
- **技能检定**: `.ra 侦查 50`、`.rab 2 射击`、`.rap 1 闪避`
- **理智检定**: `.sc 1d6/1d10`、`.ti`（临时疯狂）、`.li`（长期疯狂）
- **人物卡**: `.pc create/show/list/change/delete/update`
- **先攻系统**: `.ri`、`.init`、`.ed`
- **角色生成**: `.coc`、`.dnd`
- **日志管理**: `.log new/on/off/end/del/list/export`
- **其他**: `.fireball`、`.jrrp`、`.setcoc`、`.dicehelp`

## 安装

1. 将 `mai-dice` 目录放入 MaiBot 的 `plugins/` 目录
2. 重启 MaiBot

## 配置

配置文件：`config.toml`

- `plugin.enabled`: 是否启用插件
- `dice.default_faces`: 默认骰子面数
- `llm_mode.enabled`: 是否启用 LLM 美化
- `napcat.enable_recall_listener`: 是否启用撤回监听

## 文案自定义

文案模板定义在 `_conf_schema.json` 中，可通过创建 `data/overrides.json` 覆盖：

```json
{
  "output": {
    "dice.normal.success": "{name}掷骰 {result} = {total}",
    "skill_check.success": "{nickname}进行{skill_name}检定: {roll}/{skill_value} 成功！"
  }
}
```

## 命令前缀

支持 `.`、`。`、`/` 三种前缀。

## 项目结构

```
mai-dice/
├── plugin.py              # 插件入口
├── _manifest.json         # 插件清单
├── _conf_schema.json      # 配置 Schema
├── config.toml            # 配置文件
├── component/             # 核心组件
│   ├── character.py       # 人物卡
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
