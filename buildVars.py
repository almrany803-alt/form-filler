# buildVars.py - manifest source for the add-on build (SCons generates
# manifest.ini from this). Compatibility range must be kept honest and tested
# against each January NVDA release.

addon_info = {
    "addon_name": "jobFormFiller",
    "addon_summary": "Job Form Filler",
    "addon_description": (
        "Fills job application forms from your saved details, in many "
        "languages, with spoken and braille review. Identify-and-fill by "
        "default; you stay in control and submit yourself."
    ),
    "addon_version": "0.9.40",
    "addon_author": "Mohammed <email@example.com>",
    "addon_url": "",
    "addon_sourceURL": "",
    "addon_docFileName": "readme.html",
    "addon_minimumNVDAVersion": "2024.1",
    "addon_lastTestedNVDAVersion": "2026.1",
    "addon_updateChannel": None,
    "addon_license": "GPL v2",
    "addon_licenseURL": "https://www.gnu.org/licenses/old-licenses/gpl-2.0.html",
}

pythonSources = ["addon/globalPlugins/jobFormFiller/*.py",
                 "addon/globalPlugins/jobFormFiller/core/*.py"]
i18nSources = pythonSources + ["buildVars.py"]
excludedFiles = []
baseLanguage = "en"
markdownExtensions = []
brailleTables = {}
symbolDictionaries = {}
