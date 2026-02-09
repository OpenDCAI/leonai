# Leon AI v0.3.0 Release Notes

**Release Date**: 2026-02-09
**Total Commits**: 230
**Contributors**: Development Team

---

## 📊 Overview

This is a major feature release with significant architectural improvements, new capabilities, and comprehensive testing infrastructure.

### Statistics
- 🎯 **63 New Features**
- 🐛 **56 Bug Fixes**
- 📚 **30 Documentation Updates**
- 🔧 **23 Refactorings**
- ✅ **28 New Tests** (25 passing, 88% coverage)

---

## 🌟 Major Features

### 1. **SummaryStore - Persistent Conversation Memory**
Persistent storage of conversation summaries with automatic restoration across sessions.

**Key Capabilities:**
- SQLite-based persistent storage of conversation summaries
- Automatic restoration on agent restart
- Split Turn detection for large messages (>50k characters)
- Graceful degradation and error recovery
- Thread-isolated storage with concurrent access support

**Performance:**
- Query: ~0.12ms (target <50ms) ✅
- Write: ~3.8ms (target <100ms) ✅
- Database size: ~456KB for 100 summaries ✅

**Related Commits:**
- `9a9204d` - feat: implement SummaryStore for persistent conversation summaries
- `16debed` - test: comprehensive test suite for SummaryStore
- `844249d` - fix: initialize checkpointer before middleware stack

---

### 2. **Terminal Persistence & Frontend Integration**
Complete rearchitecture of terminal/sandbox session management with web UI.

**Key Features:**
- Persistent terminal sessions across agent restarts
- Session pause/resume functionality
- Ground-truth sandbox session management
- Real-time session status tracking
- Frontend integration with React UI

**Architecture:**
- `ChatSession` - Session lifecycle management
- `Terminal` - Persistent terminal state
- `Lease` - Resource locking and session control
- `Runtime` - Execution state tracking

**Related PRs:**
- #9 - Terminal persistence & frontend integration
- #10 - Ground-truth sandbox sessions and session-level controls

**Related Commits:**
- `c5ef9e9` - Merge PR #9: Terminal persistence & frontend integration
- `b06b533` - fix: ground-truth sandbox sessions and session-level controls
- `a84bc4e` - feat: complete terminal persistence integration
- `d99f68b` - feat: implement terminal persistence architecture

---

### 3. **Web Chat UI (FastAPI + React)**
Full-featured web interface for Leon AI with sandbox management.

**Features:**
- FastAPI backend with WebSocket support
- React frontend with TypeScript
- Real-time chat interface
- Sandbox session management UI
- Workspace and session views
- Task progress tracking

**Components:**
- Backend: `services/web/main.py` (FastAPI)
- Frontend: `frontend/app/` (React + Vite)
- API: RESTful + WebSocket endpoints

**Related Commits:**
- `e660d63` - feat: add web chat UI (FastAPI backend + React frontend)
- `29393aa` - feat: add sandbox management to web chat UI
- `2c55db2` - feat: wire frontend app to backend with sandbox and workspace views

---

### 4. **Sandbox Infrastructure Layer**
Complete sandbox architecture with multiple provider support.

**Providers:**
- **Local Sandbox** - Direct local execution
- **Docker Sandbox** - Containerized execution with metrics
- **E2B Sandbox** - Cloud-based execution
- **AgentBay Sandbox** - Managed cloud sandbox

**Features:**
- Provider abstraction layer
- Session management and persistence
- File system isolation
- Command execution isolation
- Workspace initialization hooks
- Per-thread storage isolation

**CLI Commands:**
```bash
leonai sandbox ls                    # List sessions
leonai sandbox new                   # Create session
leonai sandbox rm <id>               # Remove session
leonai sandbox pause <id>            # Pause session
leonai sandbox resume <id>           # Resume session
leonai sandbox metrics <id>          # Show metrics
leonai sandbox destroy-all-sessions  # Cleanup
```

**Related Commits:**
- `88e498d` - refactor: promote sandbox to infrastructure layer
- `f0db86f` - feat: add E2B sandbox provider
- `bc2abf2` - feat: add docker sandbox and agentbay image id
- `6447745` - feat: add sandbox CLI subcommands

---

### 5. **Monitor Middleware - Runtime Observability**
Comprehensive runtime monitoring with token tracking and cost calculation.

**Monitors:**
- **TokenMonitor** - 6-way token tracking (input/output/reasoning/cache_read/cache_write/total)
- **CostCalculator** - Dynamic pricing via OpenRouter API with disk cache
- **ContextMonitor** - Context window size tracking
- **StateMonitor** - Agent state and flags tracking

**Features:**
- Real-time token usage tracking
- Cost estimation per request
- OpenRouter API integration for dynamic pricing
- Bundled pricing fallback (314 models)
- TUI integration with status display

**Related Commits:**
- `48fe9ee` - feat: add monitor middleware with token, context, and state monitors
- `8665dfe` - feat: integrate MonitorMiddleware into agent and TUI
- `054a0e9` - feat: model config enhancement + token monitor with cost tracking

---

### 6. **Queue Mode - Message Injection**
Advanced message routing system for dynamic agent control.

**Queue Types:**
- **steer** - High-priority control messages
- **followup** - Post-execution follow-ups
- **collect** - Background data collection
- **backlog** - Deferred tasks
- **interrupt** - Emergency interrupts

**Features:**
- Priority-based message routing
- State-driven queue processing
- IDLE callback triggers
- Suspend/resume support

**Related Commits:**
- `09c13de` - feat: add Queue Mode for message injection during agent execution
- `aa5be70` - feat: add Queue Mode for message injection during agent execution

---

### 7. **Task & Todo Middleware**
Sub-agent orchestration and task management.

**Features:**
- Hierarchical task management
- Sub-agent spawning and coordination
- Task status tracking
- Dependency management
- Progress reporting

**Related Commits:**
- `e2b2966` - feat: add Task and Todo middleware for sub-agent orchestration
- `34a91be` - feat: add Task and Todo middleware for sub-agent orchestration

---

### 8. **Agent Profile System**
Flexible configuration system with YAML-based profiles.

**Features:**
- YAML-based configuration
- Environment variable support
- Per-skill configuration control
- Fine-grained tool control
- Profile inheritance

**Configuration Hierarchy:**
```
~/.leon/profile.yaml          # User profile
project/profiles/*.yaml       # Project profiles
```

**Related Commits:**
- `f201040` - feat: implement Agent Profile system
- `317cf4c` - feat: add per-skill configuration control
- `070f28a` - feat: add fine-grained tool control

---

### 9. **Skills System**
Progressive disclosure system for agent capabilities.

**Features:**
- Skill-based capability organization
- Progressive disclosure to reduce prompt size
- MCP (Model Context Protocol) integration
- Namespace isolation for tools

**Related Commits:**
- `0c32d9c` - feat: implement skills system with progressive disclosure
- `eef47b8` - feat: add MCP skill support with langchain-mcp-adapters

---

### 10. **Time Travel & Session Management**
Checkpoint-based session management with time travel capabilities.

**Features:**
- Session checkpointing
- Time travel to previous states
- Session persistence
- State restoration

**Related Commits:**
- `8ea24f1` - feat: add time travel and session management (v0.2.4)
- `f87de60` - feat: add time travel and session management (v0.2.4)

---

## 🐛 Critical Bug Fixes

### Initialization & Lifecycle
- `844249d` - **Fix checkpointer initialization order** - Resolves `'LeonAgent' object has no attribute 'checkpointer'`
- `16debed` - **Fix missing imports** - Add Path and SummaryStore imports to middleware
- `fb1aae2` - **Fix refresh active sandbox status** - Proper status updates after session actions
- `54f945c` - **Fix paused chat sessions** - Keep visible and auto-resume on run

### Sandbox & Execution
- `3579855` - **Fix sandbox read_file crash** - Handle file read errors gracefully
- `edd797b` - **Fix agentbay ContextSync persistence** - Proper path handling
- `b7aba35` - **Fix sandbox tool names** - Use standard names (read_file, run_command)
- `7c695e4` - **Fix thread_id tracking** - Use ContextVar instead of threading.local

### Configuration & Tools
- `ba5db96` - **Fix ChatOpenAI usage** - Explicit provider when base_url is set
- `d2b3f7d` - **Fix MCP tool whitelist** - Correct filtering logic
- `50865d5` - **Fix MCP tools in LangGraph** - Include in CLI export

---

## 🔧 Major Refactorings

### Architecture
- `88e498d` - **Promote sandbox to infrastructure layer** - Clean separation of concerns
- `625a095` - **Decouple sandbox/middleware** - Single-direction dependency
- `129f17a` - **Clean up sandbox architecture** - Remove legacy code

### Code Organization
- `1e522c4` - **Replace shell middleware with command middleware** - Better abstraction
- `47ffc2f` - **Eliminate schema duplication** - DRY principle in middleware
- `7ebac65` - **Remove legacy store layers** - Enforce lease pause semantics

---

## 📚 Documentation

### Architecture & Design
- `41744d8` - Add architecture design documents
- `8a24510` - Add architecture and design analysis documents
- `6e557aa7` - Update README and SANDBOX.md for sandbox architecture
- `e9f5b0` - Add sandbox usage and configuration guide

### Guides & References
- `e47cf6f` - Add profile README and finalize implementation
- `e59807d` - Add profiles/README.md with configuration principles
- `fbd7803` - Update task.md with completed features

---

## ✅ Testing Infrastructure

### Test Suite (28 tests, 25 passing)

**Unit Tests (14/14)** - `tests/middleware/memory/test_summary_store.py`
- Concurrent reads/writes (5 threads write, 10 threads read)
- Large data handling (1MB summaries)
- Special characters and SQL injection protection
- Edge cases (negative indices, empty strings)
- Database locking and retry logic
- Transaction rollback on errors

**Integration Tests (8/8)** - `tests/middleware/memory/test_memory_middleware_integration.py`
- Summary save on compaction
- Summary restore on startup
- Split Turn save and restore
- Rebuild from checkpointer
- Multiple threads isolation
- Error handling (missing thread_id, unavailable checkpointer)
- Second compaction updates

**Performance Tests (3/3)** - `tests/middleware/memory/test_summary_store_performance.py`
- Query performance with 1000 summaries (~0.12ms)
- Concurrent write performance (10 threads, ~3.8ms)
- Database size growth (100 summaries, ~456KB)

**E2E Tests (3 created)** - `tests/test_e2e_summary_persistence.py`
- Full agent summary persistence
- Agent split turn e2e
- Agent concurrent threads

**Coverage:**
- `summary_store.py`: 88% (target ≥85%) ✅
- Overall: 70%

**New Test Files:**
- `tests/conftest.py` - Test configuration
- `tests/middleware/memory/test_memory_middleware_integration.py`
- `tests/middleware/memory/test_summary_store_performance.py`
- `tests/test_e2e_summary_persistence.py`
- `tests/test_chat_session.py`
- `tests/test_lease.py`
- `tests/test_terminal.py`
- `tests/test_runtime.py`
- And many more...

---

## 🚀 Performance Improvements

### SummaryStore
- Query latency: ~0.12ms (240x faster than target)
- Write latency: ~3.8ms (26x faster than target)
- Storage efficiency: ~4.5KB per summary

### Sandbox
- Parallel session listing
- Optimized file operations
- Reduced context switching

---

## 🔄 Breaking Changes

### Configuration
- Profile system replaces old config format
- Workspace path validation changes
- Tool whitelist format updated

### Sandbox
- Tool names standardized (read_file, run_command, etc.)
- Context path default changed from `/workspace` to `/root`
- Session management API updated

### Middleware
- Shell middleware replaced with command middleware
- Schema format changes in FileSystemMiddleware

---

## 📦 Dependencies

### New Dependencies
- `langchain-mcp-adapters` - MCP protocol support
- `aiosqlite` - Async SQLite for checkpointer
- `fastapi` - Web backend
- `uvicorn` - ASGI server
- `websockets` - Real-time communication

### Updated Dependencies
- `langchain>=1.2.6` - Core framework updates
- Various security and bug fix updates

---

## 🛠️ Migration Guide

### From v0.2.3 to v0.3.0

1. **Update Configuration**
   ```bash
   # Old: ~/.leon/config.yaml
   # New: ~/.leon/profile.yaml
   ```

2. **Update Tool Names** (if using sandbox)
   ```python
   # Old: sandbox_read_file
   # New: read_file
   ```

3. **Update Workspace Path** (if customized)
   ```yaml
   # Old default: /workspace
   # New default: /root
   ```

4. **Install New Version**
   ```bash
   pip install --upgrade leonai
   ```

---

## 🙏 Acknowledgments

This release represents 230 commits and significant collaborative effort. Special thanks to all contributors who helped with:
- Architecture design and implementation
- Testing and quality assurance
- Documentation and guides
- Bug reports and fixes

---

## 🔗 Links

- **PyPI**: https://pypi.org/project/leonai/0.3.0/
- **GitHub**: https://github.com/OpenDCAI/leonai
- **Documentation**: See `docs/` folder
- **Issues**: https://github.com/OpenDCAI/leonai/issues

---

## 📝 Full Changelog

For the complete list of 230 commits, see:
```bash
git log v0.2.3..v0.3.0
```

Or view on GitHub: https://github.com/OpenDCAI/leonai/compare/v0.2.3...v0.3.0
