# Preview validation — 0.2.0-preview, 2026-11-20

This is a public preview, not a claim of complete cross-platform host validation.

## Executed on macOS

Test counts are not written here: they change whenever a test is added, and a stale count
is a false claim. Run the suite and read the counts from its output. From the extracted
package:

```sh
python3 -m unittest discover -s tests -v
```

From a repository checkout, use `-s t3/tests`; the guard suite is `-s llm-profiles/tests`.

- Extracted installer ZIP: the package suite ran from a fresh path containing spaces.
- Skill metadata/frontmatter validator passed.
- Both ZIP inventories and payload SHA-256 hashes were checked against their manifests.

## Hosted platform checks

Every change reaches `main` through a pull request; a repository ruleset requires the
macOS, Ubuntu and native Windows jobs to pass and review threads to be resolved, and
blocks force-pushes and branch deletion. All three jobs run the T3 package suite and the
tests from the extracted installer archive. The macOS and Ubuntu jobs also run the full
legacy guard suite (`llm-profiles/tests`) and shell syntax checks. The Windows job runs
only the guard's portable install and hook tests (`test_install_portable.py`), plus the
PowerShell installer test.

[GitHub Actions run 44787768926](https://github.com/jkomg/paddock/actions/runs/44787768926)
passed on 2026-11-20 for `main` at commit `23fdfefff45a3bccf3a15e1e175d2515894bb545`, which
includes the credential stop and the installed-copy smoke test. The 0.2.0 version bump
and these documentation edits run in their own pull request's CI.

This verifies committed code, not real signed-in T3 integration.

## Claims and the tests that prove them

Each row is a claim the package makes, and the test in `tests/test_package.py` that fails
if the claim stops being true. `test_validation_claims_name_real_tests` fails if a row
names a test that does not exist.

| Claim | Test |
|---|---|
| Every file a command writes is re-read, and its SHA-256 is reported | `test_writes_report_hashes_of_what_is_on_disk` |
| A preview writes nothing | `test_preview_does_not_create_repo`, `test_preview_reports_nothing_written` |
| Adoption keeps existing project rules and never overwrites | `test_adoption_preserves_existing_instructions_and_refuses_overwrite` |
| A failed adoption restores every file it changed | `test_failed_adoption_restores_every_file` |
| Symlinked destinations are refused before anything is written | `test_symlink_adoption_refuses_without_writing` |
| Verification starts unconfigured; no checks is not success | `test_no_checks_is_not_success` |
| Zero, skipped or failed tests and early exits never count as passing | `test_zero_skipped_failure_and_early_exit_never_succeed` |
| Exit status 0 alone is not test evidence | `test_generic_exit_zero_is_not_test_evidence` |
| Command-only verification needs an explicit mode | `test_command_only_requires_explicit_mode` |
| Real unittest runs are recorded, including project imports | `test_actual_unittest_execution`, `test_unittest_adapter_imports_real_project_module` |
| A timeout stops the whole process tree and is not success | `test_timeout_stops_descendant_and_does_not_claim_success` |
| An interrupted or failed new attempt invalidates an older green result | `test_interrupt_cleans_up_child_and_never_keeps_green_status`, `test_interrupted_attempt_invalidates_old_success_before_waiting`, `test_failed_new_attempt_invalidates_old_green_verification` |
| Source edits, including permission changes, invalidate verification | `test_source_mutation_invalidates_success`, `test_executable_mode_change_invalidates_source`, `test_owner_execute_change_not_hidden_by_other_execute_bit` |
| Changed claims, logs, source or missing receipts fail the audit | `test_stale_claims_logs_source_and_missing_receipts_fail` |
| Empty host receipts or claims are incomplete | `test_empty_host_receipt_or_claims_are_incomplete` |
| Missing reviews fail; unknown host controls stay unknown | `test_missing_reviews_fail_and_unknown_controls_remain_unknown` |
| Missing or corrupt records are reported as audit errors, not crashes | `test_audit_reports_missing_or_corrupt_records_instead_of_crashing` |
| The audit names the digests it compared | `test_audit_names_the_digests_it_compared` |
| A builder, or one session in two roles, cannot fill the review roles | `test_builder_or_same_session_cannot_fill_final_review_roles` |
| A changed contract invalidates the instruction review | `test_changed_contract_invalidates_instruction_review` |
| Windows-anchored paths are refused on every platform | `test_windows_anchored_receipt_paths_rejected_on_every_platform` |
| Roles stay unbound until bound to a live, approved instance | `test_interview_records_unbound_roles`, `test_route_requires_explicit_binding_and_live_provider` |
| Installation previews, upgrades, uninstalls, and refuses local changes | `test_install_preview_upgrade_and_uninstall`, `test_installer_refuses_local_changes` |
| Installed skill creates a project whose runner works after skill removal; missing reviews remain incomplete | `test_installed_skill_creates_and_verifies_project` |
| An open exposed-credential incident blocks task, verify, packet, audit and doctor | `test_open_credential_incident_blocks_task_work` |
| An incident closes only with secret-free evidence (verified) or the user's statement (attested), and never stores the value | `test_incident_closes_only_with_clean_evidence_or_a_statement` |
| A closed incident reopens if its rotation evidence is missing or changed, or its record is inconsistent | `test_changed_or_missing_rotation_evidence_reopens_the_incident` |
| A review packet is refused when its evidence contains a likely credential | `test_packet_refuses_evidence_containing_a_credential` |
| The credential scan flags key and password shapes but not code or placeholders | `test_secret_scan_flags_credentials_but_not_code_or_placeholders` |

## Earlier review history

An independent adopter used the skill in a scratch project to implement a count-summary
function. It exposed an import-path bug in the unittest adapter. After a scratch correction,
seven test methods passed. The product now contains that fix plus a real-module-import
regression. The adopter's audit correctly remained incomplete: provider bindings and
independent reviews were not fabricated to turn a partial setup green.

Independent code review found four initial defects. Two subsequent checks found additional
mode/interrupt and adapter issues; all reported material implementation defects were fixed.
The final bounded code review found no remaining material defect in the examined runtime,
unittest adapter and package tests. This is scoped review, not proof of correctness.

## Still unverified

- Credential detection in live chat. The rule depends on the agent recognising a pasted
  credential; `secret scan` and the packet check are pattern matches that can miss one,
  and nothing intercepts a message before the model reads it.
- End-to-end T3 cross-provider dispatch, provider-specific skill loading, and actual
  host permission enforcement on recipients' machines.
- A full multi-provider task with real signed-in identities and independent host receipts.

The Python CLI never dispatches paid work, authenticates providers, or mutates T3's private
configuration. The active agent skill uses supported host tools for orchestration. Tests
with synthetic receipts prove local schema/freshness behavior, not authenticity of host
results. An audit may report record completeness while host controls remain unknown.

Before broader rollout, run the included tests natively on Windows and a bounded real T3
task/review/adversary cycle using company-approved resources on each intended host. Preserve
failures and unknowns. Do not substitute a provider list, successful installation or an
editable local receipt for evidence that the real integration worked.
