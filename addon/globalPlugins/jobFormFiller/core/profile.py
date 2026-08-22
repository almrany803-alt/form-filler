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
    """NOT SECURE. A no-op used only for tests and non-Windows development.
    The store must never ship with this on a real machine."""
    def encrypt(self, data: bytes) -> bytes: return data
    def decrypt(self, data: bytes) -> bytes: return data


def default_crypto() -> Crypto:
    """DPAPI on Windows; refuse to silently fall back to no encryption."""
    if os.name == "nt":
        return DpapiCrypto()
    raise RuntimeError("No secure crypto available on this platform; "
                       "inject a Crypto explicitly for development.")


_EMPTY = {"active": None, "profiles": {}}


class ProfileStore:
    def __init__(self, path: str, crypto: Crypto):
        self.path = path
        self.crypto = crypto
        self._data = dict(_EMPTY)

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

    def set_field(self, key: str, value: str, profile: str | None = None):
        name = profile or self._data["active"]
        self._data["profiles"][name][key] = value

    def profile_names(self):
        return list(self._data["profiles"].keys())
