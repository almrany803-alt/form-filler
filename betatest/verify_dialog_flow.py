"""Check the store on disk after drive_dialog_flow.ps1, one PASS/FAIL per
behaviour. Config dir from JFF_CFG. Exit 1 on any failure."""
import os
import sys
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
except Exception:
    pass
sys.path.insert(0, os.path.join("addon", "globalPlugins", "jobFormFiller", "core"))
import profile  # noqa: E402

cfg = os.environ["JFF_CFG"]
store = profile.ProfileStore(os.path.join(cfg, "jobFormFiller", "profile.dat"),
                             profile.default_crypto())
store.load()
ok = True


def check(label, cond, detail=""):
    global ok
    print(("PASS  " if cond else "FAIL  ") + label + (("  " + detail) if detail else ""))
    ok = ok and bool(cond)


names = store.profile_names()
prof = store._data.get("profiles", {}).get("Mohammed", {})   # read the named profile directly
# A: details typed and saved
check("A personal details saved by keyboard",
      prof.get("given_name") == "Mohammed" and prof.get("family_name") == "Al Omrani"
      and prof.get("email") == "test@example.com" and prof.get("phone") == "07700 900000",
      "got %r" % {k: prof.get(k) for k in ("given_name", "family_name", "email", "phone")})
# B: cancel did not save
check("B cancel did not save", prof.get("given_name") == "Mohammed",
      "given_name=%r" % prof.get("given_name"))
# C: last section removed (seed had Education, Experience, Skills, Languages)
secs = store.section_names("Mohammed")
check("C last section removed", "Languages" not in secs, "sections now %r" % secs)
# D: first entry of first section edited
first = secs[0] if secs else None
rows = store.section_rows(first, "Mohammed") if first else []
first_key = profile.fields_for_type(store.section_type(first, "Mohammed"))[0] if first else ""
check("D entry 1 edited", bool(rows) and rows[0].get(first_key) == "Edited Qualification",
      "section %r field %r = %r" % (first, first_key, rows[0].get(first_key) if rows else None))
# E: profile created then deleted
check("E profile created then deleted", "Testprof" not in names and "Mohammed" in names,
      "profiles %r" % names)
print("profile store:", "OK" if ok else "PROBLEMS")
sys.exit(0 if ok else 1)
