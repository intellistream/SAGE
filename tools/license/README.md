# SAGE License Management Tools

This directory contains the industrial-grade license management system for SAGE.

## 🏗️ Architecture

```
tools/license/
├── shared/           # Common license functionality
│   ├── license_core.py    # Core license operations
│   ├── validation.py      # License validation logic
│   └── config.py         # Configuration constants
├── client/           # Customer-facing tools
│   └── license_client.py  # License installation/management
├── vendor/           # Internal vendor tools
│   └── license_vendor.py  # License generation/tracking
└── sage_license.py   # Unified entry point
```

## 🎯 Design Principles

### 1. **Separation of Concerns**
- **Client tools**: Customer license installation and status checking
- **Vendor tools**: Internal license generation and management
- **Shared components**: Common validation and core functionality

### 2. **Security by Design**
- License keys use cryptographic checksums
- Separate vendor/client key spaces
- No sensitive data in client tools

### 3. **Industrial Best Practices**
- Modular architecture for maintainability
- Clear separation between customer and vendor functionality
- Comprehensive logging and audit trails

## 🚀 Usage

### For Customers

```bash
# Install a license
python tools/license/sage_license.py install SAGE-COMM-2024-ABCD-EFGH-1234

# Check license status
python tools/license/sage_license.py status

# Remove license
python tools/license/sage_license.py remove
```

### For SAGE Team (Vendors)

```bash
# Generate a new license
python tools/license/sage_license.py generate "Company ABC" 365

# List all generated licenses
python tools/license/sage_license.py list

# Revoke a license
python tools/license/sage_license.py revoke SAGE-COMM-2024-ABCD-EFGH-1234
```

## 🔧 Integration with SAGE

The license system can be integrated into SAGE applications:

```python
from tools.license.shared.validation import LicenseValidator

validator = LicenseValidator()
if validator.has_valid_license():
    # Enable commercial features
    enable_enterprise_database()
else:
    print("Commercial license required for this feature")
```

## 📂 Migration from Legacy

The old `scripts/sage-license.py` has been refactored into this modular system:

| Legacy Function | New Location | Notes |
|----------------|--------------|-------|
| License installation | `client/license_client.py` | Customer-facing |
| License generation | `vendor/license_vendor.py` | Vendor-only |
| Validation logic | `shared/validation.py` | Reusable component |
| Configuration | `shared/config.py` | Centralized settings |

## ⚖️ Compliance

This architecture follows industry standards for:
- **Software licensing** (ISO/IEC 19770)
- **Security practices** (NIST guidelines)
- **Commercial software distribution** patterns

## 🔄 Backward Compatibility

A compatibility shim is maintained at `scripts/sage-license.py` for existing scripts.
