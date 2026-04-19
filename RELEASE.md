# Release Process for TurboPi OpenSource OS

This document describes the **step-by-step process** for cutting a new release, including version bump, pull request, tagging, and triggering the release pipeline.

---

## 1. Create a Release Branch

```
git checkout -b release/vX.Y.Z
```

## 2. Bump the Version
- Update all version strings (e.g., `VERSION`, `pyproject.toml`, or any hardcoded version numbers) to the new version (X.Y.Z).

## 3. Commit the Version Bump
```
git add .
git commit -m "(release) Bump version to X.Y.Z"
```

## 4. Push the Release Branch
```
git push origin release/vX.Y.Z
```

## 5. Open a Pull Request
- Open a PR from `release/vX.Y.Z` to `main`.
- Title: `(release) Bump version to X.Y.Z`
- Description: List any key changes or release notes.

## 6. Tag the Release (after merge)
- After the PR is merged to `main`, create a tag:
```
git checkout main
git pull origin main
git tag vX.Y.Z
git push origin vX.Y.Z
```

## 7. CI/CD Release Pipeline
- The release workflow should trigger automatically on tag push.
- Monitor GitHub Actions for completion.

## 8. Verify Release
- Confirm the new release artifact is available and deployed.
- Test the deployment as needed.

---

**Tip:** If your CI/CD requires a tag on the PR branch before merge, create the tag on the branch and push it before merging.

---

For more details, see `docs/updater/PROTOCOL.md` and `docs/updater/RELEASE_INSTALL_LAYOUT.md`.
