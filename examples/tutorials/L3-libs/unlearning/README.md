# Machine Unlearning Examples

This directory contains examples and tutorials for using SAGE's machine unlearning capabilities.

## Overview

Machine unlearning enables models to "forget" specific training data, which is crucial for:

- **Privacy compliance**: GDPR "Right to be Forgotten"
- **Data removal**: Removing incorrect or outdated data
- **Bias mitigation**: Removing biased training samples
- **Security**: Removing poisoned data from models

## Files

- `machine_unlearning_examples.py` - Comprehensive examples demonstrating:
  - Basic unlearning workflow
  - Differential privacy mechanisms
  - Evaluation metrics
  - Algorithm comparisons
  - Real-world GDPR compliance scenario

## Running Examples

```bash
# From SAGE root directory
cd examples/tutorials/unlearning
python machine_unlearning_examples.py
```

## Key Concepts

### Differential Privacy Mechanisms

- **Gaussian Mechanism**: Provides (ε,δ)-differential privacy by adding Gaussian noise
- **Laplace Mechanism**: Provides ε-differential privacy by adding Laplace noise

### Core Components

1. **Privacy Mechanisms** (`sage.libs.unlearning.algorithms`)

   - `GaussianMechanism`: (ε,δ)-DP noise addition
   - `LaplaceMechanism`: ε-DP noise addition

1. **Unlearning Engine** (`sage.libs.unlearning.dp_unlearning`)

   - `UnlearningEngine`: Orchestrates the unlearning process
   - `VectorPerturbation`: Applies noise to model parameters
   - `NeighborCompensation`: Compensates for neighboring records
   - `PrivacyAccountant`: Tracks privacy budget across operations

1. **Evaluation Tools** (`sage.libs.unlearning.evaluation`)

   - `UnlearningMetrics`: Evaluates forgetting quality and model utility

## Further Reading

- Implementation details: `packages/sage-libs/src/sage/libs/unlearning/`
- Research papers: See docstrings in mechanism implementations
- SAGE documentation: `docs/` directory

## Student Research Tasks

The unlearning module includes TODO items for advanced research:

- Analytic Gaussian mechanism (tighter bounds)
- Concentrated differential privacy
- Privacy amplification by subsampling
- Advanced composition techniques

See the source code in `packages/sage-libs/src/sage/libs/unlearning/algorithms/` for details.
