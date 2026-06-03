# Configuration Management System

<cite>
**Referenced Files in This Document**
- [ports.py](file://src/sage/foundation/config/ports.py)
- [user_paths.py](file://src/sage/foundation/config/user_paths.py)
- [__init__.py](file://src/sage/foundation/config/__init__.py)
- [config.yaml](file://config/config.yaml)
- [cluster.yaml](file://config/cluster.yaml)
- [models.json](file://config/models.json)
- [main.py](file://src/sage/cli/main.py)
- [gateway.py](file://src/sage/serving/gateway.py)
- [_version.py](file://src/sage/_version.py)
- [sagellm_registry.py](file://src/sage/foundation/model_registry/sagellm_registry.py)
- [cluster_context.py](file://src/sage/runtime/flownet/client/cluster_context.py)
</cite>

## Table of Contents
1. [Introduction](#introduction)
2. [Project Structure](#project-structure)
3. [Core Components](#core-components)
4. [Architecture Overview](#architecture-overview)
5. [Detailed Component Analysis](#detailed-component-analysis)
6. [Dependency Analysis](#dependency-analysis)
7. [Performance Considerations](#performance-considerations)
8. [Troubleshooting Guide](#troubleshooting-guide)
9. [Conclusion](#conclusion)
10. [Appendices](#appendices)

## Introduction
This document explains the Configuration Management System in SAGE, focusing on:
- Centralized port management via the SagePorts class
- XDG-compliant user directory handling via SageUserPaths and related utilities
- Environment variable handling, configuration precedence, and default value resolution
- Practical extension patterns for custom settings across development, staging, and production
- How configuration changes propagate through the SAGE architecture
- Validation, error handling, and debugging techniques
- Best practices for managing configuration across environments

## Project Structure
The configuration system spans two primary modules:
- Foundation configuration: centralized port and user paths management
- Global configuration files: YAML and JSON configuration assets shipped with the repository

```mermaid
graph TB
subgraph "Foundation Config"
CFG_INIT["config/__init__.py"]
PORTS["config/ports.py"]
PATHS["config/user_paths.py"]
end
subgraph "Global Config Assets"
CFG_YAML["config/config.yaml"]
CLUS_YAML["config/cluster.yaml"]
MODELS_JSON["config/models.json"]
end
subgraph "CLI and Serving"
CLI_MAIN["cli/main.py"]
SERVE_GW["serving/gateway.py"]
end
subgraph "Model Registry"
REG["foundation/model_registry/sagellm_registry.py"]
end
subgraph "Runtime"
RUNTIME_CTX["runtime/flownet/client/cluster_context.py"]
end
CFG_INIT --> PORTS
CFG_INIT --> PATHS
CLI_MAIN --> PORTS
CLI_MAIN --> PATHS
SERVE_GW --> PORTS
REG --> PATHS
RUNTIME_CTX --> CFG_YAML
RUNTIME_CTX --> CLUS_YAML
```

**Diagram sources**
- [__init__.py:1-7](file://src/sage/foundation/config/__init__.py#L1-L7)
- [ports.py:1-199](file://src/sage/foundation/config/ports.py#L1-L199)
- [user_paths.py:1-195](file://src/sage/foundation/config/user_paths.py#L1-L195)
- [config.yaml:1-60](file://config/config.yaml#L1-L60)
- [cluster.yaml:1-91](file://config/cluster.yaml#L1-L91)
- [models.json:1-67](file://config/models.json#L1-L67)
- [main.py:1-204](file://src/sage/cli/main.py#L1-L204)
- [gateway.py:48-135](file://src/sage/serving/gateway.py#L48-L135)
- [sagellm_registry.py:53-137](file://src/sage/foundation/model_registry/sagellm_registry.py#L53-L137)
- [cluster_context.py:134-159](file://src/sage/runtime/flownet/client/cluster_context.py#L134-L159)

**Section sources**
- [__init__.py:1-7](file://src/sage/foundation/config/__init__.py#L1-L7)
- [ports.py:1-199](file://src/sage/foundation/config/ports.py#L1-L199)
- [user_paths.py:1-195](file://src/sage/foundation/config/user_paths.py#L1-L195)
- [config.yaml:1-60](file://config/config.yaml#L1-L60)
- [cluster.yaml:1-91](file://config/cluster.yaml#L1-L91)
- [models.json:1-67](file://config/models.json#L1-L67)
- [main.py:1-204](file://src/sage/cli/main.py#L1-L204)
- [gateway.py:48-135](file://src/sage/serving/gateway.py#L48-L135)
- [sagellm_registry.py:53-137](file://src/sage/foundation/model_registry/sagellm_registry.py#L53-L137)
- [cluster_context.py:134-159](file://src/sage/runtime/flownet/client/cluster_context.py#L134-L159)

## Core Components
- SagePorts: Centralized port assignments and helpers for availability checks, environment overrides, and diagnostics.
- SageUserPaths: XDG-compliant user directory provider with convenience properties for config, data, state, and cache, plus structured subdirectories and migration utilities.
- Global configuration assets: config.yaml, cluster.yaml, and models.json define defaults and cluster topology.

Key responsibilities:
- Provide a single source of truth for ports and directories
- Support environment-driven overrides and diagnostics
- Offer standardized locations for configuration and caches across platforms

**Section sources**
- [ports.py:25-199](file://src/sage/foundation/config/ports.py#L25-L199)
- [user_paths.py:53-195](file://src/sage/foundation/config/user_paths.py#L53-L195)
- [config.yaml:1-60](file://config/config.yaml#L1-L60)
- [cluster.yaml:1-91](file://config/cluster.yaml#L1-L91)
- [models.json:1-67](file://config/models.json#L1-L67)

## Architecture Overview
The configuration system underpins SAGE’s CLI, serving, runtime, and model registry layers. It ensures consistent defaults, environment overrides, and predictable paths across deployments.

```mermaid
graph TB
CLI["CLI (sage)"] --> MAIN["cli/main.py"]
MAIN --> PORTS["SagePorts"]
MAIN --> PATHS["SageUserPaths"]
SERVE["Serving (gateway)"] --> GW["serving/gateway.py"]
GW --> PORTS
MODELREG["Model Registry"] --> PATHS
RUNTIME["Runtime (cluster context)"] --> CFG["config/config.yaml"]
RUNTIME --> CLUS["config/cluster.yaml"]
```

**Diagram sources**
- [main.py:1-204](file://src/sage/cli/main.py#L1-L204)
- [ports.py:25-199](file://src/sage/foundation/config/ports.py#L25-L199)
- [user_paths.py:53-195](file://src/sage/foundation/config/user_paths.py#L53-L195)
- [gateway.py:48-135](file://src/sage/serving/gateway.py#L48-L135)
- [sagellm_registry.py:53-137](file://src/sage/foundation/model_registry/sagellm_registry.py#L53-L137)
- [cluster_context.py:134-159](file://src/sage/runtime/flownet/client/cluster_context.py#L134-L159)
- [config.yaml:1-60](file://config/config.yaml#L1-L60)
- [cluster.yaml:1-91](file://config/cluster.yaml#L1-L91)

## Detailed Component Analysis

### SagePorts: Centralized Port Management
SagePorts encapsulates:
- Named port constants for gateway, serving, engines, embeddings, and benchmarks
- Environment-aware selection helpers (e.g., WSL vs. standard)
- Availability checks and port-finding utilities
- Environment variable override for ports
- Diagnostic reporting for port statuses

```mermaid
classDiagram
class SagePorts {
<<frozen dataclass>>
+int SAGELLM_GATEWAY
+int EDGE_DEFAULT
+int SAGELLM_SERVE_PORT
+int SAGELLM_ENGINE_PORT
+int SAGELLM_SERVE_PORT_2
+int SAGELLM_ENGINE_PORT_2
+int LLM_DEFAULT
+int LLM_SECONDARY
+int EMBEDDING_DEFAULT
+int EMBEDDING_SECONDARY
+int BENCHMARK_EMBEDDING
+int BENCHMARK_API
+int SAGELLM_DEFAULT
+int GATEWAY_DEFAULT
+int LLM_WSL_FALLBACK
+int BENCHMARK_LLM
+get_recommended_llm_port() int
+get_llm_ports() int[]
+get_embedding_ports() int[]
+get_benchmark_ports() int[]
+is_available(port, host) bool
+find_available_port(start, end) int?
+get_from_env(env_var, default) int
+check_port_status(port, host) dict
+diagnose() void
}
```

- Environment variable handling: Ports can be overridden via environment variables using a dedicated reader method.
- Diagnostics: A diagnostic routine prints environment hints and port listening/availability status for core services.

Practical usage examples:
- CLI gateway probing uses the gateway port constant for defaults.
- Serving integration builds commands and URLs using recommended ports and environment overrides.
- Runtime and cluster context resolution rely on environment variables and default files.

**Diagram sources**
- [ports.py:25-199](file://src/sage/foundation/config/ports.py#L25-L199)
- [main.py:127-153](file://src/sage/cli/main.py#L127-L153)
- [gateway.py:55-117](file://src/sage/serving/gateway.py#L55-L117)

**Section sources**
- [ports.py:25-199](file://src/sage/foundation/config/ports.py#L25-L199)
- [main.py:127-153](file://src/sage/cli/main.py#L127-L153)
- [gateway.py:55-117](file://src/sage/serving/gateway.py#L55-L117)

### SageUserPaths: XDG-Compliant User Paths
SageUserPaths provides:
- XDG directory resolution via environment variables or platform defaults
- Structured subdirectories for config, data, state, and cache
- Convenience properties for key files and directories (e.g., config.yaml, cluster.yaml, logs)
- Migration utilities for legacy configuration locations

```mermaid
classDiagram
class SageUserPaths {
-_ensure_structure() void
+config_dir Path
+data_dir Path
+state_dir Path
+cache_dir Path
+config_file Path
+cluster_config_file Path
+credentials_file Path
+models_dir Path
+sagellm_models_dir Path
+sessions_dir Path
+vector_db_dir Path
+finetune_dir Path
+flows_dir Path
+logs_dir Path
+get_log_file(name) Path
+hf_cache_dir Path
+stream_cache_dir Path
+sagellm_cache_dir Path
}
class Functions {
+get_user_config_dir() Path
+get_user_data_dir() Path
+get_user_state_dir() Path
+get_user_cache_dir() Path
+get_user_paths() SageUserPaths
+get_legacy_sage_home() Path
+migrate_legacy_config() void
}
SageUserPaths <.. Functions : "uses"
```

- Directory creation: Ensures subdirectories exist on first access.
- Legacy migration: Copies select legacy files into XDG locations when present.

**Diagram sources**
- [user_paths.py:53-195](file://src/sage/foundation/config/user_paths.py#L53-L195)

**Section sources**
- [user_paths.py:53-195](file://src/sage/foundation/config/user_paths.py#L53-L195)

### Global Configuration Assets
- config/config.yaml: Defines authentication, embedding, gateway, LLM, Ray, remote, and studio settings with defaults.
- config/cluster.yaml: Defines cluster topology, SSH, daemon, output, monitoring, and JobManager settings.
- config/models.json: Lists local and remote models with base URLs, default flags, and environment variable substitution for API keys.

These assets are consumed by runtime and CLI components to drive behavior and defaults.

**Section sources**
- [config.yaml:1-60](file://config/config.yaml#L1-L60)
- [cluster.yaml:1-91](file://config/cluster.yaml#L1-L91)
- [models.json:1-67](file://config/models.json#L1-L67)

### CLI Integration and Propagation
- The CLI status and doctor commands surface configuration directories and runtime health, integrating SageUserPaths and SagePorts.
- The serve gateway command constructs gateway configurations and probes endpoints using port constants and environment overrides.

```mermaid
sequenceDiagram
participant User as "User"
participant CLI as "CLI main.py"
participant Paths as "SageUserPaths"
participant Ports as "SagePorts"
participant Serve as "Serving gateway.py"
User->>CLI : "sage status"
CLI->>Paths : get_user_paths()
CLI-->>User : "Print config/data/state/cache dirs"
User->>CLI : "sage serve gateway --probe"
CLI->>Serve : SageServeConfig(host, port)
Serve->>Ports : use constants and env overrides
Serve-->>CLI : "Probe result (ok/url/status/error)"
CLI-->>User : "JSON or human-readable output"
```

**Diagram sources**
- [main.py:69-98](file://src/sage/cli/main.py#L69-L98)
- [main.py:127-153](file://src/sage/cli/main.py#L127-L153)
- [gateway.py:55-117](file://src/sage/serving/gateway.py#L55-L117)
- [ports.py:25-199](file://src/sage/foundation/config/ports.py#L25-L199)

**Section sources**
- [main.py:69-98](file://src/sage/cli/main.py#L69-L98)
- [main.py:127-153](file://src/sage/cli/main.py#L127-L153)
- [gateway.py:55-117](file://src/sage/serving/gateway.py#L55-L117)
- [ports.py:25-199](file://src/sage/foundation/config/ports.py#L25-L199)

### Model Registry and Configuration
The model registry resolves its root directory from SageUserPaths, ensuring consistent storage of model artifacts and manifests.

```mermaid
flowchart TD
Start(["Resolve model registry root"]) --> GetPaths["Get SageUserPaths"]
GetPaths --> Compute["Compute sagellm_models_dir"]
Compute --> Ensure["Ensure directory exists"]
Ensure --> Done(["Root path ready"])
```

**Diagram sources**
- [sagellm_registry.py:57-64](file://src/sage/foundation/model_registry/sagellm_registry.py#L57-L64)
- [user_paths.py:105-110](file://src/sage/foundation/config/user_paths.py#L105-L110)

**Section sources**
- [sagellm_registry.py:57-64](file://src/sage/foundation/model_registry/sagellm_registry.py#L57-L64)
- [user_paths.py:105-110](file://src/sage/foundation/config/user_paths.py#L105-L110)

### Environment Variable Handling and Precedence
- Ports: Environment variables can override port constants via a dedicated reader method.
- Cluster context: Runtime components resolve cluster names from environment variables, falling back to default files.
- Models: API keys in models.json can be resolved from environment variables at runtime.

```mermaid
flowchart TD
A["Resolve cluster name"] --> EnvVar["Check environment variable"]
EnvVar --> |Found| UseEnv["Use environment value"]
EnvVar --> |Not Found| DefaultFile["Read default file (~/.flownet/config.yaml)"]
DefaultFile --> FoundDefault{"Value found?"}
FoundDefault --> |Yes| UseDefault["Use default value"]
FoundDefault --> |No| Error["Raise unresolved cluster target error"]
```

**Diagram sources**
- [cluster_context.py:134-159](file://src/sage/runtime/flownet/client/cluster_context.py#L134-L159)

**Section sources**
- [ports.py:103-111](file://src/sage/foundation/config/ports.py#L103-L111)
- [cluster_context.py:81-94](file://src/sage/runtime/flownet/client/cluster_context.py#L81-L94)
- [cluster_context.py:134-159](file://src/sage/runtime/flownet/client/cluster_context.py#L134-L159)
- [models.json:46-47](file://config/models.json#L46-L47)

## Dependency Analysis
- CLI depends on SagePorts and SageUserPaths for status, doctor, and serve gateway commands.
- Serving integration depends on SagePorts for default ports and URL construction.
- Model registry depends on SageUserPaths for storage roots.
- Runtime cluster context resolution depends on environment variables and default files.

```mermaid
graph LR
CLI["cli/main.py"] --> PORTS["config/ports.py"]
CLI --> PATHS["config/user_paths.py"]
SERVE["serving/gateway.py"] --> PORTS
REG["foundation/model_registry/sagellm_registry.py"] --> PATHS
RUNTIME["runtime/flownet/client/cluster_context.py"] --> CFG["config/config.yaml"]
RUNTIME --> CLUS["config/cluster.yaml"]
```

**Diagram sources**
- [main.py:1-204](file://src/sage/cli/main.py#L1-L204)
- [ports.py:25-199](file://src/sage/foundation/config/ports.py#L25-L199)
- [user_paths.py:53-195](file://src/sage/foundation/config/user_paths.py#L53-L195)
- [gateway.py:48-135](file://src/sage/serving/gateway.py#L48-L135)
- [sagellm_registry.py:53-137](file://src/sage/foundation/model_registry/sagellm_registry.py#L53-L137)
- [cluster_context.py:134-159](file://src/sage/runtime/flownet/client/cluster_context.py#L134-L159)
- [config.yaml:1-60](file://config/config.yaml#L1-L60)
- [cluster.yaml:1-91](file://config/cluster.yaml#L1-L91)

**Section sources**
- [main.py:1-204](file://src/sage/cli/main.py#L1-L204)
- [gateway.py:48-135](file://src/sage/serving/gateway.py#L48-L135)
- [sagellm_registry.py:53-137](file://src/sage/foundation/model_registry/sagellm_registry.py#L53-L137)
- [cluster_context.py:134-159](file://src/sage/runtime/flownet/client/cluster_context.py#L134-L159)

## Performance Considerations
- Port availability checks use brief connection attempts; avoid repeated checks in tight loops.
- Diagnostics iterate predefined port sets; keep diagnostic runs infrequent in automated contexts.
- XDG directory resolution caches computed paths; initialization cost occurs once per process.

## Troubleshooting Guide
Common issues and resolutions:
- Port conflicts:
  - Use availability checks and the port finder to select alternate ports.
  - Run the diagnostic tool to inspect listening states.
- Gateway unresponsive:
  - Probe the gateway URL constructed from SagePorts defaults and environment overrides.
  - Verify CLI status shows gateway health.
- Legacy configuration migration:
  - Use the migration utility to copy legacy files into XDG locations.
- Cluster context resolution failures:
  - Ensure environment variables or default files provide a valid cluster name.

Validation and debugging techniques:
- CLI status and doctor commands surface configuration directories and runtime health.
- Serving gateway probe returns structured results for downstream automation.
- Runtime cluster context reads default files safely and raises explicit errors when unresolved.

**Section sources**
- [ports.py:85-128](file://src/sage/foundation/config/ports.py#L85-L128)
- [ports.py:131-188](file://src/sage/foundation/config/ports.py#L131-L188)
- [main.py:69-98](file://src/sage/cli/main.py#L69-L98)
- [main.py:127-153](file://src/sage/cli/main.py#L127-L153)
- [user_paths.py:167-181](file://src/sage/foundation/config/user_paths.py#L167-L181)
- [cluster_context.py:81-94](file://src/sage/runtime/flownet/client/cluster_context.py#L81-L94)
- [cluster_context.py:134-159](file://src/sage/runtime/flownet/client/cluster_context.py#L134-L159)

## Conclusion
The SAGE Configuration Management System provides a robust, XDG-compliant foundation for user directories and centralized port management. It integrates seamlessly with CLI, serving, runtime, and model registry components, enabling consistent behavior across environments. By leveraging environment variables, structured defaults, and diagnostics, teams can reliably operate SAGE in development, staging, and production.

## Appendices

### Practical Extension Patterns
- Adding custom ports:
  - Define new named constants in SagePorts and expose getters for priority ordering.
  - Use environment overrides to steer defaults in different environments.
- Extending user directories:
  - Add new convenience properties to SageUserPaths for specialized subdirectories.
  - Ensure creation during initialization to avoid runtime errors.
- Environment-driven configuration:
  - Prefer environment variables for ports and cluster names.
  - Provide sensible defaults in global YAML/JSON assets for out-of-the-box usability.

### Deployment Scenarios
- Development:
  - Use lower port ranges and local caches; rely on defaults for quick iteration.
- Staging:
  - Override ports and directories via environment variables; enable diagnostics for health checks.
- Production:
  - Pin ports and directories; centralize configuration via environment variables and default files; monitor gateway and runtime health via CLI and serving probes.

### Version and Release Notes Reference
- Version information is surfaced by the CLI and used in status output.

**Section sources**
- [main.py:101-103](file://src/sage/cli/main.py#L101-L103)
- [_version.py](file://src/sage/_version.py)