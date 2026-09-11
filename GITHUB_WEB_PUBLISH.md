# Publish ParentVUE to GitHub

Publish this release directly through the GitHub website.

## Create the repository

1. Sign in to GitHub as **blancstair**.
2. Click **+ → New repository**.
3. Name it **home-assistant-parentvue**.
4. Set the description to:
   **Home Assistant custom integration for Edupoint ParentVUE**
5. Set visibility to **Public**.
6. Leave **README**, **.gitignore**, and **License** unchecked.
7. Click **Create repository**.

## Upload the files

1. Extract `home-assistant-parentvue_github_v0.2.1.zip`.
2. Open the new empty repository.
3. Click **uploading an existing file**.
4. Drag all extracted files and folders into the upload area.
5. Confirm the repository contains:
   - `.github`
   - `custom_components`
   - `dashboard`
   - `docs`
   - `.gitignore`
   - `CHANGELOG.md`
   - `CONTRIBUTING.md`
   - `hacs.json`
   - `LICENSE`
   - `README.md`
   - `RESEARCH_NOTES.md`
   - `SECURITY.md`
6. Use commit message:
   **Release v0.2.1**
7. Commit directly to `main`.

## Set repository details

1. Open the repository main page.
2. Set the description to:
   **Home Assistant custom integration for Edupoint ParentVUE**
3. Add these topics:
   - `home-assistant`
   - `hacs`
   - `parentvue`
   - `edupoint`
   - `education`
4. Keep **Issues** enabled.

## Check validation

1. Open the **Actions** tab.
2. Open the latest **Validate** workflow.
3. Confirm both checks pass:
   - **Hassfest**
   - **HACS**

If either check fails, copy the failed step output and use that to correct the repository before creating a release.

## Install from HACS

1. Open HACS in Home Assistant.
2. Open **Custom repositories**.
3. Enter:
   `https://github.com/blancstair/home-assistant-parentvue`
4. Select **Integration**.
5. Add the repository.
6. Install **ParentVUE**.
7. Restart Home Assistant.
8. Open **Settings → Devices & services → Add integration**.
9. Search for **ParentVUE**.

## Add the ParentVUE dashboard

1. Open **Settings → Dashboards**.
2. Create a dashboard named **ParentVUE**.
3. Open it and choose **Edit dashboard**.
4. Add a card.
5. Select **ParentVUE Dashboard**.
6. Save.

The bundled card automatically discovers ParentVUE devices and entities.

## Create the GitHub release

After v0.2.1 works correctly in Home Assistant:

1. Open the repository on GitHub.
2. Click **Releases**.
3. Click **Draft a new release**.
4. Click **Choose a tag**.
5. Enter **v0.2.1** and create the tag on `main`.
6. Release title: **ParentVUE v0.2.1**
7. Copy the v0.2.1 changelog section into the release notes.
8. Publish the release.

## Never upload

Do not upload any of these to GitHub:

- ParentVUE passwords
- cookies or authentication tokens
- HAR captures
- raw authenticated HTML/XML/JSON
- student IDs
- report cards
- messages
- unreviewed diagnostic files
