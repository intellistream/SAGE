# API Reference

Complete API documentation for all SAGE packages.

## Package API Documentation

### Core Packages

- **[sage-common](common/index.md)** - Common utilities, data types, and base classes
- **[sage-platform](platform/index.md)** - Platform services (queue, storage, service base)
- **[sage-kernel](kernel/index.md)** - Execution engine and runtime
- **[sage-libs](libs/index.md)** - Algorithm libraries (agents, RAG, tools)
- **[sage-middleware](middleware/index.md)** - Domain-specific components

### Application Packages

See the [Guides](../guides/packages/) section for application-level documentation.

## API Documentation Generation

API documentation is automatically generated from Python docstrings using:

- **mkdocstrings** - Automatic API documentation from docstrings
- **Google style** - Docstring format

## Quick Links

- [Installation Guide](../getting-started/installation.md)
- [Quickstart](../getting-started/quickstart.md)
- [Package Architecture](../concepts/architecture/package-structure.md)

## Contributing

To improve API documentation:

1. Write clear docstrings in your code
2. Follow [Google docstring format](https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings)
3. Include examples in docstrings
4. Document all public APIs
