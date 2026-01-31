# Leon TUI Guide

## Overview

Leon provides a modern terminal user interface (TUI) built with Textual framework.

## Interface Layout

```
╔══════════════════════════════════════════════════════════════════╗
║                         Leon Agent                                ║
╚══════════════════════════════════════════════════════════════════╝

👤 You: Create a hello.py file

🤖 Leon: I'll create that file for you...

🔧 Tool: write_file
   file_path: /path/to/hello.py
   content: print("Hello, World!")

📤 Result:
   File created: hello.py

🤖 Leon: Successfully created hello.py...

[Input]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Leon Agent | Thread: tui-abc123 | Ctrl+C: Exit
```

## Features

### Streaming Output
- Real-time AI response display
- Automatic Markdown rendering
- Syntax highlighting for code blocks

### Tool Call Visualization
- Tool calls shown with yellow border
- Parameters auto-formatted
- Results shown with green border

### Multi-line Input
- **Enter**: Send message
- **Shift+Enter**: Insert newline

### Conversation Management
- `/clear`: Clear history (new thread)
- `/exit` or `/quit`: Exit
- **Ctrl+T**: Browse and switch threads

## Shortcuts

| Shortcut | Action |
|----------|--------|
| Enter | Send message |
| Shift+Enter | New line |
| Ctrl+C | Exit |
| Ctrl+L | Clear history |
| Ctrl+T | Switch thread |
| Ctrl+Up/Down | History navigation |
| Ctrl+Y | Copy last message |
| Ctrl+E | Export to Markdown |

## Troubleshooting

### Terminal Compatibility

Recommended terminals:
- macOS: iTerm2 or Terminal.app
- Linux: GNOME Terminal, Konsole
- Windows: Windows Terminal

### Display Issues

```bash
clear
leonai
```
