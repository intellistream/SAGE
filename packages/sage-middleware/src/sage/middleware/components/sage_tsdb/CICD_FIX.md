# CI/CD Fix for sageTSDB Submodule

## Problem
CI/CD pipeline fails with error:
```
fatal: could not read Username for 'https://github.com': No such device or address
fatal: clone of 'https://github.com/intellistream/sageTSDB.git' into submodule path failed
```

## Root Cause
The `intellistream/sageTSDB` repository exists but is likely **private**. GitHub Actions' default `GITHUB_TOKEN` doesn't have permission to access it during submodule checkout.

## Solutions

### Solution 1: Make sageTSDB Public (Recommended for Open Source)

1. Go to https://github.com/intellistream/sageTSDB/settings
2. Scroll down to "Danger Zone"
3. Click "Change repository visibility"
4. Select "Public"
5. Confirm the change

**Pros:**
- Simple, no CI changes needed
- Aligns with open-source nature of SAGE

**Cons:**
- Code becomes publicly visible

### Solution 2: Use PAT (Personal Access Token) in CI

If sageTSDB must remain private:

1. **Create a Personal Access Token (PAT)**:
   - Go to https://github.com/settings/tokens
   - Click "Generate new token (classic)"
   - Select scopes: `repo` (full control)
   - Generate and copy the token

2. **Add PAT to SAGE Repository Secrets**:
   - Go to https://github.com/intellistream/SAGE/settings/secrets/actions
   - Click "New repository secret"
   - Name: `SUBMODULE_TOKEN`
   - Value: Paste the PAT
   - Click "Add secret"

3. **Update CI Workflow** (already done in this commit):
   ```yaml
   - name: Checkout Repository
     uses: actions/checkout@v4
     with:
       token: ${{ secrets.GITHUB_TOKEN }}
       submodules: 'recursive'  # ← This enables submodule checkout
   ```

   For private submodules, you may need:
   ```yaml
   - name: Checkout Repository
     uses: actions/checkout@v4
     with:
       token: ${{ secrets.SUBMODULE_TOKEN }}  # ← Use PAT instead
       submodules: 'recursive'
   ```

### Solution 3: Configure Submodule URLs in CI

Add a step to reconfigure submodule URLs with authentication:

```yaml
- name: Configure Submodule Access
  run: |
    git config --global url."https://${{ secrets.SUBMODULE_TOKEN }}@github.com/".insteadOf "https://github.com/"
    git submodule update --init --recursive
```

## Current CI Configuration

The CI workflow has been updated to:
1. Use `submodules: 'recursive'` in checkout action
2. Remove redundant "Initialize Submodules" step
3. Add "Verify Submodules" step to check sageTSDB and other submodules

## Testing

After applying the fix:
1. Push changes to the feature branch
2. Check GitHub Actions at: https://github.com/intellistream/SAGE/actions
3. Verify "Verify Submodules" step shows sageTSDB as ✅

## Verification Commands

Local verification:
```bash
# Check if sageTSDB is accessible
git ls-remote https://github.com/intellistream/sageTSDB.git

# Test submodule clone
cd /tmp
git clone --recurse-submodules https://github.com/intellistream/SAGE.git sage-test
cd sage-test/packages/sage-middleware/src/sage/middleware/components/sage_tsdb
ls -la sageTSDB/  # Should show C++ files
```

## Related Files Modified

1. `.github/workflows/ci.yml` - Added `submodules: 'recursive'` to checkout
2. `.gitmodules` - Already correctly configured
3. This documentation file

## Next Steps

1. **Choose a solution** (recommend Solution 1 for open source)
2. **Apply the fix**
3. **Push this commit** with the CI workflow changes
4. **Monitor the CI run** to verify the fix works

---

**Created**: 2025-10-20  
**Issue**: sageTSDB submodule clone failure in CI/CD  
**Status**: Pending repository visibility change or PAT configuration
