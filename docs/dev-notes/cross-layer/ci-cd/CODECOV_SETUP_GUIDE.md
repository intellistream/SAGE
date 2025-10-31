# Codecov Integration Setup Guide

**Date**: 2024-11-08  
**Author**: SAGE Team  
**Summary**: Codecov 配置指南

---


## Overview
This document explains how to set up codecov.io integration for the SAGE project to track test coverage across all commits and pull requests.

## Prerequisites
- GitHub repository with admin access
- Codecov.io account (can sign in with GitHub)

## Setup Steps

### 1. Enable Codecov for Repository

1. Visit https://codecov.io
2. Sign in with GitHub account
3. Navigate to repository list: https://codecov.io/gh/intellistream
4. Find `SAGE` repository and enable it
5. If not listed, click "Add new repository" and select `intellistream/SAGE`

### 2. Get Codecov Token

1. Go to repository settings: https://codecov.io/gh/intellistream/SAGE/settings
2. Navigate to "General" tab
3. Copy the "Repository Upload Token" (format: `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`)

### 3. Add Token to GitHub Secrets

1. Go to GitHub repository settings: https://github.com/intellistream/SAGE/settings/secrets/actions
2. Click "New repository secret"
3. Name: `CODECOV_TOKEN`
4. Value: Paste the token copied from step 2
5. Click "Add secret"

### 4. Verify Integration

After pushing code that triggers CI:

1. Check GitHub Actions run: https://github.com/intellistream/SAGE/actions
2. Look for "Upload Coverage to Codecov" step
3. Verify it completes successfully
4. Visit Codecov dashboard: https://codecov.io/gh/intellistream/SAGE
5. Confirm coverage report appears

## Configuration Files

### `.github/workflows/ci.yml`
Added steps to:
- Install pytest and coverage dependencies
- Run tests with coverage collection
- Generate coverage.xml report
- Upload to codecov.io
- Upload HTML reports as artifacts

### `codecov.yml`
Configures:
- **Coverage targets**:
  - `sage-common`: 60%
  - Core packages: 50%
  - Apps/tools: 40%
- **Precision**: 2 decimal places
- **Thresholds**: ±1-5% tolerance
- **Ignored paths**: tests, build artifacts, cache
- **Comment format**: on PRs

## Usage

### Viewing Coverage Reports

**Codecov Dashboard**: https://codecov.io/gh/intellistream/SAGE
- Overall project coverage
- Package-level breakdown
- Coverage trends over time
- Sunburst visualization

**Pull Request Comments**:
- Codecov bot automatically comments on PRs
- Shows coverage diff: changed vs base branch
- Highlights uncovered lines in changed files
- Provides flags for passing/failing status checks

**Local HTML Reports**:
- Generated in CI artifacts
- Download from Actions run page
- Extract and open `htmlcov/index.html`

### Reading the Badge

README badge shows current coverage:
- Green: ≥80% (excellent)
- Yellow: 50-79% (acceptable)
- Red: <50% (needs improvement)

Click badge to view full report on codecov.io.

## Coverage Goals

### Current Status (as of setup)
- **sage-common**: ~25% → Target: 60%
- **sage-kernel**: Unknown → Target: 50%
- **sage-platform**: Unknown → Target: 50%
- **sage-middleware**: Unknown → Target: 50%
- **sage-libs**: Unknown → Target: 50%
- **sage-tools**: Unknown → Target: 50%

### Critical Gaps (0% coverage)
- `sage.common.utils.logging`
- `sage.common.utils.config`
- `sage.common.utils.network`
- `sage.common.utils.system`

See `docs/dev-notes/TEST_COVERAGE_IMPROVEMENT_PLAN.md` for detailed roadmap.

## Troubleshooting

### Issue: "Upload Coverage to Codecov" step fails

**Symptom**: CI shows error in codecov upload step

**Solutions**:
1. Verify `CODECOV_TOKEN` secret is set correctly
2. Check token hasn't expired (no expiration for upload tokens)
3. Ensure `coverage.xml` file is generated before upload
4. Check codecov.io service status: https://status.codecov.io

### Issue: Coverage report shows 0% or incorrect data

**Symptom**: Codecov shows empty or wrong coverage

**Solutions**:
1. Verify pytest-cov is generating `coverage.xml`
2. Check file paths in coverage.xml match repository structure
3. Ensure `codecov.yml` ignore patterns aren't too broad
4. Look at CI logs for pytest execution errors

### Issue: Badge not updating

**Symptom**: README badge shows old percentage

**Solutions**:
1. Clear browser cache (badge is cached)
2. Add `?random=<timestamp>` to badge URL temporarily
3. Wait 5-10 minutes for CDN propagation
4. Check codecov dashboard has latest data

### Issue: PR comment not appearing

**Symptom**: Codecov bot doesn't comment on pull requests

**Solutions**:
1. Enable "PR Comments" in codecov settings
2. Ensure GitHub App has PR write permissions
3. Check codecov.yml `comment.behavior` setting
4. Verify base branch has coverage data for comparison

## Maintenance

### Weekly Tasks
- Review coverage reports on codecov.io
- Identify packages with declining coverage
- Prioritize test writing for critical gaps

### Monthly Tasks
- Update coverage targets in `codecov.yml` as needed
- Review and adjust ignore patterns
- Check for deprecated codecov features
- Update this guide with new findings

### Before Major Releases
- Ensure all core packages meet targets
- Review sunburst chart for uncovered modules
- Run full test suite locally: `make test-all`
- Generate local HTML report for deep dive

## References

- **Codecov Documentation**: https://docs.codecov.com
- **GitHub Actions Integration**: https://docs.codecov.com/docs/github-actions-integration
- **codecov.yml Reference**: https://docs.codecov.com/docs/codecov-yaml
- **Badge Customization**: https://docs.codecov.com/docs/status-badges

## Support

- **Codecov Issues**: https://github.com/codecov/codecov-action/issues
- **SAGE Issues**: https://github.com/intellistream/SAGE/issues
- **Slack**: #testing channel in intellistream workspace
