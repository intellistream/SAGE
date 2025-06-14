# <div align="center">🧠 SAGE: A Dataflow-Native Framework for LLM Reasoning<div>


SAGE is a dataflow-native reasoning framework built from the ground up to support modular, controllable, and transparent workflows over Large Language Models (LLMs). It addresses common problems in existing LLM-augmented systems (like RAG and Agents), such as hard-coded orchestration logic, opaque execution paths, and limited runtime control. SAGE introduces a dataflow-centric abstraction, modeling reasoning workflows as directed acyclic graphs (DAGs) composed of typed operators.
## ✨ Features

- 🧩 **Declarative & Modular Composition**: Build complex reasoning pipelines from typed, reusable operators. The dataflow graph cleanly separates what to compute from how to compute it.

- 🔀 **Unified Data and Control Flow**: Express conditional branching, tool routing, and fallback logic declaratively within the graph structure, eliminating brittle, imperative control code.

- 💾 **Native Stateful Operators**: Memory is a first-class citizen. Model session, task, and long-term memory as stateful nodes directly within the graph for persistent, context-aware computation.

- ⚡ **Asynchronous & Resilient Runtime**: The engine executes DAGs asynchronously in a non-blocking, data-driven manner. It features stream-aware queues, event-driven scheduling, and built-in backpressure to handle complex workloads gracefully.

- 📊 **Built-in Observability & Introspection**: An interactive dashboard provides runtime instrumentation out-of-the-box. Visually inspect execution graphs, monitor operator-level metrics, and debug pipeline behavior in real-time.

## 🔧 Installation

To accommodate different user environments and preferences, we provide **comprehensive setup scripts** that support multiple installation modes. Simply run the top-level `./setup.sh` script and choose from the following four installation options:

```bash
./setup.sh
```

You will be prompted to select one of the following modes:

1. **Minimal Setup**  
   Set up only the Conda environment.

2. **Setup with Ray**  
   Includes the minimal setup and additionally installs [Ray](https://www.ray.io/), a distributed computing framework.

3. **Setup with Docker**  
   Launches a pre-configured Docker container and sets up the Conda environment inside it.

4. **Full Setup**  
   Launches the Docker container, installs all required dependencies (including **CANDY**, our in-house vector database), and sets up the Conda environment.

---

Alternatively, you can install the project manually:

1. Create a new Conda environment with Python ≥ 3.11:

   ```bash
   conda create -n sage python=3.11
   conda activate sage
   ```

2. Install the package from the root directory:

   ```bash
   pip install .
   ```

This method is recommended for advanced users who prefer manual dependency management or wish to integrate the project into existing workflows.


- **Install from source**


## 🚀 Quick Start

## 🧩 Components

## 🎨 SAGE-UI