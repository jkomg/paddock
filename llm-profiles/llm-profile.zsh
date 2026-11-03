# Folder-aware LLM logins. Sourced from ~/.zshrc. Rules: ~/.config/llm-profiles/{profiles,folders}.tsv
#
#   claude [<profile>] [args]   login comes from the folder unless a profile (or alias) is named;
#   codex  [<profile>] [args]   a login the folder does not allow is refused.
#   agy [args]                  refused if the active Gemini login is not allowed here.
#
# Profiles and their aliases come from profiles.tsv. Naming one also adds
# --dangerously-skip-permissions to sessions; subcommands (auth, mcp, doctor, ...) never get it.
# `--dangerous` works anywhere. A CLAUDE_CONFIG_DIR / CODEX_HOME already set in the environment is
# kept when it names a profile the folder allows. Outside the listed folders, plain `claude` /
# `codex` behave exactly as before.

_llm_profile_py="$HOME/.config/llm-profiles/llm_profile.py"
typeset -gA _llm_alias
() {
  local l
  for l in ${(f)"$(python3 -I "$_llm_profile_py" names 2>/dev/null)"}; do _llm_alias[${l%%=*}]=${l#*=}; done
}

_llm_pick() {  # _llm_pick <tool> <first-arg> -> sets _llm_named, _llm_dir; returns 1 on refusal
  _llm_named=""
  [[ -n "$2" && -n "${_llm_alias[$2]-}" ]] && _llm_named="${_llm_alias[$2]}"
  _llm_dir=$(python3 -I "$_llm_profile_py" resolve "$1" "$PWD" "$_llm_named") || return 1
}

claude() {
  _llm_pick claude "$1" || return 3
  [[ -n "$_llm_named" ]] && shift
  local args=() skip=0 a
  for a in "$@"; do
    if [[ "$a" == "--dangerous" || "$a" == "--dangerously-skip-permissions" ]]; then skip=1; else args+=("$a"); fi
  done
  if [[ -n "$_llm_named" ]]; then
    case "${args[1]}" in
      doctor|update|upgrade|install|mcp|config|plugin|plugins|auth|setup-token|migrate-installer|agents) ;;
      *) skip=1 ;;
    esac
  fi
  (( skip )) && args=(--dangerously-skip-permissions "${args[@]}")
  if [[ -z "$_llm_dir" ]]; then
    command claude "${args[@]}"
  elif [[ -n "${CLAUDE_CONFIG_DIR:-}" && "$CLAUDE_CONFIG_DIR" != "$_llm_dir" ]]; then
    print -u2 "llm-profile: CLAUDE_CONFIG_DIR is set to $CLAUDE_CONFIG_DIR but this folder needs ${_llm_dir/#default/the default (unset)}; unset it first."
    return 3
  elif [[ "$_llm_dir" == "default" ]]; then
    command claude "${args[@]}"           # the "default" profile's login lives in ~/.claude.json
  else
    CLAUDE_CONFIG_DIR="$_llm_dir" command claude "${args[@]}"
  fi
}

codex() {
  _llm_pick codex "$1" || return 3
  [[ -n "$_llm_named" ]] && shift
  if [[ -z "$_llm_dir" ]]; then
    command codex "$@"
  elif [[ -n "${CODEX_HOME:-}" && "$CODEX_HOME" != "$_llm_dir" ]]; then
    print -u2 "llm-profile: CODEX_HOME is set to $CODEX_HOME but this folder needs $_llm_dir; unset it first."
    return 3
  else
    CODEX_HOME="$_llm_dir" command codex "$@"
  fi
}

agy() {
  python3 -I "$_llm_profile_py" check-gemini "$PWD" || return 3
  command agy "$@"
}
