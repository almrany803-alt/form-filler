#!/usr/bin/env python3
"""Build the installable .nvda-addon from buildVars.py and the addon/ folder.

Usage:  python build.py
Output: jobFormFiller-<version>.nvda-addon in the current directory.

This is the simple packager. When we prepare a store submission we can move to
the official NVDA add-on template + SCons build, which also handles docs and
translation compilation; for now this produces a valid, installable add-on.
"""
import hashlib
import os
import shutil
import zipfile

import buildVars

ai = buildVars.addon_info
OUT = f'{ai["addon_name"]}-{ai["addon_version"]}.nvda-addon'
STAGE = ".build_stage"


def manifest():
    return (
        f'name = {ai["addon_name"]}\n'
        f'summary = "{ai["addon_summary"]}"\n'
        f'version = {ai["addon_version"]}\n'
        f'author = "{ai["addon_author"]}"\n'
        f'description = """{ai["addon_description"]}"""\n'
        f'minimumNVDAVersion = {ai["addon_minimumNVDAVersion"]}\n'
        f'lastTestedNVDAVersion = {ai["addon_lastTestedNVDAVersion"]}\n'
        f'license = "{ai["addon_license"]}"\n'
    )


def main():
    shutil.rmtree(STAGE, ignore_errors=True)
    os.makedirs(STAGE)
    with open(os.path.join(STAGE, "manifest.ini"), "w", encoding="utf-8") as f:
        f.write(manifest())

    for root, dirs, files in os.walk("addon"):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for name in files:
            if name.endswith(".pyc"):
                continue
            rel = os.path.relpath(os.path.join(root, name), "addon")
            dst = os.path.join(STAGE, rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(os.path.join(root, name), dst)

    if os.path.exists(OUT):
        os.remove(OUT)
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
        for root, _dirs, files in os.walk(STAGE):
            for name in files:
                fp = os.path.join(root, name)
                z.write(fp, os.path.relpath(fp, STAGE))
    shutil.rmtree(STAGE, ignore_errors=True)

    sha = hashlib.sha256(open(OUT, "rb").read()).hexdigest()
    print(f"Built {OUT} ({os.path.getsize(OUT)} bytes)")
    print(f"SHA256: {sha}")   # this is what the Add-on Store submission asks for


if __name__ == "__main__":
    main()
