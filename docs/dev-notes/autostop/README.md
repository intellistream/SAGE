# Autostop Service Documentation

This directory contains development notes and implementation documentation for the autostop service feature.

## Overview

The autostop service allows SAGE applications to automatically stop after completing their tasks, including proper cleanup of background services.

## Documents

### Implementation Documents

- **`AUTOSTOP_MODE_SUPPORT.md`** - Documentation for autostop mode support across different execution modes
- **`AUTOSTOP_SERVICE_FIX_SUMMARY.md`** - Summary of fixes for autostop service issues
- **`REMOTE_AUTOSTOP_IMPLEMENTATION.md`** - Implementation details for remote autostop functionality

### Chinese Documentation

- **`修复说明_autostop服务清理.md`** - Autostop service cleanup fix documentation (Chinese)
- **`远程模式支持说明.md`** - Remote mode support documentation (Chinese)

## Key Features

1. **Local Mode Support**: Autostop in local execution environment
2. **Remote Mode Support**: Autostop in distributed/remote environments
3. **Service Cleanup**: Proper cleanup of background services before stopping
4. **Job Manager Integration**: Integration with SAGE's job management system

## Related Components

- `dispatcher.py` - Main dispatcher with service cleanup logic
- `local_environment.py` - Local execution environment
- `remote_environment.py` - Remote execution environment
- `job_manager.py` - Job management service

## See Also

- [Main Dev Notes](../README.md)
- [CI/CD Documentation](../../ci-cd/)
