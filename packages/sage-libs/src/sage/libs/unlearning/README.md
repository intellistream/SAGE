# SAGE Unlearning Library

## 🎯 Overview

A modular framework for machine unlearning in RAG systems with differential privacy guarantees.

**Research Focus**: Selective unlearning with differential privacy that preserves utility on
retained data while providing provable privacy guarantees.

## 🏗️ Architecture

```
sage.libs.unlearning/
├── dp_unlearning/              # Core DP mechanisms
│   ├── base_mechanism.py       # Abstract base class for privacy mechanisms
│   ├── privacy_accountant.py   # Privacy budget tracking
│   ├── unlearning_engine.py    # Main orchestrator
│   ├── vector_perturbation.py  # Perturbation strategies
│   └── neighbor_compensation.py # Neighbor compensation
├── algorithms/                  # Concrete mechanism implementations
│   ├── laplace_unlearning.py   # Laplace mechanism
│   └── gaussian_unlearning.py  # Gaussian mechanism (TODO)
├── evaluation/                  # Evaluation metrics
│   └── metrics.py              # RRR, RS, privacy-utility trade-offs
└── benchmarks/                  # Standard datasets and tests (TODO)
```

## 🚀 Quick Start

### Installation

```bash
cd /path/to/SAGE
pip install -e packages/sage-libs
```

### Basic Usage

```python
from sage.libs.unlearning import UnlearningEngine
import numpy as np

# Initialize engine
engine = UnlearningEngine(
    epsilon=1.0,  # Privacy parameter
    delta=1e-5,  # Failure probability
    total_budget_epsilon=10.0,
    enable_compensation=True,
)

# Prepare data (example: 100 vectors of dimension 128)
vectors_to_forget = np.random.randn(5, 128)
vector_ids = [f"doc_{i}" for i in range(5)]

# Perform unlearning
result = engine.unlearn_vectors(
    vectors_to_forget=vectors_to_forget,
    vector_ids_to_forget=vector_ids,
    perturbation_strategy="uniform",
)

print(f"Success: {result.success}")
print(f"Privacy cost: ε={result.privacy_cost[0]:.4f}")
```

## 📚 For Students - Research Directions

This library is designed as a research platform. Students should focus on:

### 1. Privacy Mechanisms (Medium Difficulty)

**Location**: `algorithms/`

Implement new privacy mechanisms:

- ✅ Laplace mechanism (reference implementation)
- 🔲 Gaussian mechanism (TODO)
- 🔲 Exponential mechanism
- 🔲 Truncated Laplace
- 🔲 Your novel mechanism!

**Key files to modify**:

- Create new file in `algorithms/`
- Inherit from `BasePrivacyMechanism`
- Implement `compute_noise()` and `privacy_cost()`

### 2. Perturbation Strategies (Hard Difficulty)

**Location**: `dp_unlearning/vector_perturbation.py`

Design intelligent perturbation:

- ✅ Uniform perturbation (baseline)
- 🔲 Dimension-selective perturbation
- 🔲 PCA-preserving perturbation
- 🔲 Semantic-aware perturbation
- 🔲 Learned perturbation (neural networks)

**Research questions**:

- How to select which dimensions to perturb?
- How to preserve semantic structure?
- Can we learn optimal perturbation from data?

### 3. Neighbor Compensation (Research-Level)

**Location**: `dp_unlearning/neighbor_compensation.py`

Prevent collateral unlearning:

- ✅ Linear compensation (baseline)
- 🔲 Graph-based compensation
- 🔲 Iterative refinement
- 🔲 Learned compensation
- 🔲 Privacy-preserving compensation

**Research questions**:

- How far should compensation propagate?
- How to compensate without revealing neighbors?
- Can we prove bounds on utility preservation?

### 4. Privacy Accounting (Advanced)

**Location**: `dp_unlearning/privacy_accountant.py`

Implement tighter composition:

- ✅ Basic composition (sum of epsilons)
- 🔲 Advanced composition
- 🔲 Renyi DP composition
- 🔲 Concentrated DP
- 🔲 Adaptive budget allocation

**Research questions**:

- What's the tightest privacy bound?
- How to optimally allocate budget?
- Can we predict required budget?

### 5. Evaluation Metrics (Critical!)

**Location**: `evaluation/metrics.py`

Implement comprehensive evaluation:

- 🔲 Residual Recall Rate (RRR)
- 🔲 Retention Stability (RS)
- 🔲 Membership Inference Advantage
- 🔲 Privacy-Utility Pareto Frontier

**Research questions**:

- How to verify unlearning succeeded?
- How to measure utility degradation?
- What's the optimal privacy-utility trade-off?

## 📖 Key Concepts

### Differential Privacy

- **ε (epsilon)**: Privacy parameter. Smaller = more private.
- **δ (delta)**: Failure probability for approximate DP.
- **Sensitivity**: How much one data point can change the output.

### Unlearning Goals

1. **Completeness**: Forgotten data should not affect outputs
1. **Utility**: Retained data should work as before
1. **Efficiency**: Fast unlearning without retraining
1. **Verifiability**: Provable guarantees of unlearning

### Privacy-Utility Trade-off

```
More noise (higher ε) → Better privacy, worse utility
Less noise (lower ε) → Worse privacy, better utility
```

Goal: Find the optimal point on the Pareto frontier!

## 🎓 Research Workflow

### Phase 1: Understanding (Week 1-2)

1. Read the code and comments
1. Run `examples/unlearning/basic_unlearning_demo.py`
1. Understand each component's role
1. Read referenced papers

### Phase 2: Implementation (Month 1-2)

1. Choose a research direction (mechanisms, perturbation, compensation)
1. Implement your novel algorithm
1. Add unit tests
1. Create examples demonstrating your method

### Phase 3: Evaluation (Month 2-3)

1. Implement evaluation metrics
1. Compare against baselines
1. Generate plots and analysis
1. Document your findings

### Phase 4: Writing (Month 3-4)

1. Write technical report
1. Prove theoretical properties
1. Prepare conference submission
1. Create presentation

## 📊 Expected Outputs

### Code Contributions

- New privacy mechanisms in `algorithms/`
- Enhanced perturbation in `vector_perturbation.py`
- Better compensation in `neighbor_compensation.py`
- Comprehensive metrics in `evaluation/`

### Research Outputs

- Technical report (10-15 pages)
- Conference paper (ICML, NeurIPS, VLDB)
- Open-source implementation
- Benchmarks and comparisons

### Theoretical Contributions

- Proofs of privacy guarantees
- Utility bounds
- Complexity analysis
- Novel algorithms

## 📚 Required Reading

### Foundational Papers

1. Dwork & Roth (2014): "Algorithmic Foundations of Differential Privacy"
1. Cao & Yang (2015): "Towards Making Systems Forget with Machine Unlearning"
1. Bourtoule et al. (2021): "Machine Unlearning" (SISA)

### Advanced Topics

4. Mironov (2017): "Renyi Differential Privacy"
1. Bun & Steinke (2016): "Concentrated Differential Privacy"
1. Guo et al. (2019): "Certified Data Removal"

### Recent Work

7. Sekhari et al. (2021): "Remember What You Want to Forget"
1. Chundawat et al. (2023): "Zero-Shot Machine Unlearning"
1. Jia et al. (2023): "Model Sparsity Can Simplify Machine Unlearning"

## 🤝 Getting Help

### Code Questions

- Check comments in source files (extensive documentation)
- Run examples in `examples/unlearning/`
- Read docstrings for each function

### Research Questions

- Refer to "STUDENT RESEARCH POINT" markers in code
- Read "TODO for Students" sections
- Consult referenced papers

### Implementation Issues

- Check `base_mechanism.py` for interface requirements
- Look at `SimpleLaplaceMechanism` as reference
- Follow type hints and docstring specifications

## 📝 Contributing

When you implement something new:

1. **Add comprehensive comments**

   - Explain what the code does
   - Explain why (theoretical justification)
   - Reference papers if applicable

1. **Include research notes**

   - What problem does this solve?
   - What are the trade-offs?
   - What are open questions?

1. **Provide examples**

   - Create a demo in `examples/unlearning/`
   - Show typical usage
   - Compare with baselines

1. **Document your work**

   - Update this README
   - Add docstrings
   - Write technical notes

## 🎯 Success Criteria

A successful student project should have:

- ✅ Novel algorithm implementation (passes unit tests)
- ✅ Theoretical analysis (proofs of privacy/utility)
- ✅ Empirical evaluation (experiments on real data)
- ✅ Comprehensive documentation (code + report)
- ✅ Conference-quality paper (ready for submission)

## 📧 Support

For questions or discussions about this research project:

- File issues on GitHub
- Join the SAGE community discussions
- Consult with your advisor

______________________________________________________________________

**Remember**: This is a research project, not just coding! Focus on:

- Novel ideas and insights
- Rigorous theoretical analysis
- Comprehensive empirical validation
- Clear communication of results

Good luck with your research! 🚀
