"""Seed an encrypted test profile for the beta-fill CI, using the add-on's own
store code and DPAPI (as the runner user, so NVDA can read it back).
Config dir comes from the JFF_CFG environment variable."""
import os
import sys

sys.path.insert(0, os.path.join("addon", "globalPlugins", "jobFormFiller", "core"))
import profile  # noqa: E402

cfg = os.environ["JFF_CFG"]
os.makedirs(os.path.join(cfg, "jobFormFiller"), exist_ok=True)
store = profile.ProfileStore(
    os.path.join(cfg, "jobFormFiller", "profile.dat"), profile.DpapiCrypto())
store.add_profile("default", {
    "given_name": "Mohammed", "family_name": "Al Omrani",
    "email": "test@example.com", "phone": "+44 7700 900000",
    "city": "Bristol", "country": "United Kingdom",
})
store.save()
print("seeded profile via DPAPI")
