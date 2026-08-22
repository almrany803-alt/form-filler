"""Verify what the keyboard-driven dialog saved. Reads the encrypted profile
back (DPAPI, as the runner user) and asserts it holds the typed values."""
import os
import sys

sys.path.insert(0, os.path.join("addon", "globalPlugins", "jobFormFiller", "core"))
import profile  # noqa: E402

cfg = os.environ["JFF_CFG"]
store = profile.ProfileStore(
    os.path.join(cfg, "jobFormFiller", "profile.dat"), profile.default_crypto())
store.load()
p = store.get_active() or {}
print("profile loaded from disk:", p)

expect = {
    "given_name": "Mohammed",
    "family_name": "Al Omrani",
    "email": "test@example.com",
    "phone": "07700 900000",
    "city": "Bristol",
    "country": "United Kingdom",
}
bad = {k: (p.get(k), v) for k, v in expect.items() if p.get(k) != v}
if bad:
    print("MISMATCH (field: got vs expected):", bad)
    sys.exit(1)
print("PASS: the dialog, driven only by keyboard, saved every field correctly.")
