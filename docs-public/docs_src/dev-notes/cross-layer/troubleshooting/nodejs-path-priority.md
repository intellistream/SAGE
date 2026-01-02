# Node.js Path Priority Issue (nvm vs conda)

## Problem

When both nvm and conda Node.js are installed, the system may use the wrong version due to PATH
priority.

**Symptom**:

```bash
$ conda install -y nodejs=22 -c conda-forge  # Install Node.js 22
$ node --version                              # Still shows v18.x (from nvm)
v18.20.8
```

## Root Cause

nvm modifies PATH in `~/.bashrc` or `~/.zshrc`, often placing its binaries **before** conda:

```bash
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"  # This prepends nvm to PATH
```

This causes:

```
PATH = /home/user/.nvm/versions/node/v18.20.8/bin:...:/home/user/miniconda3/envs/sage/bin
       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
       nvm (priority)                           conda (ignored)
```

## Solutions

### Solution 1: Remove nvm, use conda exclusively (Recommended ✅)

**Best long-term solution**: Since you're already using conda for Python, unify Node.js management
with conda.

```bash
# 1. Backup .bashrc
cp ~/.bashrc ~/.bashrc.backup.before_nvm_removal

# 2. Remove nvm initialization from .bashrc
sed -i '/export NVM_DIR=/d' ~/.bashrc
sed -i '/\[ -s "$NVM_DIR\/nvm.sh" \]/d' ~/.bashrc
sed -i '/\[ -s "$NVM_DIR\/bash_completion" \]/d' ~/.bashrc

# 3. Reload config
source ~/.bashrc

# 4. Verify Node.js version
which node  # Should show conda path
node --version  # Should show v22.x

# 5. (Optional) Remove nvm directory to free disk space
rm -rf ~/.nvm  # Frees ~240MB
```

**Pros**:

- ✅ Permanently solves PATH conflicts
- ✅ Unified environment management (Python + Node.js in conda)
- ✅ No additional shell configuration needed
- ✅ Reduces disk usage (~240MB)

**Cons**:

- ❌ Less flexible if you need to frequently switch Node.js versions

### Solution 2: Temporarily fix PATH (Quick workaround)

**Temporarily** (current terminal session):

```bash
export PATH="/home/shuhao/miniconda3/envs/sage/bin:$PATH"
node --version  # Now shows v22.x
```

**Permanently** (modify shell config):

Edit `~/.bashrc` or `~/.zshrc`, move conda initialization **after** nvm:

```bash
# BAD: nvm after conda (nvm wins)
# >>> conda initialize >>>
# ...conda init code...
# >>> conda initialize <<<
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"

# GOOD: conda after nvm (conda wins when activated)
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
# >>> conda initialize >>>
# ...conda init code...
# >>> conda initialize <<<
```

Then reload:

```bash
source ~/.bashrc  # or ~/.zshrc
conda activate sage
node --version  # Should show v22.x
```

### Solution 2: Use nvm Node.js (Alternative)

If you prefer nvm:

```bash
nvm install 22
nvm use 22
nvm alias default 22
```

### Solution 3: Uninstall One Version (Clean)

**Remove nvm** (if using conda):

```bash
rm -rf ~/.nvm
# Remove nvm lines from ~/.bashrc or ~/.zshrc
```

**Remove conda Node.js** (if using nvm):

```bash
conda remove nodejs
```

## Verification

After applying a solution:

```bash
which node       # Should point to desired Node.js
node --version   # Should show v22.x (for Vite 7.x)
npm --version    # Should match Node.js version
```

## SAGE Requirements

- **Minimum**: Node.js 20.19.0 (for Vite 7.x)
- **Recommended**: Node.js 22.x (latest LTS)
- Install via conda: `conda install -y nodejs=22 -c conda-forge`

## See Also

- [SAGE Studio README](../../l6-studio/README.md)
- [Vite 7.x Migration Guide](https://vite.dev/guide/migration.html)
