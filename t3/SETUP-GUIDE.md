# Paddock: your first project

A step-by-step guide for Windows and Mac, with ChatGPT/Codex or Claude in T3 Code.
It is for people who have never used a terminal; `QUICKSTART.md` is the short version.

> **Start here.** Use this guide with the Paddock installer ZIP and `SHA256SUMS` from the
> same build. If your company runs its own model gateway (for example LiteLLM), your setup
> owner gives you its address and how to get a key; section 4 shows where those go.

## What you are setting up

T3 Code is the app you open to work with your AI assistant. Codex is the OpenAI coding
assistant you connect through your ChatGPT account; Claude Code is the Claude coding
assistant. Paddock adds a repeatable process for planning, doing work, checking results and
getting separate reviews.

You do not install a model server, Docker or a local model for this setup.

## What to have ready

- Access to an approved ChatGPT/Codex or Claude Code account.
- The Paddock installer ZIP and its `SHA256SUMS` file.
- Permission to install software on your computer. If installation is restricted, use your
  normal software-request process.
- Optional: your company gateway's base URL and a way to get your own key (section 4).

One approved AI provider is enough to start. Separate AI sessions can fill the
coordinator, builder, code reviewer and process reviewer roles.

## Follow your path

- **Windows:** section 1 → 3 → 4 (optional) → 5 → 7 and 8.
- **Mac:** section 2 → 3 → 4 (optional) → 6 → 7 and 8.
- Sections 9–11 cover troubleshooting, maintenance and reference.

## How to use command boxes

A terminal is a window where you paste an instruction and press Enter. Copy only the
contents of a command box, one line at a time unless told otherwise. Wait for the prompt to
return before running the next line.

Most everyday work happens in the T3 conversation; the command boxes are mainly for
installation. Never put a real API key into a document or an ordinary chat message.

---

## 1. Windows: prepare your computer

### Install T3 Code

[Official download page](https://t3.codes/download): choose Stable, then the Windows
download. Run the `.exe` and follow its installer, then open T3 Code from the Start menu.
This guide uses native Windows, not WSL or a remote server.

### Open PowerShell

Open Start, type PowerShell, and open Windows PowerShell (or a PowerShell tab in Windows
Terminal). You do not need *Run as administrator*. Paste these lines separately:

```powershell
python --version
git --version
```

Continue if Python reports 3.11 or newer and Git reports a version. A Microsoft Store
window opening instead of a Python version means Python is not ready.

### Install Python if needed

[Official Python downloads](https://www.python.org/downloads/windows/): install a current
Python 3 release, 3.11 or newer. If the installer offers *Add Python to PATH*, select it.
Reopen PowerShell and run `python --version` again. If `py --version` works instead, use
`py` wherever this guide says `python`.

### Install Git if needed

[Git for Windows](https://git-scm.com/install/windows): choose x64 (ARM64 only on an ARM
computer), keep the defaults, reopen PowerShell and run `git --version` again.

> **Checkpoint:** T3 Code opens, Python is 3.11+, and Git prints a version. Next: section 3.

## 2. Mac: prepare your computer

### Install T3 Code

[Official download page](https://t3.codes/download): choose Stable. In the Apple menu → About
This Mac, an Apple M-series chip means Apple Silicon; Intel means the x64 build. Open the `.dmg`,
drag T3 Code to Applications if shown, and open it.

### Open Terminal

Press Command–Space, type Terminal, press Return. Paste these lines separately:

```sh
python3 --version
git --version
```

### Install Python if needed

[Official Python downloads for Mac](https://www.python.org/downloads/macos/): install
Python 3.11 or newer from the `.pkg`, reopen Terminal and run `python3 --version` again.

### Install Git if needed

If `git --version` offers to install Apple Command Line Tools, accept. Otherwise run:

```sh
xcode-select --install
```

You do not need the full Xcode app. See also
[Git's macOS instructions](https://git-scm.com/install/mac).

> **Checkpoint:** T3 Code opens, Python is 3.11+, and Git prints a version. Next: section 3.

## 3. Connect ChatGPT/Codex or Claude

Use the account your organisation approves. Settings → Providers in T3 is where you check
an existing connection; button names can vary by release.

### Option A: ChatGPT/Codex

1. In T3 onboarding or Settings → Providers, choose **Connect with ChatGPT**. Pick your
   local computer if asked which environment to configure.
2. Complete the OpenAI sign-in with your approved account and workspace. T3 handles the
   Codex installation for this connection.
3. Confirm the connection is ready and pick it in the model picker for your project.

An existing working Codex CLI login also works; keep its configuration.
[T3: Codex connection instructions](https://github.com/pingdotgg/t3code/blob/main/docs/user/providers-codex.md)

### Option B: Claude

Install Claude Code if needed, then open a new terminal window.

Windows PowerShell:

```powershell
irm https://claude.ai/install.ps1 | iex
```

Mac Terminal:

```sh
curl -fsSL https://claude.ai/install.sh | bash
```

Then, on either system:

```sh
claude --version
claude auth login
```

Sign in with your approved Claude account, then enable Claude in T3 Settings → Providers
and confirm the account it reports. Preserve any existing custom account folders.
[Claude Code installation guide](https://code.claude.com/docs/en/quickstart)

> **Checkpoint:** your provider is available in T3. A browser chat alone does not confirm
> this. You do not need both subscriptions.

## 4. Optional: your company's model gateway

Skip this section if your organisation has no gateway such as LiteLLM.

Your setup owner tells you:

- the **base URL**, usually ending in `/v1` (for example `https://llm-gateway.example.com/v1`);
- how to **activate your own key** (often a self-service portal page).

Model: an exact model name available to your key, confirmed during the interview.
`MODEL_NAME` in any example is a placeholder.

### Give the key only through secure entry

During the setup interview, say your key is ready and ask the assistant to open T3's
secure secret-entry request. Enter the key there, never in an ordinary chat message. If
secure entry is unavailable, ask your setup owner for an approved credential store.

You can authorise one small Hello request to confirm access; it may use some of your
organisation's model quota. A successful Hello confirms gateway access only. It does not
show that T3 can use that model as a Paddock worker; the interview checks that separately.

## 5. Windows: install Paddock

### Check the ZIP and open the installer folder

1. Save the installer ZIP and `SHA256SUMS` in Downloads and check the hash (section 11).
2. Right-click the ZIP → Extract All → Extract.
3. Open the extracted folders until you see `install.py` and `QUICKSTART.md`.
4. Click the File Explorer address bar, type `powershell`, press Enter. Run `dir` and
   confirm `install.py` is listed.

### Choose the skills folder

A skill is a set of instructions the assistant loads. These lines use the default folders.
If T3 Settings → Providers shows a custom `CODEX_HOME` or Claude configuration directory,
use its `skills` subfolder instead.

For ChatGPT/Codex:

```powershell
$paddockSkills = "$HOME/.codex/skills"
```

Or, for Claude:

```powershell
$paddockSkills = "$HOME/.claude/skills"
```

Then run these separately:

```powershell
python install.py --skills-dir "$paddockSkills"
python install.py --skills-dir "$paddockSkills" --apply
python "$paddockSkills/paddock-crew/scripts/paddock.py" --version
```

The first previews, the second installs, and the third prints the version in the ZIP's
`VERSION` file. To use both providers, repeat for the other folder. Do not also install the
smaller skill-only ZIP.

> **Checkpoint:** the version command works. Start a fresh provider session in T3 so it can
> discover the skill. Keep the extracted folder for updates and removal. Next: section 7.

## 6. Mac: install Paddock

### Check the ZIP and open the installer folder

1. Save the installer ZIP and `SHA256SUMS` in Downloads and check the hash (section 11).
2. Double-click the ZIP to extract it, and open folders until you see `install.py`.
3. In Terminal, type `cd ` (with a space), drag the installer folder into Terminal, and
   press Return. Run `ls` and confirm `install.py` is listed.

### Choose the skills folder

For ChatGPT/Codex:

```sh
paddockSkills="$HOME/.codex/skills"
```

Or, for Claude:

```sh
paddockSkills="$HOME/.claude/skills"
```

Then run these separately:

```sh
python3 install.py --skills-dir "$paddockSkills"
python3 install.py --skills-dir "$paddockSkills" --apply
python3 "$paddockSkills/paddock-crew/scripts/paddock.py" --version
```

> **Checkpoint:** the version command works. Start a fresh provider session in T3. Keep the
> extracted folder for updates and removal. Next: section 7.

## 7. Run the Paddock setup interview

### Create a practice project

Create a folder named `Paddock Practice` in Documents. In T3, drag it onto the project
sidebar (or Add project), start a new conversation there, and pick the connection from
section 3. Never use the installer folder as a project.

### Paste this into T3

Delete the bracketed gateway sentences if you skipped section 4.

```text
Use Paddock Crew to set up this project. First confirm that you can load the installed
paddock-crew skill. Interview me in plain language about my approved ChatGPT/Codex,
Claude [and company LiteLLM gateway] access. Keep local models off.

[My gateway base URL is <BASE URL FROM YOUR SETUP OWNER>. I activated my own key. Request
it through secure secret entry; do not ask me to paste it into chat or print it. I
authorise one small Hello request to check access using an approved model.]

Discover T3's actual provider capabilities. Confirm my account, exact model and supported
connection before assigning any role. Keep code review and process review in separate
fresh sessions. Preserve existing project instructions and tests. Create the project setup
and configure real verification checks. Do not publish, deploy or buy anything. Explain any
unavailable connection and what still needs setup.
```

### Answer the interview

The assistant first lists every provider T3 has, by the name shown in T3's Providers
settings, including any T3 can't use right now and why. If one you enabled is missing,
say so; it may be switched off in this project's settings even though it's on in
Providers.

Say which accounts are approved, which assistant you prefer and what you want to make. Ask
for the available approved models rather than guessing. If no compatible gateway adapter
exists, the assistant must say so; you can continue with Codex or Claude and keep the
gateway marked unavailable.

> **Checkpoint:** the assistant names the skill, project folder, account and model choices,
> and verification command, and the project has a `.paddock` folder. If the skill will not
> load, see section 9.

## 8. Complete your first checked task

### Check the setup

```text
Run Paddock doctor for this project. Explain any missing provider bindings or verification
checks and finish configuring them. Do not report setup complete while required settings
are missing.
```

The underlying command, run from the project folder (`python3` on Mac):

```sh
python .paddock/paddock.py doctor --project .
```

A passing doctor checks configuration; it does not call providers or prove tests passed.

### Your first task

```text
In this practice project, use Paddock to create a simple local welcome webpage titled
"My Paddock Practice". Include a short introduction and a checklist of three things I want
to learn. Save it as index.html. Do not add a server, paid service or external dependency.

Agree on concrete checks for the title, introduction and three checklist items. Run those
checks. Obtain a fresh code review and a separate fresh process review. Fix findings within
this scope. Tell me exactly how to open the file and what was verified, including any
review or check that could not run. Do not publish or deploy.
```

Open `index.html` yourself and confirm the title, introduction and three items appear. The
final report should list changes, checks run and their results, code-review findings,
process-review findings and limitations, each separately.

> **Ready for a pilot task** when T3 uses your provider, Paddock loads, the project is
> configured, the sample works, checks ran and separate reviews completed. A Hello response
> or doctor result alone is not the end-to-end check.

## 9. If something goes wrong

**Python or Git "not recognized" / "command not found".** Reopen the terminal after
installing. On Windows try `py`; on Mac use `python3`. Don't paste Mac commands into
PowerShell.

**"Can't open file install.py".** You are in the wrong folder or inside the ZIP view.
Extract the ZIP and open a terminal in the folder that contains `install.py`.

**Existing or modified installation.** For an unchanged install, upgrade (section 10). If
files were edited locally, ask your setup owner to reconcile them; do not force-delete.

**T3 cannot find Paddock.** Paste:

```text
I installed paddock-crew, but this session cannot find it. Please compare this provider's
actual configuration home with the installation folder, check skill-discovery support, and
tell me the exact fix. Do not change credentials or reinstall unrelated software.
```

Then start a fresh provider session.

**Provider login or gateway fails.** Check Settings → Providers. For the gateway: 401
usually means an invalid or inactive key, 403 an access restriction, 429 a usage limit, and
model-not-found needs an exact model name. For connection or certificate errors, check
VPN/network requirements; never disable certificate verification.

**You pasted a password or key into chat.** The assistant will stop and won't continue
until it's rotated. That is deliberate: chat history is stored, so the value counts as
exposed. It shows you exactly where to revoke the old one and create a new one, runs what
it can for you, and records the evidence. Give the new value only through secure entry.

**Doctor fails or reviews are missing.** Ask the assistant to finish real checks and
bindings. Never replace a check with one that always passes. If separate reviews cannot
run, don't call the task reviewed.

> **Asking for help:** send your OS, T3 version, provider, step number and the exact error
> with secrets removed. Never send keys, tokens or credential files.

## 10. Everyday use, updates and removal

Open T3, choose your project, confirm the provider and account, and describe the outcome
you want. You don't reinstall Paddock per task. Keep local crew bindings and run records
(`.paddock`) out of anything you share; ask the assistant for a clean handoff if unsure.

**Update:** extract the new installer ZIP (check its hash), open a terminal there, set
`paddockSkills` again (section 5 or 6), preview, then apply. Use `python3` on Mac.

```sh
python install.py --skills-dir "$paddockSkills" --upgrade
python install.py --skills-dir "$paddockSkills" --upgrade --apply
```

Updating the skill does not update `.paddock` files already copied into projects.

**Remove:** from the retained installer folder:

```sh
python install.py --skills-dir "$paddockSkills" --uninstall
python install.py --skills-dir "$paddockSkills" --uninstall --apply
```

This removes only the managed skill: not your projects, T3, Python, Git, logins or keys.

## 11. Checking the ZIP and references

Keep the installer ZIP and `SHA256SUMS` together, open a terminal in that folder, and run
(use your actual filename):

Windows PowerShell:

```powershell
Get-FileHash .\paddock-t3-installer-VERSION.zip -Algorithm SHA256
```

Mac Terminal:

```sh
shasum -a 256 paddock-t3-installer-VERSION.zip
```

Compare the hash with the line for that filename in `SHA256SUMS` (case doesn't matter). If
they differ, get a fresh copy. Matching hashes detect a changed download; they don't prove
who made the files, so get both from the intended source.

- [T3 downloads](https://t3.codes/download) ·
  [T3 install help](https://github.com/pingdotgg/t3code/blob/main/docs/user/install.md) ·
  [T3 Codex setup](https://github.com/pingdotgg/t3code/blob/main/docs/user/providers-codex.md) ·
  [T3 Claude setup](https://github.com/pingdotgg/t3code/blob/main/docs/user/providers-claude.md)
- [OpenAI Codex authentication](https://developers.openai.com/codex/auth/) ·
  [Claude Code installation](https://code.claude.com/docs/en/quickstart)
- [Python downloads](https://www.python.org/downloads/) · [Git downloads](https://git-scm.com/install/)

> **Validation limit:** this guide is based on the package, `QUICKSTART.md`,
> `VALIDATION.md` and official setup documentation. These exact steps have not been run
> end to end on fresh Windows and Mac computers with live accounts. Complete the practice
> task before a wider rollout.
