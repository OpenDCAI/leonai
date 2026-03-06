---
name: sksadd
description: 从上次搜索结果安装 skill 到指定组，用法：/sksadd <组名> <编号>
---

从用户输入中提取组名和编号，执行并输出结果：

```bash
python3 "$(git rev-parse --show-toplevel 2>/dev/null)/.claude/skills/sksadd/add.py" "<GROUP>" "<INDEX>"
```
