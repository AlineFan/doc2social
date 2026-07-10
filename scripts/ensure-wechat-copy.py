#!/usr/bin/env python3
"""Ensure output HTML files include the WeChat rich-copy button.

Usage:
    python3 scripts/ensure-wechat-copy.py output
    python3 scripts/ensure-wechat-copy.py --check output

This intentionally only injects the copy UI. Use publish-to-wechat.sh or
inline-images.py when you also need local images converted to data URIs.
"""
import argparse
import os
import runpy
import sys


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INLINE = os.path.join(ROOT, "scripts", "inline-images.py")
COPY_ROOT_ID = "wechat-copy-root"
COPY_UI_MARKER = "wechat-rich-copy-ui"


def iter_html(paths):
    for path in paths:
        if os.path.isdir(path):
            for root, dirs, files in os.walk(path):
                dirs[:] = [d for d in dirs if not d.startswith(".")]
                for name in files:
                    if name.lower().endswith(".html"):
                        yield os.path.join(root, name)
        elif path.lower().endswith(".html"):
            yield path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="fail if any HTML is missing the copy UI")
    parser.add_argument("paths", nargs="+", help="HTML files or directories to scan")
    args = parser.parse_args()

    inject_copy_ui = runpy.run_path(INLINE)["inject_copy_ui"]
    changed = []
    missing = []
    scanned = 0

    for path in iter_html(args.paths):
        scanned += 1
        with open(path, encoding="utf-8") as f:
            html = f.read()
        has_root = COPY_ROOT_ID in html
        has_ui = COPY_UI_MARKER in html
        if has_root and has_ui:
            continue
        missing.append(path)
        if not args.check:
            new_html = inject_copy_ui(html)
            with open(path, "w", encoding="utf-8") as f:
                f.write(new_html)
            changed.append(path)

    if args.check and missing:
        print("Missing WeChat copy button:")
        for path in missing:
            print(f"  - {path}")
        return 1

    print(f"scanned={scanned} missing={len(missing)} changed={len(changed)}")
    for path in changed:
        print(f"  + {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
