"""Seed a profile that also has a Work (Experience) section with three entries,
for the repeating-block fill test. Uses the add-on's own store + DPAPI.
"""
import os
import sys

sys.path.insert(0, os.path.join("addon", "globalPlugins", "jobFormFiller", "core"))
import profile  # noqa: E402

cfg = os.environ["JFF_CFG"]
os.makedirs(os.path.join(cfg, "jobFormFiller"), exist_ok=True)
store = profile.ProfileStore(
    os.path.join(cfg, "jobFormFiller", "profile.dat"), profile.default_crypto())
store.add_profile("default", {
    "given_name": "Mohammed", "family_name": "Al Omrani",
    "email": "test@example.com", "phone": "+44 7700 900000",
    "city": "Bristol", "country": "United Kingdom",
})
store.set_active("default")
store.add_section("Experience", "Work")
store.add_row("Experience", {"job_title": "Senior Engineer",
                             "employer": "Acme Corp",
                             "start_date": "2021", "end_date": "present"})
store.add_row("Experience", {"job_title": "Developer", "employer": "Globex",
                             "start_date": "2018", "end_date": "2021"})
store.add_row("Experience", {"job_title": "Intern", "employer": "Initech",
                             "start_date": "2017", "end_date": "2018"})
store.save()
print("seeded profile with a Work section of 3 entries")
