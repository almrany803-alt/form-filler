"""Seed a profile with Work and Education sections for the LIVE repeating test,
so whichever repeating section a real form has can be filled."""
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
for r in [{"job_title": "Senior Engineer", "employer": "Acme Corp",
           "start_date": "2021", "end_date": "present"},
          {"job_title": "Developer", "employer": "Globex",
           "start_date": "2018", "end_date": "2021"}]:
    store.add_row("Experience", r)
store.add_section("Education", "Education")
for r in [{"institution": "University of Bristol", "qualification": "BSc",
           "field_of_study": "Computer Science",
           "start_date": "2014", "end_date": "2017"},
          {"institution": "City College", "qualification": "Diploma",
           "field_of_study": "IT", "start_date": "2012", "end_date": "2014"}]:
    store.add_row("Education", r)
store.save()
print("seeded Work (2) + Education (2)")
