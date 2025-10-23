# 🚀 SAGE Unlearning Library - Examples & Documentation

This directory contains complete examples and documentation for the SAGE Unlearning Library.

> **From research to production: A comprehensive guide to privacy-preserving unlearning**

## ⚡ Quick Start (3 Steps, 5 Minutes)

### 1️⃣ Run the Demo
```bash
python basic_unlearning_demo.py
```
See unlearning in action with a simple example.

### 2️⃣ Choose Your Path
```bash
cat QUICK_REFERENCE.md
```
Find the right usage example for your scenario.

### 3️⃣ Deep Dive
Pick one of the `usage_*.py` files and explore the code with detailed comments.

---

## 📚 Documentation

### Quick Reference
| Example | Focus | Best For |
|---------|-------|----------|
| `basic_unlearning_demo.py` | Overview | Getting started |
| `usage_1_direct_library.py` | Direct Library Usage | Scripts & notebooks |
| `usage_2_sage_function.py` | SAGE Integration | Pipeline processing |
| `usage_3_memory_service.py` | MemoryService | VDB integration |
| `usage_4_complete_rag.py` | Full RAG System | Production scenarios |

---

### `basic_unlearning_demo.py` - Overview Demo
Basic demonstration of the SAGE Unlearning Library.

- Generates synthetic vectors
- Performs unlearning operations
- Compares different perturbation strategies
- Tracks privacy budget

**Run it:**
```bash
python basic_unlearning_demo.py
```

---

### `usage_1_direct_library.py` - Direct Library Usage
Use the unlearning library directly without SAGE runtime.

**Best for:**
- Independent scripts and notebooks
- Quick prototyping
- Algorithm research
- No SAGE dependency

**Covers:**
- Basic unlearning operations
- Custom privacy mechanisms
- Batch unlearning
- Similarity-based unlearning
- Privacy budget management

**Run it:**
```bash
python usage_1_direct_library.py
```

**Example snippet:**
```python
from sage.libs.unlearning import UnlearningEngine

engine = UnlearningEngine(epsilon=1.0, delta=1e-5)
result = engine.unlearn_vectors(
    vectors_to_forget=forget_vectors,
    vector_ids_to_forget=forget_ids,
    perturbation_strategy="adaptive"
)
```

---

### `usage_2_sage_function.py` - SAGE Function Integration
Use unlearning in SAGE Functions and Pipelines.

**Best for:**
- SAGE Pipeline integration
- Streaming data processing
- Multiple data sources
- Stateful processing

**Covers:**
- Vector generator Source Function
- Unlearning processor Function
- Result collector Sink Function
- Stateful pipelines
- Conditional unlearning

**Run it:**
```bash
python usage_2_sage_function.py
```

**Example pipeline:**
```python
env.from_source(VectorGenerator) \
   .map(UnlearningProcessor, epsilon=1.0) \
   .sink(ResultCollector)

env.submit(autostop=True)
```

---

### `usage_3_memory_service.py` - MemoryService Integration
Integrate unlearning with MemoryService and VDB.

**Best for:**
- RAG systems
- VDB integration
- Memory management
- Cross-service coordination

**Covers:**
- DPMemoryService class
- Vector storage and retrieval
- DP-based forgetting
- Privacy budget tracking
- Multi-collection management

**Run it:**
```bash
python usage_3_memory_service.py
```

**Example usage:**
```python
service = DPMemoryService(epsilon=1.0)
service.create_collection("documents")

# Store memories
mem_id = service.store_memory(
    collection_name="documents",
    content=text,
    vector=embedding
)

# Forget with DP
result = service.forget_with_dp(
    collection_name="documents",
    memory_ids=[mem_id],
    perturbation_strategy="adaptive"
)
```

---

### `usage_4_complete_rag.py` - Complete RAG System
Full RAG system with privacy unlearning.

**Best for:**
- Production RAG systems
- User data deletion (GDPR compliance)
- Malicious content removal
- Audit logging

**Covers:**
- RAG corpus initialization
- Document retrieval
- User deletion requests
- Malicious content detection
- Compliance audit logs

**Run it:**
```bash
python usage_4_complete_rag.py
```

**Example usage:**
```python
system = RAGUnlearningSystem(epsilon=1.0)

# Handle GDPR deletion request
result = system.handle_user_deletion_request(
    collection_name="knowledge_base",
    user_id="user_123"
)

# Remove malicious content
result = system.handle_malicious_content_removal(
    collection_name="knowledge_base",
    detection_keywords=["spam", "malware"]
)

# Audit compliance
logs = system.get_audit_log()
```

---

## 🚀 Quick Start Guide

### 1. Set Up Environment
```bash
cd /path/to/SAGE
pip install -e packages/sage-libs
```

### 2. Run Examples in Order
```bash
# Start with basic overview
python examples/unlearning/basic_unlearning_demo.py

# Try direct library usage
python examples/unlearning/usage_1_direct_library.py

# Explore SAGE integration
python examples/unlearning/usage_2_sage_function.py

# See service integration
python examples/unlearning/usage_3_memory_service.py

# Full RAG system
python examples/unlearning/usage_4_complete_rag.py
```

### 3. Understand the Architecture
```
┌─────────────────────────────────┐
│  Application Layer              │ ← usage_4_complete_rag.py
├─────────────────────────────────┤
│  MemoryService Integration      │ ← usage_3_memory_service.py
├─────────────────────────────────┤
│  SAGE Function/Pipeline         │ ← usage_2_sage_function.py
├─────────────────────────────────┤
│  Direct Library Usage           │ ← usage_1_direct_library.py
├─────────────────────────────────┤
│  Unlearning Library             │ ← basic_unlearning_demo.py
│  (sage.libs.unlearning)         │
└─────────────────────────────────┘
```

---

## 📊 Comparison: Which Example to Use?

### For Independent Research
→ Use **`usage_1_direct_library.py`**
- Zero dependencies on SAGE runtime
- Pure algorithm implementation
- Easy to experiment with

### For Pipeline Integration
→ Use **`usage_2_sage_function.py`**
- Integrates with SAGE Kernel
- Supports streaming data
- Stateful processing

### For RAG Systems
→ Use **`usage_3_memory_service.py`** + **`usage_4_complete_rag.py`**
- VDB integration
- Vector storage and retrieval
- Production-ready patterns

### For Learning
→ Start with **`basic_unlearning_demo.py`**
- Clear, simple examples
- Well-commented code
- Progressive complexity

---

## 💡 Key Concepts

### Privacy Budget
Each unlearning operation consumes privacy budget (ε, δ).

```python
# Check remaining budget
status = engine.get_privacy_status()
remaining = status['remaining_budget']
print(f"Remaining ε: {remaining['epsilon_remaining']:.4f}")
```

### Perturbation Strategies
Different strategies trade off privacy and utility:

- **`uniform`**: Simple, high noise, high privacy
- **`selective`**: Dimension-specific, medium privacy
- **`adaptive`**: Data-aware, balanced privacy-utility

### Neighbor Compensation
Prevents "collateral damage" to similar vectors when unlearning.

```python
engine = UnlearningEngine(
    enable_compensation=True  # Activate neighbor compensation
)
```

---

## 🔬 Research Extensions

Students can extend these examples by:

### 1. Custom Mechanisms
Implement new privacy mechanisms in `sage/libs/unlearning/algorithms/`:

```python
class MyCustomMechanism(BasePrivacyMechanism):
    def compute_noise(self, sensitivity, epsilon):
        # Your novel mechanism
        pass
```

### 2. Better Perturbation
Improve `vector_perturbation.py` with:
- PCA-preserving strategies
- Semantic-aware perturbation
- Learned perturbation (neural networks)

### 3. Evaluation Metrics
Implement in `sage/libs/unlearning/evaluation/metrics.py`:
- Residual Recall Rate
- Retention Stability
- Privacy-Utility Tradeoff Analysis

### 4. Advanced Composition
Enhance `privacy_accountant.py`:
- Advanced composition theorems
- Renyi DP
- Concentrated DP

---

## 📚 References

### Theory
- Dwork & Roth (2014): "Algorithmic Foundations of Differential Privacy"
- Cao & Yang (2015): "Towards Making Systems Forget with Machine Unlearning"
- Bourtoule et al. (2021): "Machine Unlearning"

### Implementation
- See `sage/libs/unlearning/` for detailed code comments
- Read docstrings in each module for research hints
- Check "STUDENT RESEARCH POINT" markers for extension ideas

---

## ❓ FAQ

**Q: Can I use these examples outside of SAGE?**
A: Yes! `usage_1_direct_library.py` works standalone without SAGE.

**Q: How do I test my own privacy mechanisms?**
A: Create a subclass of `BasePrivacyMechanism` and pass it to `UnlearningEngine`.

**Q: What's the privacy cost of forgetting N vectors?**
A: Approximately ε_per_vector * N (unless using advanced composition).

**Q: Can I reuse privacy budget across operations?**
A: Yes, the privacy accountant tracks total budget automatically.

**Q: How do I verify unlearning actually worked?**
A: See `sage/libs/unlearning/evaluation/metrics.py` for verification metrics.

---

## 🤝 Contributing

To contribute new examples:

1. Create a new file in `examples/unlearning/`
2. Document the scenario clearly
3. Add to this README
4. Ensure it runs with: `python your_example.py`
5. Submit a PR with description

---

## 📞 Support

- For library questions: Check `sage/libs/unlearning/` docstrings
- For integration issues: See `usage_*.py` examples
- For research ideas: Read the "TODO for Students" sections
- Show budget allocation strategies

#### `evaluation_demo.py`
- Compute all metrics (RRR, RS, etc.)
- Generate comparison plots
- Benchmark against baselines

## For Students

Each example should:
1. Be self-contained and runnable
2. Include clear comments explaining what's happening
3. Demonstrate a specific feature or technique
4. Provide visualizations when possible
5. Include references to relevant papers

## Creating New Examples

Template structure:
```python
"""
Example Title
=============

Brief description of what this example demonstrates.

**Research Focus**: What students should learn from this.
"""

import numpy as np
from sage.libs.unlearning import ...

def main():
    # Step 1: Setup
    print("Setting up...")

    # Step 2: Main demonstration
    print("Demonstrating...")

    # Step 3: Evaluation
    print("Evaluating...")

    # Step 4: Visualization (optional)
    print("Visualizing...")

if __name__ == "__main__":
    main()
```

## Running Examples

All examples assume you have installed the SAGE library:
```bash
cd /path/to/SAGE
pip install -e packages/sage-libs
```

Then run examples from this directory:
```bash
python basic_unlearning_demo.py
```

---

## Files Overview

| File | Type | Purpose |
|------|------|---------|
| **README.md** | 📖 Doc | ⭐ Start here - complete guide |
| **QUICK_REFERENCE.md** | 💡 Doc | 5-minute quick lookup |
| **TROUBLESHOOTING.md** | 🔧 Doc | Error solutions & debugging |
| **basic_unlearning_demo.py** | 🐍 Code | Simple demo to get started |
| **usage_1_direct_library.py** | 🐍 Code | Direct library usage (5 examples) |
| **usage_2_sage_function.py** | 🐍 Code | SAGE Function integration |
| **usage_3_memory_service.py** | 🐍 Code | VDB and MemService integration |
| **usage_4_complete_rag.py** | 🐍 Code | Production-ready RAG system |

---

## Choosing Your Usage Example

**I want to...**

- 🏃 **Quickly test the algorithm**
  → `python usage_1_direct_library.py`

- 🔧 **Integrate with SAGE Pipeline**
  → `python usage_2_sage_function.py`

- 🗄️ **Build a vector database system**
  → `python usage_3_memory_service.py`

- 🚀 **Deploy a production system**
  → Study `usage_4_complete_rag.py`

- ❓ **Fix an error**
  → See `TROUBLESHOOTING.md`

---

## Quick Reference

For detailed information, see:
- **How to choose?** → `QUICK_REFERENCE.md`
- **Errors & solutions** → `TROUBLESHOOTING.md`
- **Code examples** → `usage_*.py` files

## Common Commands

```bash
# Run the basic demo
python basic_unlearning_demo.py

# Check SAGE installation
python -c "from sage.libs.unlearning import UnlearningEngine; print('✓')"

# View quick reference
cat QUICK_REFERENCE.md

# Find troubleshooting help
grep -n "your error message" TROUBLESHOOTING.md
```

---

## Next Steps

1. ✅ Run `python basic_unlearning_demo.py`
2. ✅ Read `QUICK_REFERENCE.md`
3. ✅ Choose a `usage_*.py` file for your use case
4. ✅ Explore the code and modify parameters

**Happy learning! 🎉**
