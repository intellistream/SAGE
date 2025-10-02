# Dev Notes Quick Start Guide

## 🚀 Creating a New Dev Note

### Step 1: Choose the Category

Determine which category your dev note belongs to:
- **autostop/**: Autostop service features and fixes
- **security/**: Security improvements, API keys, configuration
- **ci-cd/**: CI/CD pipeline, build issues, deployment
- **archived/**: Historical summaries (usually not for new notes)

### Step 2: Copy the Template

```bash
cd /home/shuhao/SAGE/docs/dev-notes
cp TEMPLATE.md <category>/<YOUR_FEATURE>_<ISSUE_NUMBER>.md
```

Example:
```bash
cp TEMPLATE.md autostop/NEW_AUTOSTOP_FEATURE_880.md
```

### Step 3: Fill in the Template

Edit your new file and fill in all sections:
- Update the title with your feature/fix name and issue number
- Fill in date, author, type, and status
- Complete all relevant sections
- Remove sections that don't apply (but keep the main structure)

### Step 4: Update as You Progress

Keep the document updated:
- Mark objectives as completed with `[x]`
- Update the status field
- Add test results
- Document any issues or changes

## 📝 Naming Convention

Use this format: `<FEATURE_NAME>_<ISSUE_NUMBER>.md`

Examples:
- ✅ `API_CACHE_IMPLEMENTATION_880.md`
- ✅ `FIX_MEMORY_LEAK_901.md`
- ✅ `DOCKER_SUPPORT_850.md`
- ❌ `fix.md` (too vague)
- ❌ `new-feature.md` (no issue number)

## 🏷️ Document Types

Choose the appropriate type for your document:

- **Feature Implementation**: New features or capabilities
- **Bug Fix**: Fixing existing issues
- **Refactoring**: Code restructuring without changing behavior
- **Documentation**: Documentation improvements
- **Security Fix**: Security-related fixes or improvements
- **Performance**: Performance optimizations

## 📊 Status Values

Use these standard status values:

- **In Progress**: Active development
- **Completed**: Work finished, tested, and merged
- **Archived**: Historical reference, no longer active
- **Blocked**: Waiting on dependencies
- **On Hold**: Paused for later

## ✅ Checklist Before Finalizing

Before marking your dev note as "Completed":

- [ ] All objectives are checked off
- [ ] Implementation details are documented
- [ ] Test results are included
- [ ] Related issues/PRs are linked
- [ ] Code is merged to main branch
- [ ] Status is updated to "Completed"

## 🔗 Useful Commands

```bash
# View the template
cat docs/dev-notes/TEMPLATE.md

# Create a new dev note
cp docs/dev-notes/TEMPLATE.md docs/dev-notes/<category>/<NAME>_<NUM>.md

# List all dev notes
find docs/dev-notes -name "*.md" -type f | sort

# Search for a specific topic
grep -r "keyword" docs/dev-notes/
```

## 💡 Tips

1. **Be specific**: Include issue numbers and dates
2. **Link everything**: Connect to GitHub issues, PRs, and related docs
3. **Update regularly**: Keep the status current as you work
4. **Include code**: Add relevant code snippets for clarity
5. **Think future**: Write for developers who will read this later

## 📚 Examples

Good examples to reference:
- `autostop/AUTOSTOP_MODE_SUPPORT.md` - Comprehensive feature implementation
- `security/api_key_security.md` - Configuration guide with examples
- `ci-cd/FIX_LIBSTDCXX_CI_869.md` - Bug fix documentation

---

**Need help?** Check the [main README](README.md) or ask the team!
