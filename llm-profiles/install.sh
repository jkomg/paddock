#!/usr/bin/env bash
# Compatibility entry point. Native Windows: python llm-profiles/install.py
set -euo pipefail
exec python3 -I "$(dirname "$0")/install.py" "$@"
