#!/usr/bin/env bash
set -euo pipefail

VENV="${VENV:-$HOME/ibm-6c2q-venv}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if ! command -v uv >/dev/null 2>&1; then
  echo "Installing uv..."
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
fi

uv python install 3.13
rm -rf "$VENV"
uv venv "$VENV" --python 3.13
uv pip install --python "$VENV/bin/python" -r "$ROOT/requirements.txt"

echo
echo "Environment ready."
echo "Activate with: source $VENV/bin/activate"
echo "Then save credentials: python hardware/save_open_plan_account.py"
echo "Then preflight:        python hardware/preflight_open_plan.py"
