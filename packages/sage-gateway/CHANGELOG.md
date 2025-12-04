# SAGE Gateway Changelog

## [Unreleased] - 2025-12-03

### Breaking Changes

- **Removed `UnifiedAPIServer`**: The `unified_api_server.py` module has been removed from
  `sage-common`. Control Plane functionality is now integrated into `sage-gateway`.
  - Users should use `sage gateway start` instead of manually starting UnifiedAPIServer.
  - All `/v1/management/*` endpoints are now served by sage-gateway.

### Added

- **`sage gateway` CLI command group**: New unified CLI for Gateway management

  - `sage gateway start` - Start Gateway (background by default, port 8000)
  - `sage gateway stop` - Stop Gateway (graceful/force)
  - `sage gateway status` - Show status, engines, and backends
  - `sage gateway logs` - View logs (with `--follow` support)
  - `sage gateway restart` - Restart Gateway

- **Control Plane integration**: sage-gateway now includes full Control Plane functionality

  - `GET /v1/management/engines` - List engines
  - `POST /v1/management/engines/start` - Start engine
  - `POST /v1/management/engines/stop` - Stop engine
  - `GET /v1/management/backends` - List registered backends
  - `GET /v1/management/gpu` - GPU resource status

- **Dynamic backend discovery**: UnifiedInferenceClient can now discover backends dynamically

  - Backend list refresh every 30 seconds
  - Automatic failover when backends become unavailable

### Changed

- **Updated CLI hints**: `sage llm engine` commands now hint to use `sage gateway start`
- **Updated `sage studio start`**: Now indicates Gateway includes Control Plane scheduler
- Renamed package from `sage-gateway` to `isage-gateway` for consistency
- Use dynamic version from `_version.py` instead of hardcoded version
- Auto-start Gateway when running `sage studio start` (unless `--no-gateway`)
- Improved startup workflow with auto-install and auto-build features

### Developer Notes

The Gateway unification addresses the previous split architecture:

- Before: Two separate gateways (sage-gateway for Chat/RAG, UnifiedAPIServer for Control Plane)
- After: Single unified gateway (`sage-gateway`) with all functionality

Migration guide:

```bash
# Before
python -c "from sage.common.components.sage_llm.unified_api_server import ..."

# After
sage gateway start
```

## [0.1.1] - 2025-11-21

### Changed

- Renamed package from `sage-gateway` to `isage-gateway` for consistency
- Use dynamic version from `_version.py` instead of hardcoded version
- Auto-start Gateway when running `sage studio start` (unless `--no-gateway`)
- Improved startup workflow with auto-install and auto-build features

### Added

- Gateway status display in `sage studio status`
- `--gateway` flag to `sage studio stop` to optionally stop Gateway
- `--no-auto-install` flag to disable automatic dependency installation
- `--no-auto-build` flag to disable automatic production build
- Interactive confirmation prompts before auto-install/auto-build
- Comprehensive startup documentation with auto-features

### Developer Experience

**Auto-install Dependencies**: When running `sage studio start` for the first time, if
`node_modules` is missing, the system will prompt: "开始安装依赖?" with default yes. This eliminates the
need to manually run `sage studio install`.

**Auto-build Production**: When starting in production mode (`--prod`), if the `dist/` build output
is missing, the system will prompt: "开始构建?" with default yes. This ensures production builds are
always ready.

**Workflow Simplification**:

- Before: `sage studio install` → `sage studio build` → `sage studio start`
- After: `sage studio start` (confirms and auto-executes missing steps)

## [0.1.0] - 2025-11-17

### Added

#### Phase 6: Advanced Chat Features (Commit: 3d303a7e)

- ✅ **Markdown Rendering**: Full GitHub-flavored markdown support with react-markdown
- ✅ **Syntax Highlighting**: Code blocks with VS Code Dark+ theme via react-syntax-highlighter
- ✅ **Rich Formatting**: Tables, lists, blockquotes, headings with custom styling
- ✅ **Code Block Features**: Copy button, language detection, syntax highlighting
- ✅ **Typography Plugin**: Tailwind typography for consistent prose styling
- ✅ **Smart Rendering**: Simple text for user messages, rich markdown for AI responses

**Features**:

- Automatic language detection from code fence markers
- One-click code copying
- Responsive table rendering
- Custom styled components (links, lists, headings, blockquotes)
- Streaming cursor animation
- Dark theme support for code blocks

**Dependencies Added**:

```json
{
  "react-markdown": "^9.x",
  "remark-gfm": "^4.x",
  "react-syntax-highlighter": "^15.x",
  "@tailwindcss/typography": "^0.5.x"
}
```

#### Phase 3: SAGE Kernel Integration (Commit: 9f38cb55)

- ✅ **Real LLM Execution**: Integrated SAGE DataStream kernel for actual LLM inference
- ✅ **OpenAI Client Integration**: Connect to OpenAI-compatible APIs (OpenAI, DashScope, vLLM,
  Ollama)
- ✅ **Development Mode**: Automatic fallback to echo mode when no API key configured
- ✅ **Environment Configuration**: Support for multiple LLM backends via env vars
- ✅ **Comprehensive Tests**: 5 kernel integration tests covering mock LLM, dev mode, multi-turn,
  error handling, config

**Environment Variables**:

```bash
SAGE_CHAT_MODEL=qwen-max                  # Model name
SAGE_CHAT_BASE_URL=https://...            # API base URL
SAGE_CHAT_API_KEY=your-key                # API key (optional for dev mode)
ALIBABA_API_KEY=your-key                  # Alternative for Alibaba DashScope
```

#### Phase 4: NeuroMem Session Backend (Commit: 868b9964)

- ✅ **NeuroMem Storage**: Use SAGE's native memory system for session persistence
- ✅ **Dual Backend Support**: Choose between file storage or NeuroMem via environment
- ✅ **Metadata Tracking**: Store session stats (created_at, last_active, message_count, tokens)
- ✅ **Cross-Instance Persistence**: Sessions persist across gateway restarts
- ✅ **Comprehensive Tests**: 11 tests for NeuroMem storage covering all operations

**Features**:

- TextStorage for session JSON data
- MetadataStorage for session statistics
- Automatic fallback to file storage if NeuroMem unavailable
- Environment-based configuration

**Configuration**:

```bash
SAGE_GATEWAY_SESSION_BACKEND=neuromem     # Options: file, neuromem
SAGE_GATEWAY_SESSION_NEUROMEM_PATH=~/.sage/gateway/neuromem_sessions
```

#### Phase 5: End-to-End Testing (Commit: 81f1c974)

- ✅ **7 E2E Integration Tests**: Complete chat workflow validation
- ✅ **Dev Mode Testing**: Verify echo responses without API key
- ✅ **Multi-Turn Conversations**: Test context preservation across messages
- ✅ **Streaming Responses**: Validate SSE streaming format
- ✅ **Session Persistence**: Test session sharing across adapter instances
- ✅ **Error Handling**: Verify graceful error responses
- ✅ **Stats Validation**: Test session statistics accuracy
- ✅ **NeuroMem Backend**: Test NeuroMem storage integration

**Test Coverage**:

- Total: 37 tests (100% passing)
  - 7 E2E chat flow tests
  - 5 Kernel integration tests
  - 11 NeuroMem storage tests
  - 3 OpenAI adapter tests
  - 5 Server endpoint tests
  - 6 Session manager tests

### Changed

- **Removed TODO Comments**: Cleaned up completed TODOs from codebase
- **Improved Documentation**: Updated README with NeuroMem configuration
- **Fixed OpenAI Client**: Added `seed=42` parameter for reproducibility
- **Better Test Fixtures**: Use monkeypatch to properly isolate test environments

### Technical Improvements

- **Architecture**: Pluggable storage backend with SessionStorage protocol
- **Type Safety**: Full type hints across session management
- **Error Handling**: Graceful degradation when LLM unavailable
- **Testing**: Comprehensive test coverage for all features
- **Documentation**: Clear configuration examples and environment variables

### Benefits

1. **No External Dependencies**: NeuroMem eliminates need for Redis
1. **Showcases SAGE Capabilities**: Uses native SAGE memory system
1. **Flexible Configuration**: Easy switching between storage backends
1. **Production Ready**: Full error handling and session management
1. **Well Tested**: 37 tests covering all functionality

## Summary

The gateway is now production-ready with:

- ✅ Real LLM integration (OpenAI, DashScope, vLLM, Ollama)
- ✅ Native NeuroMem session persistence
- ✅ Comprehensive test coverage (37 tests)
- ✅ Flexible configuration via environment variables
- ✅ Graceful error handling and dev mode
- ✅ Full OpenAI API compatibility

**Next Steps**: Advanced chat features (code highlighting, markdown rendering, file uploads)
