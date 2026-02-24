#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Install aligo CLI wrapper script.

Usage:
  scripts/install_cli.sh [options]

Options:
  --name <cmd>        Command name (default: aligo)
  --target <dir>      Install directory (default: /usr/local/bin)
  --python <bin>      Python executable (default: python3)
  --entry <path>      CLI entry file (default: <repo>/src/aligo/cli.py)
  --user              Install to ~/.local/bin
  --force             Overwrite existing command
  -h, --help          Show help
EOF
}

CMD_NAME="aligo"
TARGET_DIR="/usr/local/bin"
PYTHON_BIN="python3"
FORCE="0"
USER_MODE="0"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
ENTRY_PATH="${REPO_ROOT}/src/aligo/cli.py"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --name)
      CMD_NAME="$2"
      shift 2
      ;;
    --target)
      TARGET_DIR="$2"
      shift 2
      ;;
    --python)
      PYTHON_BIN="$2"
      shift 2
      ;;
    --entry)
      ENTRY_PATH="$2"
      shift 2
      ;;
    --user)
      USER_MODE="1"
      shift
      ;;
    --force)
      FORCE="1"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage
      exit 2
      ;;
  esac
done

if [[ "${USER_MODE}" == "1" ]]; then
  TARGET_DIR="${HOME}/.local/bin"
fi

if [[ ! -f "${ENTRY_PATH}" ]]; then
  echo "Entry file not found: ${ENTRY_PATH}" >&2
  exit 1
fi

if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
  echo "Python executable not found: ${PYTHON_BIN}" >&2
  exit 1
fi

mkdir -p "${TARGET_DIR}"
TARGET_FILE="${TARGET_DIR}/${CMD_NAME}"

if [[ -e "${TARGET_FILE}" && "${FORCE}" != "1" ]]; then
  echo "Target exists: ${TARGET_FILE}" >&2
  echo "Use --force to overwrite." >&2
  exit 1
fi

cat > "${TARGET_FILE}" <<EOF
#!/usr/bin/env bash
exec ${PYTHON_BIN} "${ENTRY_PATH}" "\$@"
EOF

chmod +x "${TARGET_FILE}"

echo "Installed: ${TARGET_FILE}"
if [[ "${TARGET_DIR}" == "${HOME}/.local/bin" ]]; then
  echo "Ensure ~/.local/bin is in PATH:"
  echo '  export PATH="$HOME/.local/bin:$PATH"'
fi
