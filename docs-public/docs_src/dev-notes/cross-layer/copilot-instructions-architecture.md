# Copilot Instructions Architecture

## Overview

This document explains the architecture and rationale behind SAGE's Copilot instruction files.

## Architecture

### File Structure

```
.github/
├── copilot-instructions.md         # Main instructions (✅ COMMITTED, 1149 lines)
├── sage.chatmode.md.example        # Chat mode template (✅ COMMITTED, ~200 lines)
└── chatmodes/
    └── sage.chatmode.md            # User-local config (❌ GITIGNORED)

packages/.../submodule/.github/     # Submodule-specific instructions
├── sageFlow/.github/copilot-instructions.md    # C++ stream processing
├── sageTSDB/.github/copilot-instructions.md    # C++ time-series DB
└── ...
```

### Single Source of Truth

**`.github/copilot-instructions.md`** (1149 lines) - Main authoritative document

- Complete SAGE project rules and guidelines
- Architecture constraints (L1-L6 layers, no upward dependencies)
- Critical principles (Control Plane only, no fallback logic, readme-first)
- Installation procedures, testing commands, common issues
- Dependency management, port configuration, API patterns
- Updated when project architecture or policies change

**Why this is the canonical source:**

- Reduces maintenance burden (update one file)
- Prevents documentation drift between multiple instruction files
- Single place to check for up-to-date project rules
- Used by GitHub Copilot in all contexts (inline, chat, PR reviews)

### Quick Reference Template

**`.github/sage.chatmode.md.example`** (~200 lines) - User-local chat mode template

- Condensed quick reference for common operations
- Links back to main instructions for detailed information
- Committed as example/template
- Users copy to `.github/chatmodes/sage.chatmode.md` for local use

**Why use a template instead of committing the chat mode:**

- VS Code Copilot Chat modes are **user-specific configurations**
- Different team members may want different verbosity/style preferences
- Should not be forced via version control
- Allows customization while maintaining consistency

**What's included in quick reference:**

- 🎯 Core principles (Control Plane, no fallbacks, readme-first)
- 🏗️ Architecture summary (L1-L6 layers)
- 📦 Dependency management essentials
- 🚀 Quick start commands
- 🔧 Common commands table
- 🐛 Common issues table
- 📚 Links to full documentation

### User-Local Chat Mode

**`.github/chatmodes/sage.chatmode.md`** (gitignored) - Personal configuration

- Created by copying `.github/sage.chatmode.md.example`
- User can customize verbosity, add personal notes, adjust formatting
- NOT committed to repository (`.github/chatmodes/` in `.gitignore`)
- Each team member maintains their own

**How to set up:**

```bash
# Copy template to create local chat mode
cp .github/sage.chatmode.md.example .github/chatmodes/sage.chatmode.md

# (Optional) Customize for your preferences
vim .github/chatmodes/sage.chatmode.md
```

### Submodule Instructions

**`packages/.../submodule/.github/copilot-instructions.md`** - Independent submodule rules

- C++ submodules (sageFlow, sageTSDB, neuromem) have unique build/test requirements
- Separate Git repositories need their own instructions
- Focus on submodule-specific:
  - C++ build system (CMake, pybind11)
  - Testing commands specific to submodule
  - Directory structure
  - Integration with main SAGE project

**Examples:**

- `sageFlow/.github/copilot-instructions.md` - Stream processing engine (C++20)
- `sageTSDB/.github/copilot-instructions.md` - Time-series database (C++17)
- `neuromem/.github/copilot-instructions.md` - Memory system (Python + C++)

**Why submodules have separate instructions:**

- Independent Git repositories with their own version control
- Different technology stacks (C++ vs Python)
- Self-contained build and test procedures
- Can be used independently from main SAGE project
- Keeps submodule documentation self-contained

## Design Principles

### 1. DRY (Don't Repeat Yourself)

- **Problem:** Previous architecture had 626-line chatmode file duplicating main instructions
- **Solution:** 200-line quick reference that links to main instructions
- **Benefit:** Update once, apply everywhere

### 2. User Autonomy

- **Problem:** Forcing chat mode settings via version control
- **Solution:** Provide template, let users customize locally
- **Benefit:** Each team member can adjust to their preferences

### 3. Single Source of Truth

- **Problem:** Multiple instruction files can drift out of sync
- **Solution:** One authoritative document (copilot-instructions.md)
- **Benefit:** Always know where to find/update project rules

### 4. Submodule Independence

- **Problem:** C++ submodules have unique requirements
- **Solution:** Separate instructions in submodule repos
- **Benefit:** Submodules remain self-contained and portable

## Update Workflow

### When to update main instructions

- Architecture changes (new layers, package reorganization)
- New critical rules (control plane policies, security requirements)
- Installation procedure changes
- Port/configuration changes
- Common issues/solutions updates

### When to update quick reference template

- Only when **frequently-used quick reference information** changes
- Links to main docs remain valid (no need to update)
- Example: New common command, critical principle added

### When to update submodule instructions

- Submodule-specific build changes
- New testing procedures
- Integration points with main SAGE project change

## History

| Date       | Change                               | Rationale                                                      |
| ---------- | ------------------------------------ | -------------------------------------------------------------- |
| 2025-12-28 | Created chatmode example template    | Addressed "为啥我们需要几个不同的copilot instructions" concern |
| 2025-12-28 | Made `.github/chatmodes/` gitignored | User-local configurations should not be committed              |
| 2025-12-28 | Condensed chatmode to ~200 lines     | Reduced from 626 lines, removed redundancy                     |

## FAQ

### Q: Why not just use `.github/copilot-instructions.md` for chat mode?

**A:** VS Code Copilot Chat can read from multiple sources:

- Inline Copilot: Uses `.github/copilot-instructions.md`
- Chat mode: Can use custom `.github/chatmodes/*.chatmode.md` files
- Chat modes allow **user-specific customizations** (verbosity, tone, additional context)

The quick reference template optimizes for chat interactions (shorter, more focused) while linking
to complete documentation when needed.

### Q: What if I want to add my own notes to chat mode?

**A:** That's exactly why chat modes are user-local:

1. Copy template: `cp .github/sage.chatmode.md.example .github/chatmodes/sage.chatmode.md`
1. Add your notes/reminders to the local file
1. Changes stay on your machine (gitignored)

### Q: How do I know if my local chat mode is outdated?

**A:** The template links to `.github/copilot-instructions.md` for all details. As long as the main
instructions are up-to-date, your chat mode will reference correct information.

If the quick reference template is updated, you'll see changes in:

```bash
git diff .github/sage.chatmode.md.example
```

You can choose to merge those changes into your local chat mode or keep your customizations.

### Q: Can I share my chat mode customizations?

**A:** Yes, through:

1. **Internal team wiki** - Share tips on useful customizations
1. **Pull request to template** - If your changes benefit everyone, propose updating the example
1. **Personal gists** - Share your customized version externally

But don't commit to main repo (defeats the purpose of user-local configs).

## Related Documentation

- [Main Copilot Instructions](../../.github/copilot-instructions.md)
- [Chat Mode Template](../../.github/sage.chatmode.md.example)
- [Documentation Policy](documentation-policy.md) (if exists)

## References

- [VS Code Copilot Chat Documentation](https://code.visualstudio.com/docs/copilot/copilot-chat)
- [GitHub Copilot Instructions](https://docs.github.com/en/copilot/customizing-copilot/adding-custom-instructions-for-github-copilot)
