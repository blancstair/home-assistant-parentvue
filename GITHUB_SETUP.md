# Publishing this repository to GitHub

The files contain the placeholder:

`YOUR_GITHUB_USERNAME`

Run the included PowerShell helper from the repository root:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\scripts\set_github_owner.ps1" -GitHubUser "YOUR_ACTUAL_GITHUB_USERNAME"
```

Then initialize/publish the repository.

If GitHub CLI (`gh`) is installed:

```powershell
git init
git add .
git commit -m "Release v0.2.0"
git branch -M main

gh auth login
gh repo create home-assistant-parentvue --public --source=. --remote=origin --push
```

Set the repository description to something like:

> Home Assistant custom integration for Edupoint ParentVUE with multi-child Grade Book and school schedule support.

Recommended topics:

- `home-assistant`
- `hacs`
- `parentvue`
- `edupoint`
- `education`

Enable GitHub Issues.

## First release

After the repository is pushed:

```powershell
git tag v0.2.0
git push origin v0.2.0
```

You may create a GitHub Release from the tag in the GitHub UI.

HACS can also install from the default branch while the project is still under
development; published GitHub releases provide cleaner version selection.

## HACS

HACS integration repositories use the standard:

`custom_components/<domain>/`

layout. This repository follows that structure.

Before expecting HACS validation to pass, confirm that:

- the GitHub-owner placeholder has been replaced
- the repository is public
- Issues are enabled
- repository description is set
- repository topics are set
- README exists

The included validation workflow runs both HACS validation and Hassfest.
Brand/image checks are temporarily ignored while the project has no Home
Assistant Brands entry.
