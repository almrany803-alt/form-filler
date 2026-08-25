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

elif cmd == "seed_sections":
    os.makedirs(os.path.dirname(path), exist_ok=True)
    import cvparse  # noqa: E402  (core dir already on sys.path above)
    CV = """Mohammed Alomrani
mohammed@example.com
EDUCATION
Bachelor of Arts in Education, University of the West of England, Bristol (Sep 2023 to Jun 2026)
TEACHING AND VOLUNTEER EXPERIENCE
Sight Support West of England, Technology Support Volunteer (Mar 2024 to Jun 2026)
Taught visually impaired people to use technology.
Look UK, Peer Mentor (Sep 2023 to present)
Mentored young people.
SKILLS
Accessible Learning Design
LANGUAGES
Arabic: Native
English: Fluent
"""
    store.add_profile("Mohammed", cvparse.cv_to_fields(cvparse.parse_cv_text(CV)))
    store.set_active("Mohammed")
    secs = cvparse.parse_cv_sections(CV)
    n = 0
    for sname, rows in secs.items():
        for r in rows:
            store.add_row(sname, r, profile="Mohammed")
            n += 1
    store.save()
    print("seeded", n, "section entries across", store.section_names("Mohammed"))

elif cmd == "check_sections":
    store.load()
    names = store.section_names("Mohammed")
    exp = store.section_rows("Experience", "Mohammed")
    print("sections:", names, "| Experience entries:", len(exp))
    if "Awards" not in names or len(exp) != 1:
        print("MISMATCH: expected Awards present and Experience to have 1 entry")
        sys.exit(1)
    print("PASS crud store state")

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

elif cmd == "seed_english":
    os.makedirs(os.path.dirname(path), exist_ok=True)
    store.add_profile("English", {
        "given_name": "John", "family_name": "Smith",
        "email": "john@example.com"})
    store.set_active("English")
    store.save()
    print("seeded English")

elif cmd == "check_created":
    store.load()
    names = set(store.profile_names())
    teach = store.get_profile("Teaching")
    eng = store.get_profile("English")
    print("names:", names, "active:", store.active_name(),
          "Teaching.given:", teach.get("given_name"),
          "English.given:", eng.get("given_name"))
    ok = (names == {"English", "Teaching"}
          and teach.get("given_name") == "Sarah"
          and eng.get("given_name") == "John"
          and store.active_name() == "Teaching")
    print("PASS check_created" if ok else "FAIL check_created")
    sys.exit(0 if ok else 1)

elif cmd == "check_deleted":
    store.load()
    names = set(store.profile_names())
    print("names:", names, "active:", store.active_name())
    ok = (names == {"English"} and store.active_name() == "English"
          and store.get_profile("English").get("given_name") == "John")
    print("PASS check_deleted" if ok else "FAIL check_deleted")
    sys.exit(0 if ok else 1)

elif cmd == "check_import_menu":
    store.load()
    names = set(store.profile_names())
    p = store.get_active() or {}
    print("names:", names, "active:", store.active_name(), "profile:", p)
    ok = (p.get("given_name") == "Jane" and p.get("family_name") == "Doe"
          and p.get("email") == "jane.doe@example.co.uk"
          and store.active_name() is not None)
    print("PASS check_import_menu" if ok else "FAIL check_import_menu")
    sys.exit(0 if ok else 1)

elif cmd == "check_menu_new":
    store.load()
    names = set(store.profile_names())
    ok = ("Teaching" in names and store.active_name() == "Teaching"
          and "English" in names)
    print("names:", names, "active:", store.active_name())
    print("PASS check_menu_new" if ok else "FAIL check_menu_new")
    sys.exit(0 if ok else 1)

elif cmd == "check_menu_del":
    store.load()
    names = set(store.profile_names())
    ok = ("Teaching" not in names and "English" in names
          and store.active_name() == "English")
    print("names:", names, "active:", store.active_name())
    print("PASS check_menu_del" if ok else "FAIL check_menu_del")
    sys.exit(0 if ok else 1)
