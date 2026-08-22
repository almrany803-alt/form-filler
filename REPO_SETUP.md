# Setting up the GitHub repo

This mirrors how we set up Zul, adapted for an NVDA add-on. The big difference:
Zul's repo was a distribution point only, so it had no .gitignore and no source
in it. This is a real development repo, so it keeps the source and tests, has a
.gitignore, and runs the tests on every push.

## 1. Create and push the repo

Fastest, and no credential ever passes through a chat: use your own GitHub CLI
login and the bundled script.

```
gh auth login                       # one time; stores your login in your keychain
pwsh -File setup-repo.ps1 -RepoName jobformfiller -Private
```

That inits git, commits, creates the repo under your account, and pushes.

If you would rather use a token (your call), scope it tightly, the way we did
for Zul:
- Personal access tokens -> Fine-grained tokens -> Generate new token.
- Name: `jobformfiller automation`.
- Expiration: the longest offered (366 days).
- Resource owner: your own account.
- Repository access: Only select repositories -> pick this one repo only. This
  is the part that matters: the token can touch nothing else on your account.
- Repository permissions: Contents = Read and write (enough to push and to
  create releases). Leave the rest as No access.

Then push with the token as the git credential. Rotate it afterwards if it ever
passes through a chat.

## 2. What is in the repo

- `addon/` the add-on source (the global plugin and the pure-Python core).
- `tests/` the brain tests. They run in CI on every push (see
  `.github/workflows/tests.yml`).
- `live-tests/` the real-NVDA, real-browser tests (Windows/CI).
- `build.py` one command to package the installable add-on.
- `buildVars.py` the manifest source (name, version, author, NVDA versions).
- README, LICENSE (GPL v2), .gitignore.

## 3. Releases carry the installable add-on

Unlike Zul, there is no updater, no asset packs, no special "files" release.
An add-on release is simple: one built `.nvda-addon` file per version.

```
python build.py            # prints the file name AND its SHA256
gh release create v0.2.2 jobFormFiller-0.2.2-dev.nvda-addon --notes "..."
```

The permanent download URL of that attached file, plus the SHA256 that
`build.py` prints, are exactly the two things the Add-on Store submission form
asks for when you are ready to publish. Until then, people can install the file
directly, the same way you have been.
