# Feature Plan: Studio-Middleware Integration & Agentic Framework Upgrade

**Branch**: `feature/studio-middleware-integration-poc`
**Status**: In Progress / Verification Phase

## Overview

This plan outlines the comprehensive upgrade to the SAGE Agentic Framework (L3), its integration into the Middleware (L4), and the exposure of these capabilities to SAGE Studio (L6). It also includes significant improvements to the installation and environment health check systems.

The goal is to make `sage-libs` (L3) the source of truth for agentic behaviors and integrate it into **`sage-gateway`** (so `sage chat` becomes smart) and `sage-studio`.

**Key Architectural Shift**:
*   **L3 (Algorithm Core)**: Provides the core algorithms and runtime engines. `AgentRuntime` is designed as a service-like component (similar to `sage-db`), providing stateful execution capabilities.
*   **L4 (Service/Operator)**: Wraps L3 algorithms into composable operators and services.
*   **Sage Chat (formerly Studio)**: The focus shifts from just a "Drag-and-Drop" editor to a fully agentic conversational interface ("Sage Chat"). The system now analyzes user intent, plans execution using `AgentOrchestrator`, and calls tools dynamically, rather than just executing static pipelines.

## Architecture Changes

### 1. L3: Agentic Framework Upgrade (`sage-libs`)

Refactored the core agent runtime to be more modular and generator-based.

*   **`AgentRuntime`** (`sage.libs.agentic.agents.runtime.agent`):
    *   **Role**: Core execution engine (Service-like). It manages the state and execution loop of an agent.
    *   New generator-based execution engine (`step()` yields events).
    *   Supports pluggable `Profile`, `Planner`, and `MCPRegistry` (Tools).
    *   Standardized event types: `plan`, `action`, `observation`, `error`, `reply`.
*   **`SimpleLLMPlanner`** (`sage.libs.agentic.agents.planning.simple_llm_planner`):
    *   Basic LLM-based planner that generates a sequence of steps based on user query and tool descriptions.
*   **`SearcherBot`** (`sage.libs.agentic.agents.bots.searcher_bot`):
    *   Updated to support the new execution model.

### 2. L4: Middleware Operators (`sage-middleware`)

Created new operators to wrap L3 capabilities and add middleware-specific features (like refinement).

*   **`AgentRuntimeOperator`** (`sage.middleware.operators.agentic.runtime`):
    *   Wraps L3 `AgentRuntime` into a standard L4 `MapOperator`.
    *   Handles configuration parsing and component instantiation (Profile, Generator, Planner, Tools).
    *   Enables "Drag-and-Drop" agent creation in Studio.
*   **`RefinedSearcherOperator`** (`sage.middleware.operators.agentic.refined_searcher`):
    *   **New Component**: Combines L3 `SearcherBot` with L4 `RefinerService`.
    *   **Flow**: Search (L3) -> Results -> Refinement (L4) -> Refined Results.
    *   Implements MCP-compatible `call()` method for easy tool integration.

### 3. L6: Studio Integration (`sage-studio` -> `sage-chat`)

Updated Studio to leverage the new middleware operators and improve the chat experience. The long-term goal is to evolve "Studio" into "Sage Chat", a unified agentic interface.

*   **`AgentOrchestrator`** (`sage.studio.services.agent_orchestrator`):
    *   **Core Logic for Sage Chat**: Handles user intent analysis, planning, and dynamic tool execution.
    *   Now initializes `ResearcherAgent` with a dynamic tool registry.
    *   Registers `NatureNewsTool` (via adapter) and `ArxivSearchTool`.
*   **`MiddlewareToolAdapter`** (`sage.studio.tools.middleware_adapter`):
    *   **Key Integration**: Generic adapter to convert synchronous L4 `MiddlewareBaseTool` into asynchronous L6 Studio Tools.
    *   Auto-generates Pydantic schemas from tool signatures for proper validation.
*   **Backend API** (`sage.studio.config.backend.api`):
    *   **Security/Config**: Dynamic CORS configuration. Now automatically allows `SagePorts.STUDIO_FRONTEND` and supports `SAGE_STUDIO_ALLOWED_ORIGINS` env var.

### 4. Environment & Installation (`tools/install`)

Significant improvements to the developer experience and environment stability.

*   **`quickstart.sh`**:
    *   **Auto-Doctor**: Now runs `run_full_diagnosis` by default before installation.
    *   **Auto-Fix**: If issues are found, automatically triggers `run_auto_fixes`.
*   **`environment_doctor.sh`**:
    *   **CLI Conflict Detection**: Added `check_cli_conflicts` to detect "zombie" binaries (e.g., `~/.local/bin/sage`) that conflict with Conda environments.
    *   **Auto-Fix**: Added `fix_cli_conflicts` to safely remove these conflicting binaries.
    *   **Smart Interaction**: Skips confirmation in CI environments; supports `AUTO_CONFIRM_FIX` env var.

## Implementation Tracks (Detailed)

### Track 1: L3 Core Implementation (The Engine)
**Objective**: Replace placeholder code in `sage-libs` with functional implementations.
**Files**: `packages/sage-libs/src/sage/libs/agentic/agents/bots/searcher_bot.py`
*   Implement `search` method to accept a query and use provided tools.
*   Implement `execute` method to coordinate the search process.
*   Ensure it handles tool errors gracefully.

### Track 2: L3 Runtime Hardening (The Safety)
**Objective**: Upgrade `AgentRuntime` from "minimal viable" to "production ready".
**Files**: `packages/sage-libs/src/sage/libs/agentic/agents/runtime/agent.py`
*   Add error handling for tool execution failures inside the `step` loop.
*   Implement a safety check mechanism to validate tool arguments against the schema.
*   Ensure the `step` method returns structured observations.
*   Add logging for every step of the execution.

### Track 3: Gateway Integration (The Brain Upgrade)
**Objective**: Upgrade `sage-gateway` to use `AgentRuntime` for complex queries, making `sage chat` agentic.
**Files**: `packages/sage-gateway/src/sage/gateway/adapters/openai.py`
*   Import `AgentRuntime` and `SearcherBot` from `sage.libs.agentic`.
*   In `chat_completions`, add logic to detect if the user needs "research" or "complex reasoning".
*   If complex: Instantiate `AgentRuntime` with `SearcherBot` and execute the query.
*   If simple: Fallback to the existing `RAGPipeline`.

### Track 4: Tool Standardization (The Bridge)
**Objective**: Ensure Middleware tools have proper Pydantic schemas for L3 agents to consume.
**Status**: ✅ Completed
**Files**: `packages/sage-studio/src/sage/studio/tools/middleware_adapter.py`
*   Implement a robust schema generator that inspects the `input_types` dictionary of Middleware tools.
*   Map string types (e.g., "int", "str", "bool") to actual Python types.
*   Ensure the generated `args_schema` correctly reflects required vs optional parameters.

### Track 5: Context Refinement (The Optimizer)
**Objective**: Integrate `sage-refiner` to compress search results before passing them to the LLM.
**Status**: ✅ Completed
**Files**: `packages/sage-libs/src/sage/libs/agentic/agents/bots/searcher_bot.py`
*   Import `RefinerService` from `sage.middleware.components.sage_refiner`.
*   In `SearcherBot.execute`, call `refiner.refine(query=query, documents=results)`.

### Track 6: Streaming & Service Management (The Experience)
**Objective**: Enable real-time feedback in Studio and robust service lifecycle management.
**Status**: ✅ Completed
**Files**:
*   `packages/sage-studio/src/sage/studio/chat_manager.py`
*   `packages/sage-libs/src/sage/libs/agentic/agents/bots/searcher_bot.py`
*   `packages/sage-middleware/src/sage/middleware/agent/runtime.py`
*   **Service Management**:
    *   `sage studio start` now intelligently detects existing services via `SAGE_*_BASE_URL` env vars.
    *   `sage studio stop` defaults to preserving LLM/Embedding services (use `--all` to stop them).
    *   Fixed CORS issues in Backend API to support custom frontend ports (e.g., 35180).
*   **Streaming**:
    *   Implemented `search_generator` in `SearcherBot` for real-time search progress.
    *   Implemented `step_stream` in `AgentRuntime` to yield thought/action events.
    *   Studio backend now streams these events to the frontend for "Thinking..." UI.

## Verification Status

*   [x] **L3 Agent Runtime**: Unit tests passed (`tests/lib/agents/test_runtime_agent.py`).
*   [x] **L4 Operators**: `RefinedSearcherOperator` implemented.
*   [x] **Environment Doctor**: Verified fix for CLI conflicts (CI/CD artifact cleanup).
*   [x] **End-to-End Integration**: Verified that Studio can successfully call `RefinedSearcherOperator` via the `MiddlewareToolAdapter`.
    *   Created `tests/manual/test_refined_searcher_integration.py` and verified success.
    *   Fixed `MiddlewareToolAdapter` to support Pydantic V2 and async execution.
*   [x] **AgentRuntimeOperator**: Verified with `SimpleLLMPlanner`.
    *   Created `tests/manual/test_agent_runtime_operator.py` and verified success.
*   [x] **Gateway Updates**:
    *   OpenAI Adapter updated to import and utilize `RefinedSearcherOperator` and `AgentRuntime`.
    *   Verified code paths in `packages/sage-gateway/src/sage/gateway/adapters/openai.py`.
*   [x] **Service Management**:
    *   Verified `sage studio stop` preserves LLM services.
    *   Verified `sage studio start` reuses existing services.
    *   Verified CORS support for custom frontend ports.

## Next Steps

1.  Run integration tests for `RefinedSearcherOperator` within the Studio context.
2.  Verify the `AgentRuntimeOperator` works with the new `SimpleLLMPlanner`.
3.  Merge to `develop` after final validation.
