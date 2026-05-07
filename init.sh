#!/usr/bin/env bash
# =============================================================================
# MacroAI — Script d'inicialització i arrancada
# =============================================================================
# Que fa aquest script:
#   1. Comprova que els tres CLIs (kimi, claude, opencode) siguin al PATH
#   2. Crea l'entorn virtual Python si no existeix
#   3. Instal·la totes les dependències (langgraph, textual, etc.)
#   4. Ofereix llançar en mode UI (recomanat) o mode CLI simple
#
# Ús:
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
echo    "  Kimi CLI  ·  Claude CLI  ·  OpenCode CLI"
echo    "  Orquestrat amb LangGraph + UI Textual"
echo ""

# =============================================================================
# 1. COMPROVACIÓ DE PREREQUISITS
# =============================================================================
info "Comprovant binaris CLI necessaris..."

MISSING=0

# kimi: Arquitecte i Memory Archivist. Mode CLI exclusiu.
# L'ACP server (kimi acp) existeix però té opcions limitades;
# l'invoquem sempre com a subprocés directe.
if command -v kimi &>/dev/null; then
    ok "kimi     → $(command -v kimi)"
else
    err "kimi NO trobat al PATH."
    warn "Instal·la-lo des de: https://moonshotai.github.io/kimi-cli/"
    MISSING=1
fi

# claude: Codificador avançat. Mode CLI exclusiu (--print -p).
# No té API disponible en aquest entorn; interacció via subprocés.
if command -v claude &>/dev/null; then
    ok "claude   → $(command -v claude)"
else
    err "claude NO trobat al PATH."
    warn "Instal·la-lo: npm install -g @anthropic-ai/claude-code"
    MISSING=1
fi

# opencode: Optimitzador de prompts i codificador simple.
# NOTA SOBRE L'API: opencode suporta dues modalitats d'interacció:
#   a) CLI:        opencode run "missatge"    ← usem aquesta (simple, fiable)
#   b) ACP server: opencode acp --port XXXX  ← disponible però no necessària
#      L'SDK Python (acp-sdk>=1.0) permet connectar-se al servidor ACP,
#      però el overhead de gestionar el cicle de vida del servidor no
#      compensa per a tasques puntuals. El mode CLI és suficient.
if command -v opencode &>/dev/null; then
    ok "opencode → $(command -v opencode)"
else
    err "opencode NO trobat al PATH."
    warn "Instal·la-lo: npm install -g opencode-ai"
    MISSING=1
fi

if [[ $MISSING -eq 1 ]]; then
    echo ""
    err "Un o més CLIs no s'han trobat. Instal·la'ls i torna a executar init.sh."
    exit 1
fi

# Comprovació de la versió de Python (mínim 3.10)
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
# 3. DEPENDÈNCIES PYTHON
# =============================================================================
info "Actualitzant pip..."
pip install --quiet --upgrade pip

info "Instal·lant dependències de requirements.txt..."
pip install --quiet -r "$SCRIPT_DIR/requirements.txt"
ok "Dependències instal·lades:"
pip list 2>/dev/null | grep -E "langgraph|langchain|textual" | while read -r line; do
    echo "       $line"
done

echo ""

# =============================================================================
# 4. CREACIÓ DE .env (si no existeix)
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
read -rp "  Opció [1/2, default=1]: " CHOICE
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
