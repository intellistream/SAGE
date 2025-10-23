# Test Coverage Improvement Plan

## 🎯 Current Status

### CI Test Results (After Latest Fixes)

**Fixed Issues** ✅:
- ~~studio module missing `__init__.py`~~ - **FIXED**
- ~~Test timeout (30s → 60s)~~ - **FIXED**  
- ~~Missing `minimal` install mode~~ - **FIXED**
- ~~Test fixture error (`test_import`)~~ - **FIXED**

**Current Test Status**:
- ✅ sage-tools: 78 passed, 4 fixed
- ⚠️ Coverage issues in multiple packages

### Coverage Report Summary

| Package | Coverage | Status | Priority |
|---------|----------|--------|----------|
| sage-common | 25% | 🔴 Low | P0 |
| sage-kernel | Unknown | ❓ Not tested | P1 |
| sage-platform | Unknown | ❓ Not tested | P1 |
| sage-middleware | Unknown | ❓ Not tested | P2 |
| sage-libs | Unknown | ❓ Not tested | P2 |
| sage-tools | ~80% | 🟡 Good | P3 |
| sage-apps | Unknown | ❓ Not tested | P3 |
| sage-benchmark | Unknown | ❓ Not tested | P3 |
| sage-studio | Unknown | ❓ Not tested | P3 |

## 🔍 Detailed Analysis

### sage-common (25% coverage)

**Critical Issues** 🔴:

1. **Logging utilities**: 0% coverage
   - `utils/logging/__init__.py` (202 lines, 0%)
   - `utils/logging/custom_logger.py` (35 lines, 0%)
   - `utils/logging/custom_formatter.py` (35 lines, 0%)

2. **Network utilities**: 0% coverage
   - `utils/network/base_tcp_client.py` (164 lines, 0%)
   - `utils/network/local_tcp_server.py` (319 lines, 0%)

3. **Configuration**: 0% coverage
   - `utils/config/manager.py` (101 lines, 0%)
   - `utils/config/loader.py` (37 lines, 0%)

4. **System utilities**: 0% coverage
   - `utils/system/environment.py` (171 lines, 0%)
   - `utils/system/network.py` (181 lines, 0%)
   - `utils/system/process.py` (203 lines, 0%)

5. **Embedding providers**: 0-40% coverage
   - Many embedding wrappers have low coverage
   - Service layer has 20% coverage

**Good Coverage** ✅:
- Core data types: 92-100%
- Serialization (dill): 61%
- Model registry: 85%

## 📋 Action Plan

### Phase 1: Fix Test Infrastructure (Week 1)

**P0 - Immediate**:
- [x] Fix conftest.py conflicts between packages
- [x] Add missing `__init__.py` files
- [x] Fix test timeouts
- [ ] Set up proper pytest configuration for multi-package workspace
- [ ] Add coverage reporting to CI

**Deliverable**: Clean test runs for all packages

### Phase 2: Increase sage-common Coverage (Week 2-3)

**P1 - Critical Modules** (Target: 60%):
1. Logging utilities
   - Test log formatting
   - Test log rotation
   - Test custom handlers

2. Configuration management
   - Test config loading
   - Test environment variables
   - Test config validation

3. Network utilities
   - Test TCP client/server
   - Test connection handling
   - Test error cases

**P2 - Important Modules** (Target: 40%):
4. System utilities
   - Test process management
   - Test environment detection
   - Test network utilities

5. Embedding services
   - Test factory patterns
   - Test error handling
   - Mock external API calls

### Phase 3: Other Packages (Week 4-5)

**P1 - Core Packages**:
- sage-kernel: Target 50% coverage
- sage-platform: Target 50% coverage

**P2 - Domain Packages**:
- sage-middleware: Target 40% coverage
- sage-libs: Target 40% coverage

**P3 - Application Packages**:
- sage-apps: Target 30% coverage
- sage-benchmark: Target 30% coverage
- sage-studio: Target 30% coverage

### Phase 4: Performance & CI Optimization (Week 6)

**Performance Issues**:
1. **Slow `sage dev status` command** (>30s)
   - Profile import times
   - Lazy load heavy modules
   - Cache expensive operations
   - Target: <10s

2. **Slow test suite**
   - Parallelize tests where possible
   - Mock external dependencies
   - Optimize fixtures
   - Target: <5min for full suite

**CI Improvements**:
- [ ] Add coverage badges to README
- [ ] Set up codecov.io integration
- [ ] Add pre-commit hooks for coverage checks
- [ ] Create test coverage dashboard

## 🛠️ Implementation Guidelines

### Writing Tests

```python
# Good test structure
def test_feature_name():
    """Test description focusing on behavior"""
    # Arrange
    setup_data = ...
    
    # Act
    result = function_under_test(setup_data)
    
    # Assert
    assert result == expected_value
```

### Mocking External Dependencies

```python
from unittest.mock import Mock, patch

@patch('sage.common.components.sage_embedding.openai.OpenAI')
def test_openai_embedding(mock_openai):
    """Test OpenAI embedding without actual API calls"""
    mock_openai.return_value.embeddings.create.return_value = Mock(
        data=[Mock(embedding=[0.1, 0.2, 0.3])]
    )
    # Test logic here
```

### Coverage Targets

- **New Code**: 80% minimum
- **Existing Code**: Incremental improvement
- **Critical Paths**: 90%+ (security, data integrity)
- **UI/CLI**: 50%+ (harder to test)

## 📊 Progress Tracking

### Week 1 (Current)
- [x] Fix CI test failures
- [x] Document coverage gaps
- [ ] Set up coverage tracking

### Week 2-3
- [ ] sage-common: 25% → 60%
- [ ] Add logging tests
- [ ] Add config tests
- [ ] Add network tests

### Week 4-5
- [ ] sage-kernel: 0% → 50%
- [ ] sage-platform: 0% → 50%
- [ ] sage-middleware: 0% → 40%

### Week 6
- [ ] Performance optimization
- [ ] CI improvements
- [ ] Documentation updates

## 🎓 Why This Matters

1. **Confidence**: High test coverage means we can refactor safely
2. **Bugs**: Catch issues before they reach production
3. **Documentation**: Tests serve as executable documentation
4. **Onboarding**: New contributors can understand code through tests
5. **Maintenance**: Easier to verify bug fixes and add features

## 📝 Next Steps

**Immediate** (This Week):
1. Run full test suite locally and document all failures
2. Fix pytest configuration for multi-package workspace
3. Add coverage reporting to CI workflow

**Short Term** (Next 2 Weeks):
1. Write tests for highest-priority modules (logging, config)
2. Mock external dependencies (APIs, databases)
3. Reach 60% coverage for sage-common

**Long Term** (1 Month):
1. Establish 50%+ coverage across all core packages
2. Optimize test suite performance
3. Integrate coverage checks into PR workflow

---

**Created**: 2025-10-23
**Last Updated**: 2025-10-23
**Status**: In Progress
**Owner**: Development Team
