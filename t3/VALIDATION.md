# Preview validation — 2026-11-09

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

- Native Windows/PowerShell execution. CI includes native Windows jobs, but those jobs
  have not executed as part of this local delivery.
- Hosted CI execution and any branch-protection setup.
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
