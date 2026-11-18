# Exposed credentials: stop, rotate, verify

A credential is any password, API key, access token, private key, session cookie,
recovery code or connection string with a password in it. Paddock treats one as
**compromised** once it appears in chat (from the user or any agent), a file an agent
read, command or tool output, logs, a commit or a review packet. Chat transcripts are kept
by the provider and the host, and deleting a message does not undo that. The only fix is
to rotate the credential.

This applies to every role. A worker or reviewer that sees a credential tells the
coordinator, and the coordinator tells the user. Nobody decides alone that a leak is
harmless. Only the user can say it is not a real credential.

## 1. Stop at once

- Stop the current task, including "just this last step". Don't start new work, dispatch
  workers or send packets.
- Never repeat the value. Refer to it by kind and at most its last 4 characters.
- Don't write it to files, memory, commits, briefs, logs or tickets, and don't pass it to
  another worker, reviewer or provider.
- If it was written to a project file, don't commit. If it is already committed, say so;
  rewriting history doesn't help once it has been pushed. Rotation is still the fix.

## 2. Tell the user plainly

Say what was exposed (kind and last 4), where it appeared, and why it matters. Keep it short
and calm, without blame. For example:

> I need to stop here. The message above contains what looks like your LiteLLM API key
> (ending `x7Qa`). Chat history is stored by the provider and by T3, so treat that key as
> exposed. Let's rotate it now (about two minutes) before we continue.

## 3. Record it

```sh
python3 .paddock/paddock.py secret open --kind "LiteLLM API key" --where "T3 chat, coordinator thread" --hint x7Qa
```

Use `python` on Windows. While any incident is open, `task`, `verify` and `packet` refuse to
run and `audit` reports an error. That is intended. Don't work around it with tools outside
Paddock.

## 4. Do the rotation for them

Make rotation easy. Identify who issued the credential and give exact steps: the specific
revoke/regenerate page or console path, and commands the user can paste. Offer to run the
commands that don't need the secret, such as opening the page, listing keys by ID, or deleting
the old key by its ID. Revoking a key changes a credential, so confirm before you run anything
that does.

Typical routes (check the issuer's current docs if one is unfamiliar):

| Issuer | Revoke and replace |
| --- | --- |
| Company LiteLLM gateway | The company's key self-service page: delete the old key, create a new one |
| OpenAI / ChatGPT API | platform.openai.com → API keys: revoke, create |
| Anthropic API | console.anthropic.com → API keys: disable/delete, create |
| GitHub token | github.com → Settings → Developer settings → tokens: delete, create. `gh auth refresh` for the gh CLI login |
| AWS access key | `aws iam create-access-key`, update the consumer, then `aws iam delete-access-key --access-key-id <OLD_ID>` |
| Password | Change it on the service; sign out other sessions; turn on MFA if offered |
| SSH/private key | Generate a new key, replace the public key wherever it is authorised, remove the old one |

Store the new credential safely and **never ask for it in chat**. Options: T3's secure
secret entry, the OS keychain (macOS Keychain, Windows Credential Manager), or a field the
provider manages. If something must read it from an environment variable, load that from
the keychain rather than writing it into a dotfile in the repo.

## 5. Verify, then close

Preferably use evidence that doesn't reuse the exposed value:

- `issuer_shows_revoked`: the issuer's own listing shows the old credential deleted or
  inactive, e.g. `aws iam list-access-keys`, or the key page with the old key gone. Save that
  output or text to a file with no secret in it.
- `old_rejected`: one request to the credential's own issuer with the old value returns
  401/403. Send it only to that issuer, without echoing it, and save just the status and
  error body.

Only when neither is possible (for example a website password) use `user_attested` with
the user's own statement of what they did. That is recorded as attested, not verified, and
the final report says so. If the user says the flagged text is not a real credential
(an example, a revoked test key), use `false_positive` with their statement.

```sh
python3 .paddock/paddock.py secret close --id <ID> --verification issuer_shows_revoked \
  --evidence revoked.txt --replacement secure_entry
python3 .paddock/paddock.py secret close --id <ID> --verification user_attested \
  --statement "Changed the password at 14:05 and signed out other sessions" --replacement os_keychain
```

`close` refuses evidence or statements that themselves contain a credential. Resume the task
only after `secret status` shows nothing open. Mention the closed incident and its assurance
level in the final report.

## Catching what people miss

`paddock.py secret scan FILE...` (or `-` for stdin) flags likely credentials by pattern
and shows at most the last 4 characters. `packet` runs the same scan over everything it
would send to reviewers and refuses on a hit. A clean scan doesn't prove there is no
secret: recognising one in context is still every agent's job.
