# profile.py - the encrypted store for the user's details.
#
# Holds one or more profiles (UK, Gulf, Arabic) with one active. Everything is
# written encrypted at rest. Encryption is pluggable so the STORE LOGIC is
# testable off Windows, while the real add-on uses Windows DPAPI, which ties
# the data to the current Windows user account with no key for us to manage.

import json
import os
import ctypes


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
        self._data = {"active": None, "profiles": {}}

    # --- persistence ---------------------------------------------------------
    def load(self):
        if not os.path.exists(self.path):
            self._data = {"active": None, "profiles": {}}
            return self._data
        with open(self.path, "rb") as f:
            raw = f.read()
        text = self.crypto.decrypt(raw).decode("utf-8")
        self._data = json.loads(text)
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
        if self._data["active"] == old:
            self._data["active"] = new

    def delete_profile(self, name: str):
        self._data["profiles"].pop(name, None)
        if self._data["active"] == name:
            names = self.profile_names()
            self._data["active"] = names[0] if names else None

    def set_field(self, key: str, value: str, profile: str | None = None):
        name = profile or self._data["active"]
        self._data["profiles"][name][key] = value

    def profile_names(self):
        return list(self._data["profiles"].keys())
