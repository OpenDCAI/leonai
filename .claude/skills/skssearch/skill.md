---
name: skssearch
description: 搜索 SkillsMP，用法：/skssearch <关键词>（请使用英文关键词）
---

从用户输入中提取搜索关键词，执行并输出结果：

```bash
python3 "$(git rev-parse --show-toplevel 2>/dev/null)/.claude/skills/skssearch/search.py" "<KEYWORD>"
```
