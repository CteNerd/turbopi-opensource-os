# Branch Protection Configuration

## Purpose

This document outlines the required branch protection rules for the repository to ensure safe, repeatable development practices.

## Required Configuration

Branch protection must be enabled for the `main` branch with the following settings:

### Core Requirements

1. **Require Pull Request Reviews Before Merging**
   - ✅ Enable "Require a pull request before merging"
   - Required number of approvals: **1**
   - ✅ Enable "Dismiss stale pull request approvals when new commits are pushed"

2. **Require Status Checks to Pass**
   - ✅ Enable "Require status checks to pass before merging"
   - ✅ Enable "Require branches to be up to date before merging"
   - Add all CI workflow checks as required status checks (when CI is configured)

3. **Require Conversation Resolution**
   - ✅ Enable "Require conversation resolution before merging"
   - Ensures all review comments are addressed

4. **Restrict Who Can Push**
   - ✅ Enable "Do not allow bypassing the above settings"
   - Ensures even administrators follow the PR process

5. **Additional Protections**
   - ✅ Enable "Require linear history" (optional but recommended)
   - Helps maintain a clean commit history

## How to Configure

### Via GitHub Web UI

1. Go to repository **Settings**
2. Navigate to **Branches** in the left sidebar
3. Under "Branch protection rules", click **Add rule**
4. In "Branch name pattern", enter: `main`
5. Configure the settings as outlined above
6. Click **Create** or **Save changes**

### Verification

After configuration, the following should be true:

- Direct pushes to `main` are blocked
- All changes must go through a Pull Request
- PRs require at least one approval
- All status checks must pass (when configured)
- Review comments must be resolved

## Rationale

These protections align with the project's philosophy:

> Safety > Features

By requiring PRs and reviews, we:
- Prevent accidental breaking changes
- Enable peer review and knowledge sharing
- Maintain audit trail of all changes
- Reduce security and quality risks

## Related Documents

- [CONTRIBUTING.md](../CONTRIBUTING.md) - Contribution guidelines
- [SECURITY.md](../SECURITY.md) - Security policy
- [CODEOWNERS](../CODEOWNERS) - Code ownership and review assignments
