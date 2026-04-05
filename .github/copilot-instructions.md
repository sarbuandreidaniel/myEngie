# Copilot Instructions

## API Integration Testing

Any new API endpoint added to `custom_components/myengie/api.py` **must** be tested using `debug_auth.py` before being considered complete.

### Steps
1. Add the method to `MyEngieAPI` in `api.py`
2. Add a corresponding test block in `debug_auth.py` following the existing numbered pattern (e.g. `# 13. get_new_endpoint`)
3. Run the script: `/Users/andreisarbu/Code/ha-myEngie/.venv/bin/python debug_auth.py`
4. Confirm the endpoint returns `✅` and inspect the response structure
5. Use the real response structure to implement sensor parsing in `sensor.py`

### Credentials
Stored in `.env` (git-ignored). The script loads them automatically via `python-dotenv`.

---

## Translations

Whenever a string is added or updated in `custom_components/myengie/translations/en.json`, **immediately translate the same key into every other language file** found in the `custom_components/myengie/translations/` directory (currently `ro.json`).

- Keep all translation files in sync with `en.json` — no key present in `en.json` should be missing from any other language file.
- Use natural, idiomatic phrasing for each language rather than a word-for-word literal translation.
- If a new language file is added to the folder in the future, apply the same rule to it automatically.
