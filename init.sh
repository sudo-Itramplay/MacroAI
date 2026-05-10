#!/usr/bin/env bash
# =============================================================================
# MacroAI — Script d'inicialitzacio i arrancada
# =============================================================================
# Que fa aquest script:
#   1. Comprova que opencode sigui al PATH
#   2. Crea l'entorn virtual Python si no existeix
#   3. Instal·la totes les dependencies (langgraph, textual, etc.)
#   4. Ofereix llançar en mode UI (recomanat) o mode CLI simple
#
# Us:
#   chmod +x init.sh && ./init.sh
# =============================================================================

set -euo pipefail

# --- Colors i helpers ---------------------------------------------------------
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; BOLD='\033[1m'; NC='\033[0m'

ok()   { echo -e "${GREEN}[✓]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }
err()  { echo -e "${RED}[✗]${NC} $1" >&2; }
info() { echo -e "${BLUE}[·]${NC} $1"; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo ""
echo -e "${BOLD}  MacroAI — Sistema Multiagent${NC}"
echo    "  OpenCode CLI  ·  LangGraph  ·  Textual UI"
echo    "  Diversos models via --model (fast + potent)"
echo ""

# =============================================================================
# 1. COMPROVACIO DE PREREQUISITS
# =============================================================================
info "Comprovant binaris CLI necessaris..."

MISSING=0

# opencode: L'unic CLI necessari. Tots els agents (optimizer, architect,
# complex coder, simple coder, finalizer) usen opencode amb models diferents
# via --model provider/model.
if command -v opencode &>/dev/null; then
    ok "opencode  → $(command -v opencode)"
else
    err "opencode NO trobat al PATH."
    warn "Instal·la-lo: npm install -g opencode-ai"
    MISSING=1
fi

if [[ $MISSING -eq 1 ]]; then
    echo ""
    err "opencode no s'ha trobat. Instal·la'l i torna a executar init.sh."
    exit 1
fi

# Comprovacio de la versio de Python (minim 3.10)
if ! command -v python3 &>/dev/null; then
    err "python3 no trobat al PATH."
    exit 1
fi

PY_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
PY_MIN_MAJOR=3; PY_MIN_MINOR=10
PY_MAJOR=$(echo "$PY_VER" | cut -d. -f1)
PY_MINOR=$(echo "$PY_VER" | cut -d. -f2)

if [[ $PY_MAJOR -lt $PY_MIN_MAJOR || ( $PY_MAJOR -eq $PY_MIN_MAJOR && $PY_MINOR -lt $PY_MIN_MINOR ) ]]; then
    err "Python >= ${PY_MIN_MAJOR}.${PY_MIN_MINOR} necessari (tens $PY_VER)."
    exit 1
fi
ok "python3  → $PY_VER"

echo ""

# =============================================================================
# 2. ENTORN VIRTUAL
# =============================================================================
VENV_DIR="$SCRIPT_DIR/venv"

if [[ ! -d "$VENV_DIR" ]]; then
    info "Creant entorn virtual Python a ./venv ..."
    python3 -m venv "$VENV_DIR"
    ok "venv creat"
else
    ok "venv ja existeix"
fi

# Activem el venv per a la resta del script
# shellcheck source=/dev/null
source "$VENV_DIR/bin/activate"
ok "venv activat ($(python --version))"

echo ""

# =============================================================================
# 3. DEPENDENCIES PYTHON
# =============================================================================
info "Actualitzant pip..."
pip install --quiet --upgrade pip

info "Instal·lant dependencies de requirements.txt..."
pip install --quiet -r "$SCRIPT_DIR/requirements.txt"
ok "Dependencies instal·lades:"
pip list 2>/dev/null | grep -E "langgraph|langchain|textual" | while read -r line; do
    echo "       $line"
done

echo ""

# =============================================================================
# 4. CREACIO DE .env (si no existeix)
# =============================================================================
ENV_FILE="$SCRIPT_DIR/.env"
ENV_EXAMPLE="$SCRIPT_DIR/.env.example"

if [[ ! -f "$ENV_FILE" && -f "$ENV_EXAMPLE" ]]; then
    cp "$ENV_EXAMPLE" "$ENV_FILE"
    warn ".env creat a partir de .env.example (no necessari per al funcionament)"
fi

# =============================================================================
# 5. LLANÇAMENT
# =============================================================================
echo -e "${BOLD}  Com vols executar MacroAI?${NC}"
echo ""
echo "  [1]  UI  →  python main_ui.py    (recomanat — interfície visual completa)"
echo "  [2]  CLI →  python src/main.py   (mode terminal minimal)"
echo ""
read -rp "  Opcio [1/2, default=1]: " CHOICE
CHOICE=${CHOICE:-1}

cd "$SCRIPT_DIR"

echo ""
case "$CHOICE" in
    2)
        info "Arrancant en mode CLI..."
        exec python src/main.py
        ;;
    *)
        info "Arrancant la UI Textual..."
        exec python main_ui.py
        ;;
esac
