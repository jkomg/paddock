# Evidence commands and their limits

From an adopted repo (`python3` may be needed on macOS):

    python .paddock/paddock.py task --task example --request original-request.md --contract accepted-contract.md
    python .paddock/paddock.py verify --task example

Capture the original request faithfully, including later steering. Keep accepted
interpretations in contract.md; do not silently rewrite the request to fit the result.
`task` prints the contract digest for instruction review. The contract digest covers
request, contract, AGENTS.md, CLAUDE.md, shared rules, project checks and crew policy.

After verification, write the proposed final claims to `.paddock/runs/example/claims.md`.
Write host.json in the same directory, for example:

    {"builder_session_ids":["actual-session-id"],"controls_state":"unknown",
     "receipts":["evidence/actual-builder-tool-result.json"]}

Use actual saved host/tool results, with sensitive data removed before distribution.
controls_state is observed, partially_observed or unknown. Explain each control and
its actual trigger/result in receipts; this field alone proves nothing. Include the
coordinator as a builder if it implemented changes. An absent receipt is not success.
All receipt paths are relative to the task directory, with no traversal or symlinks.

    python .paddock/paddock.py packet --task example

Give independent reviewers the packet path, its printed digest, source path, relevant
source files and original evidence paths. The packet binds evidence by hash; it does
not transmit or redact any data. Save reviews in the format in reviews.md. Then:

    python .paddock/paddock.py audit --task example

The audit checks completeness, matching source/input hashes, actual check outcomes,
review records, and distinct recorded session IDs. It does NOT authenticate receipt
provenance, know a model's intent, judge whether tests are meaningful, or prove controls
were enforced. All files remain editable by the user/agents. The adversary must inspect
raw host evidence and exact claims; do not represent this CLI as tamperproof attestation.

## Check adapters

`command` means only successful process completion. `test` requires a fresh JSON file
at the environment variable PADDOCK_CHECK_RECEIPT, written after the runner finishes:

    {"completed":true,"passed":7,"failed":0,"skipped":0}

Counts must be nonnegative integers. Zero passing tests, missing/malformed receipt,
any failures, any skips, early process exit and timeout prevent a complete test result.
Expected failures count as skipped. A test may exit 0 before completing; no receipt
means incomplete. Raw logs and receipts are retained in unique directories for every
run. An old receipt cannot satisfy a new run. Prior failed attempts remain on disk.

The included unittest adapter records actual TestResult counts. Other frameworks need
an adapter that obtains equivalent real runner data. A fake JSON file, echo command,
or copied console summary is not an adapter. The adversary should inspect the adapter
and test command when evaluating the claim that checks ran.

`verification_mode: tests` requires at least one test check. `commands` is an explicit
choice for work without applicable tests and must be described as command verification,
not tests passed. An empty check list is always unconfigured.

Source hashing covers Git tracked and nonignored untracked files plus required Paddock
policy/config files. Generated run artifacts are excluded to avoid circular hashes.
Configure project build outputs in .gitignore. External dependencies, ignored app files,
remote services and symlink targets outside the manifest are not captured. Submodules
are refused by this preview rather than silently treated as covered. No project check
can modify source and still yield a fresh successful verification receipt.

Native Windows timeout cleanup uses taskkill /T /F; Unix uses a process group. Escaped
or deliberately detached processes need additional host controls. Run the native CI
suite and a real T3 smoke task on each supported OS before claiming end-to-end support.
