"""Seed and check the encrypted profile for the dialog scenario stories.
Usage: python profile_tool.py seed
       python profile_tool.py check <cancel|edit|unicode>
Config dir from JFF_CFG."""
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
except Exception:
    pass

sys.path.insert(0, os.path.join("addon", "globalPlugins", "jobFormFiller", "core"))
import profile  # noqa: E402

cfg = os.environ["JFF_CFG"]
path = os.path.join(cfg, "jobFormFiller", "profile.dat")
store = profile.ProfileStore(path, profile.default_crypto())

cmd = sys.argv[1]

if cmd == "seed":
    os.makedirs(os.path.dirname(path), exist_ok=True)
    store.add_profile("default", {
        "given_name": "BASELINE", "family_name": "Base",
        "email": "base@example.com",
    })
    store.save()
    print("seeded BASELINE")

elif cmd == "check":
    mode = sys.argv[2]
    store.load()
    p = store.get_active() or {}
    print(f"mode {mode} -> profile {p}")
    EXPECT = {
        "cancel":  {"given_name": "BASELINE"},          # cancel must NOT change it
        "edit":    {"given_name": "Edited"},            # edit must persist
        "unicode": {"given_name": "محمد",               # Arabic must round-trip
                    "family_name": "O'Brien-李"},        # apostrophe + CJK too
        "cv_en":   {"given_name": "John", "family_name": "Smith",
                    "email": "john.smith@example.com"},
        "cv_ar":   {"given_name": "محمد", "family_name": "العمراني",
                    "email": "mohammed.alomrani@example.com"},
        "cv_docx": {"given_name": "Jane", "family_name": "Doe",
                    "email": "jane.doe@example.co.uk"},
        "cv_pdf":  {"given_name": "Michael", "family_name": "Brown",
                    "email": "michael.brown@example.com"},
    }
    exp = EXPECT[mode]
    bad = {k: (p.get(k), v) for k, v in exp.items() if p.get(k) != v}
    if bad:
        print("MISMATCH (field: got vs expected):", bad)
        sys.exit(1)
    print("PASS", mode)
