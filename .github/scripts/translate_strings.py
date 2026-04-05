#!/usr/bin/env python3
"""Translate missing strings from en.json into all other language files."""

import json
from pathlib import Path

from deep_translator import GoogleTranslator

TRANSLATIONS_DIR = Path("custom_components/myengie/translations")
SOURCE_LANG = "en"
CONTEXT_FILE = TRANSLATIONS_DIR / "en.context.json"

LANG_MAP = {
    "ro": "ro",
    "de": "de",
    "fr": "fr",
    "es": "es",
    "nl": "nl",
    "hu": "hu",
    "pl": "pl",
    "cs": "cs",
    "sk": "sk",
    "bg": "bg",
    "it": "it",
    "pt": "pt",
    "sv": "sv",
    "da": "da",
    "fi": "fi",
    "nb": "no",
    "lt": "lt",
    "lv": "lv",
    "et": "et",
    "sl": "sl",
    "hr": "hr",
    "uk": "uk",
    "ru": "ru",
    "tr": "tr",
    "zh-Hans": "zh-CN",
    "zh-Hant": "zh-TW",
    "ja": "ja",
    "ko": "ko",
}


def flatten(d: dict, prefix: str = "") -> dict:
    """Flatten nested dict to dotted-key -> value."""
    out = {}
    for k, v in d.items():
        key = f"{prefix}.{k}" if prefix else k
        if isinstance(v, dict):
            out.update(flatten(v, key))
        else:
            out[key] = v
    return out


def set_leaf(d: dict, dotted_key: str, value: str) -> None:
    """Set a value in a nested dict using a dotted key path."""
    keys = dotted_key.split(".")
    for key in keys[:-1]:
        d = d.setdefault(key, {})
    d[keys[-1]] = value


def translate_missing(source_flat: dict, target: dict, lang_code: str, context: dict) -> tuple[dict, int]:
    """Find missing keys, translate them, and inject into target."""
    target_flat = flatten(target)
    missing = {k: v for k, v in source_flat.items() if k not in target_flat}
    if not missing:
        return target, 0

    translator = GoogleTranslator(source=SOURCE_LANG, target=lang_code)
    count = 0
    for key, text in missing.items():
        try:
            hint = context.get(key)
            if hint:
                # Prepend context on its own line so Google Translate uses it
                # as guidance, then take everything after the first newline.
                combined = f"[{hint}]\n{text}"
                translated_combined = translator.translate(combined)
                parts = translated_combined.split("\n", 1)
                translated = parts[1].strip() if len(parts) > 1 else translated_combined
            else:
                translated = translator.translate(text)
            set_leaf(target, key, translated)
            print(f"  [{lang_code}] {key}: '{text}' -> '{translated}'")
            count += 1
        except Exception as exc:
            print(f"  [{lang_code}] FAILED {key}: {exc}")

    return target, count


def check_context_coverage(source_flat: dict, context: dict) -> None:
    """Warn about keys in en.json that have no entry in en.context.json."""
    missing = [k for k in source_flat if k not in context]
    if missing:
        print("⚠️  Missing context hints (translations will be less accurate):")
        for key in missing:
            print(f"   {key}")


def main() -> None:
    source_file = TRANSLATIONS_DIR / f"{SOURCE_LANG}.json"
    with open(source_file, encoding="utf-8") as f:
        source = json.load(f)
    source_flat = flatten(source)

    context: dict = {}
    if CONTEXT_FILE.exists():
        with open(CONTEXT_FILE, encoding="utf-8") as f:
            context = json.load(f)

    check_context_coverage(source_flat, context)

    total_changed = 0

    for lang_file in sorted(TRANSLATIONS_DIR.glob("*.json")):
        lang_stem = lang_file.stem
        if lang_stem in (SOURCE_LANG, "en.context"):
            continue

        lang_code = LANG_MAP.get(lang_stem, lang_stem)

        with open(lang_file, encoding="utf-8") as f:
            target = json.load(f)

        target, count = translate_missing(source_flat, target, lang_code, context)

        if count > 0:
            with open(lang_file, "w", encoding="utf-8") as f:
                json.dump(target, f, ensure_ascii=False, indent=2)
                f.write("\n")
            print(f"✅ {lang_file.name}: {count} string(s) translated")
            total_changed += count
        else:
            print(f"⏭️  {lang_file.name}: no new strings")

    if total_changed == 0:
        print("Nothing to translate.")
    else:
        print(f"\nDone -- {total_changed} total string(s) translated across all languages.")

    # Exit with code 1 if nothing changed so CI can detect no-op runs
    raise SystemExit(0 if total_changed > 0 else 2)


if __name__ == "__main__":
    main()
