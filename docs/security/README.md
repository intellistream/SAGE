# Security Documentation

This directory contains documentation related to security practices and configurations for the SAGE project.

## Contents

- `API_KEY_SECURITY.md` - Guide for secure API key management and configuration

## Best Practices

1. Never commit API keys or other sensitive credentials to the repository
2. Use `.env` files for local development (ensure `.env` is in `.gitignore`)
3. Use GitHub Secrets for CI/CD environments
4. Follow the guidelines in `API_KEY_SECURITY.md` for proper configuration

## Related Documentation

- CI/CD configuration: [../ci-cd/](../ci-cd/)
- Development notes: [../dev-notes/](../dev-notes/)
