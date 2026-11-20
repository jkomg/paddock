# Changelog

## 0.2.1-preview — 2026-11-20

- **Setup finds every T3 provider.** The interview now starts from T3's live provider
  list instead of a fixed set of names. Previously an enabled provider whose instance ID
  wasn't the default (for example a ChatGPT/Codex instance called `codex_work` next to a
  disabled `codex`) could be left out. New `paddock.py providers --catalog FILE` lists
  every instance with its display name, driver, model count and, for unusable ones, T3's
  reason. Binding uses that instance ID.

## 0.2.0-preview — 2026-11-20

- **Exposed credentials stop the work.** A password, API key, token or private key seen
  in chat, files, output or evidence is treated as compromised. Agents stop, never repeat
  it, and walk the user through revoking and replacing it. New
  `paddock.py secret open|close|status|scan` commands. While an incident is open, `task`,
  `verify` and `packet` refuse to run and `audit` and `doctor` fail. Closing needs
  secret-free evidence (verified) or the user's statement (user-attested). Changed or
  missing evidence reopens the incident. Review packets that look like they contain a
  credential are refused.
- `SETUP-GUIDE.md`: a step-by-step guide for first-time Windows and Mac users, shipped in
  the installer ZIP.
- `QUICKSTART.md`: which package to share and how to check its SHA-256.
- An installed-copy smoke test: install, create a project, remove the skill, then run a
  real test through the project's copied runner.

## 0.1.0-preview — 2026-11-09

First public preview: onboarding interview, project adoption, real-check verification,
evidence packets, separate code and process reviews, and the managed installer.
