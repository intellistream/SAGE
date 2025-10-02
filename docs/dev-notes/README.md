# Development Notes

This directory contains development notes, fix summaries, and implementation documentation for SAGE project.

## 📁 Directory Structure

```
dev-notes/
├── README.md              # This file
├── TEMPLATE.md            # Template for new dev notes
├── autostop/              # Autostop service related documentation
├── security/              # Security and configuration documentation
├── ci-cd/                 # CI/CD and build fixes
└── archived/              # Historical summaries and completed work
```

## 📝 Creating New Dev Notes

When creating a new development note, please:

1. **Use the template**: Copy `TEMPLATE.md` as a starting point
2. **Follow naming convention**: `[FEATURE_NAME]_[ISSUE_NUMBER].md` (e.g., `API_CACHE_880.md`)
3. **Choose the right category**: Place in the appropriate subdirectory
4. **Link to issues**: Reference the GitHub issue number in the document
5. **Keep it updated**: Update the status as work progresses

### Example
```bash
cp TEMPLATE.md autostop/NEW_FEATURE_123.md
# Edit the file with your content
```

## 📂 Categories

### 🔄 [autostop/](./autostop/)
Documentation related to autostop service implementation and fixes.

**Contents:**
- `AUTOSTOP_MODE_SUPPORT.md` - Autostop mode support documentation
- `AUTOSTOP_SERVICE_FIX_SUMMARY.md` - Summary of autostop service fixes
- `REMOTE_AUTOSTOP_IMPLEMENTATION.md` - Remote autostop implementation details
- `修复说明_autostop服务清理.md` - Autostop service cleanup (Chinese)
- `远程模式支持说明.md` - Remote mode support (Chinese)

### 🔒 [security/](./security/)
Security-related fixes, configuration, and best practices.

**Contents:**
- `api_key_security.md` - API key security configuration guide
- `CONFIG_CLEANUP_REPORT.md` - Configuration file security cleanup report
- `SECURITY_UPDATE_SUMMARY.md` - Security updates and improvements summary
- `TODO_SECURITY_CHECKLIST.md` - Security checklist and tasks

### 🔧 [ci-cd/](./ci-cd/)
CI/CD pipeline fixes, build issues, and deployment notes.

**Contents:**
- `FIX_LIBSTDCXX_CI_869.md` - libstdc++ CI issue #869 fix

### 📦 [archived/](./archived/)
Historical summaries and completed project documentation.

**Contents:**
- `COMPLETE_SUMMARY.md` - Complete project summary
- `ROOT_CLEANUP_SUMMARY.md` - Root directory cleanup summary

## 🎯 Purpose

These documents serve as:
- **Historical records** of feature implementations and bug fixes
- **Knowledge base** for development decisions and rationale
- **Troubleshooting guides** for technical challenges and solutions
- **Reference materials** for future development work

## 📚 Best Practices

1. **Be specific**: Include issue numbers, dates, and affected components
2. **Be complete**: Document the problem, solution, and testing
3. **Be clear**: Write for future developers who may not have context
4. **Link references**: Connect to related issues, PRs, and documentation
5. **Update status**: Keep the status field current as work progresses

## 🔗 Related Documentation

- Main documentation: [docs/](../)
- CI/CD documentation: [docs/ci-cd/](../ci-cd/)
- Security documentation: [docs/security/](../security/)
- Public documentation: [docs-public/](../../docs-public/)

---

**Note**: For current project documentation and user guides, see the main [docs/](../) directory.
