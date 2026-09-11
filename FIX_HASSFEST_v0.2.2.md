# Fix the current Hassfest errors

Apply these four file updates through the GitHub website.

1. Open `custom_components/parentvue/manifest.json`.
2. Click the pencil icon.
3. Replace the entire file with the v0.2.2 `manifest.json`.
4. Commit the change to `main`.

Repeat the same process for:

- `custom_components/parentvue/__init__.py`
- `custom_components/parentvue/strings.json`
- `custom_components/parentvue/translations/en.json`

Then update:

- `custom_components/parentvue/const.py`
- `custom_components/parentvue/config_flow.py`
- `CHANGELOG.md`

After the commits finish:

1. Open **Actions**.
2. Open **Validate**.
3. Click **Run workflow**.
4. Run it against `main`.
5. Confirm both **Hassfest** and **HACS** are green.

If another validation error appears, copy the annotation exactly before changing
anything else.
