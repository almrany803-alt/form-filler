"""Seed a DUMMY profile for the live-application test, so no real personal data
is entered on real company forms (and the run never submits anyway)."""
import os, sys
sys.path.insert(0, os.path.join("addon", "globalPlugins", "jobFormFiller", "core"))
import profile  # noqa: E402

cfg = os.environ["JFF_CFG"]
os.makedirs(os.path.join(cfg, "jobFormFiller"), exist_ok=True)
store = profile.ProfileStore(
    os.path.join(cfg, "jobFormFiller", "profile.dat"), profile.default_crypto())
store.add_profile("default", {
    "given_name": "Alex", "family_name": "Sample",
    "email": "test@example.com", "phone": "+44 7700 900000",
    "city": "Bristol", "country": "United Kingdom",
    "work_authorisation": "Yes", "nationality": "British",
    "date_of_birth": "1990-05-20",
})
store.save()
print("seeded dummy live-test profile")
