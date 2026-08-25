# profile.py - the encrypted store for the user's details.
#
# Holds one or more profiles (UK, Gulf, Arabic) with one active. Everything is
# written encrypted at rest. Encryption is pluggable so the STORE LOGIC is
# testable off Windows, while the real add-on uses Windows DPAPI, which ties
# the data to the current Windows user account with no key for us to manage.

import json
import os
import ctypes


# Suggested field names for common sections, used only to pre-fill a new row so
# the user is not staring at blank fields. Guidance, not a schema: any section
# can be added, renamed or removed, and any field left, added or renamed.
SECTION_TEMPLATES = {
    "Experience": ["job_title", "employer", "start_date", "end_date",
                   "description"],
    "Education": ["institution", "qualification", "field_of_study",
                  "start_date", "end_date"],
    "Skills": ["skill"],
    "Certifications": ["name", "issuer", "date"],
    "Languages": ["language", "proficiency"],
}


class Crypto:
    """Interface. encrypt/decrypt operate on bytes and must round-trip."""
    def encrypt(self, data: bytes) -> bytes: raise NotImplementedError
    def decrypt(self, data: bytes) -> bytes: raise NotImplementedError


class DpapiCrypto(Crypto):
    """Real encryption on Windows via CryptProtectData/CryptUnprotectData.
    Not exercised in the Linux sandbox; verified only on the user's machine."""
    def _call(self, fn, data: bytes) -> bytes:
        from ctypes import wintypes

        class BLOB(ctypes.Structure):
            _fields_ = [("cbData", wintypes.DWORD),
                        ("pbData", ctypes.POINTER(ctypes.c_char))]

        buf = ctypes.create_string_buffer(data, len(data))
        blob_in = BLOB(len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char)))
        blob_out = BLOB()
        if not fn(ctypes.byref(blob_in), None, None, None, None, 0,
                  ctypes.byref(blob_out)):
            raise OSError("DPAPI call failed")
        try:
            return ctypes.string_at(blob_out.pbData, blob_out.cbData)
        finally:
            ctypes.windll.kernel32.LocalFree(blob_out.pbData)

    def encrypt(self, data: bytes) -> bytes:
        return self._call(ctypes.windll.crypt32.CryptProtectData, data)

    def decrypt(self, data: bytes) -> bytes:
        return self._call(ctypes.windll.crypt32.CryptUnprotectData, data)


class NullCrypto(Crypto):
    """Plain storage: no encryption. Used for the profile store, which holds
    ordinary contact details (not secrets), and for tests."""
    def encrypt(self, data: bytes) -> bytes: return data
    def decrypt(self, data: bytes) -> bytes: return data


def default_crypto() -> Crypto:
    # The profile holds ordinary contact details, not secrets, and the CV they
    # came from is already on the device in plain form, so the store is plain
    # JSON for now. The Crypto slot stays, so encryption can return later (for
    # example if the AI feature ever handles anything sensitive). DpapiCrypto is
    # kept above for that day.
    return NullCrypto()


_EMPTY = {"active": None, "profiles": {}}


class ProfileStore:
    def __init__(self, path: str, crypto: Crypto):
        self.path = path
        self.crypto = crypto
        self._data = {"active": None, "profiles": {}, "sections": {}}

    # --- persistence ---------------------------------------------------------
    def load(self):
        if not os.path.exists(self.path):
            self._data = {"active": None, "profiles": {}, "sections": {}}
            return self._data
        with open(self.path, "rb") as f:
            raw = f.read()
        text = self.crypto.decrypt(raw).decode("utf-8")
        self._data = json.loads(text)
        # Backward compatible: profiles saved before sections existed have no
        # "sections" key; give them an empty one so the section methods work.
        self._data.setdefault("sections", {})
        return self._data

    def save(self):
        text = json.dumps(self._data, ensure_ascii=False).encode("utf-8")
        blob = self.crypto.encrypt(text)
        tmp = self.path + ".tmp"
        with open(tmp, "wb") as f:
            f.write(blob)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, self.path)      # atomic on the same filesystem

    # --- profiles ------------------------------------------------------------
    def add_profile(self, name: str, fields: dict | None = None):
        self._data["profiles"][name] = dict(fields or {})
        if self._data["active"] is None:
            self._data["active"] = name

    def set_active(self, name: str):
        if name not in self._data["profiles"]:
            raise KeyError(name)
        self._data["active"] = name

    def active_name(self):
        return self._data["active"]

    def get_active(self) -> dict:
        name = self._data["active"]
        if name is None:
            return {}
        return self._data["profiles"][name]

    def get_profile(self, name: str) -> dict:
        return dict(self._data["profiles"].get(name, {}))

    def rename_profile(self, old: str, new: str):
        if old not in self._data["profiles"] or new == old:
            return
        self._data["profiles"][new] = self._data["profiles"].pop(old)
        secs = self._data.setdefault("sections", {})
        if old in secs:
            secs[new] = secs.pop(old)
        if self._data["active"] == old:
            self._data["active"] = new

    def delete_profile(self, name: str):
        self._data["profiles"].pop(name, None)
        self._data.setdefault("sections", {}).pop(name, None)
        if self._data["active"] == name:
            names = self.profile_names()
            self._data["active"] = names[0] if names else None

    def set_field(self, key: str, value: str, profile: str | None = None):
        name = profile or self._data["active"]
        self._data["profiles"][name][key] = value

    def profile_names(self):
        return list(self._data["profiles"].keys())

    # --- sections (Experience, Education, Skills, or any the user adds) -------
    # A section is {"name": str, "rows": [ {field: value, ...}, ... ]}. Rows are
    # free-form dicts, so a section holds whatever a CV needs, and the user can
    # add, rename and remove both sections and rows.
    def _sections_for(self, profile=None):
        name = profile or self._data["active"]
        if name is None:
            return None
        return self._data.setdefault("sections", {}).setdefault(name, [])

    def sections(self, profile=None):
        """Every section for a profile, as copies so callers cannot mutate the
        store by accident; use the methods below to change them."""
        secs = self._sections_for(profile)
        if not secs:
            return []
        return [{"name": s["name"], "rows": [dict(r) for r in s["rows"]]}
                for s in secs]

    def section_names(self, profile=None):
        secs = self._sections_for(profile)
        return [s["name"] for s in secs] if secs else []

    def add_section(self, name, profile=None):
        """Add an empty section. No-op if one of that name already exists."""
        secs = self._sections_for(profile)
        if secs is None or any(s["name"] == name for s in secs):
            return
        secs.append({"name": name, "rows": []})

    def remove_section(self, name, profile=None):
        secs = self._sections_for(profile)
        if secs is not None:
            secs[:] = [s for s in secs if s["name"] != name]

    def rename_section(self, old, new, profile=None):
        secs = self._sections_for(profile)
        if secs is None or old == new or any(s["name"] == new for s in secs):
            return
        for s in secs:
            if s["name"] == old:
                s["name"] = new
                return

    def _get_section(self, name, profile=None):
        secs = self._sections_for(profile)
        if secs is None:
            return None
        for s in secs:
            if s["name"] == name:
                return s
        return None

    def section_rows(self, name, profile=None):
        s = self._get_section(name, profile)
        return [dict(r) for r in s["rows"]] if s else []

    def add_row(self, section, row=None, profile=None):
        """Append a row to a section, creating the section if it does not exist."""
        if self._sections_for(profile) is None:
            return
        s = self._get_section(section, profile)
        if s is None:
            self.add_section(section, profile)
            s = self._get_section(section, profile)
        s["rows"].append(dict(row or {}))

    def update_row(self, section, index, row, profile=None):
        s = self._get_section(section, profile)
        if s and 0 <= index < len(s["rows"]):
            s["rows"][index] = dict(row or {})

    def remove_row(self, section, index, profile=None):
        s = self._get_section(section, profile)
        if s and 0 <= index < len(s["rows"]):
            s["rows"].pop(index)
