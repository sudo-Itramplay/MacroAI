# MacroAI — Sistema d'Orquestració Multiagent

Sistema que coordina tres agents d'IA heterogenis mitjançant **LangGraph**, automatitzant la planificació i generació de codi de forma econòmica: cada tasca es delega a l'agent òptim segons la seva complexitat.

L'arquitectura **no requereix claus API**. Invoca directament els binaris CLI que ja tens instal·lats al sistema com a subprocessos Python. Això elimina quotes, latència de xarxa innecessària i la gestió de secrets.

---

## Arquitectura del Sistema

### Agents i la seva modalitat d'interacció

| Agent | Rol | Modalitat | Comandament |
|---|---|---|---|
| **Kimi** | Arquitecte + Memory Archivist | **CLI exclusiu** | `kimi --quiet --afk --session <id> --prompt "..."` |
| **Claude** | Codificador avançat | **CLI exclusiu** | `claude --print -p "..."` |
| **OpenCode** | Optimitzador + Codificador simple | **CLI** (`opencode run`) | `opencode run "..."` |

**Per què CLI i no API per a Kimi i Claude?**
Kimi i Claude no disposen d'API accessible en aquest entorn. Funcionen exclusivament com a binaris locals invocats via `subprocess.run()`. Són completament independents d'OpenCode; el codi Python és l'únic orquestrador.

**Nota sobre l'API d'OpenCode:**
OpenCode suporta dues modalitats:
- `opencode run "missatge"` — CLI directe, usat per MacroAI.
- `opencode acp --port XXXX` — servidor ACP (Agent Client Protocol); el SDK Python `acp-sdk>=1.0` permet connectar-s'hi via HTTP. Útil si es volen eliminar els cold starts en crides molt freqüents, però afegeix overhead de gestió de servidor. El CLI és suficient i més simple per a l'ús actual.

### Nodes del pipeline (LangGraph)

```
┌───────────┐    ┌───────────┐    ┌──────────────────────┐    ┌──────────┐
│ optimizer │ ─► │ architect │ ─► │ claude  OR  opencode  │ ─► │ finalize │
│ (OpenCode)│    │  (Kimi)   │    │ (per complexitat)     │    │  (Kimi)  │
└───────────┘    └───────────┘    └──────────────────────┘    └──────────┘
```

| Node | Agent | Funció |
|---|---|---|
| `optimizer` | OpenCode | Tradueix el requeriment brut de l'usuari a una especificació estructurada |
| `architect` | Kimi | Planifica la tasca atòmica i classifica la complexitat (`simple` / `complexa`) |
| `claude` | Claude | Codifica tasques `complexa`: algorismes, lògica de negoci, integracions difícils |
| `opencode` | OpenCode | Codifica tasques `simple`: boilerplate, estructures de dades, codi repetitiu |
| `finalize` | Kimi | Comprimeix tot el context en un `<MEMORY_DUMP>` i el desa a disc |

### Estat compartit (AgentState)

Els nodes es comuniquen a través d'un diccionari compartit que LangGraph passa de node en node:

| Camp | Descripció |
|---|---|
| `project_requirements` | Requeriment de l'usuari (optimitzat pel node `optimizer`) |
| `current_task` | Tasca atòmica decidida per l'Arquitecte |
| `complexity` | `simple` (→ OpenCode) o `complexa` (→ Claude) |
| `generated_code` | Codi produït pel codificador actiu |
| `session_id` | Identificador de sessió; permet projectes paral·lels |
| `memory_context` | Memòria comprimida de sessions anteriors |

### Persistència de memòria entre sessions

Cada execució acaba amb el node `finalize` que demana a Kimi que produeixi un `<MEMORY_DUMP>` estructurat. El dump s'escriu a `.macroai_memory/<session_id>.md` i es carrega automàticament a la propera execució, fent el sistema **stateful** malgrat que cada crida CLI sigui un procés independent.

El format del dump inclou seccions especialitzades per agent:
- `[TASK_STACK]` amb tasques etiquetades `[CLAUDE]` o `[OPENCODE]`
- `[NEXT_ACTION]` amb `Target`, `Files` i `Signature` explícits

---

## Estructura del Projecte

```
MacroAI/
├── src/
│   ├── agents.py       # Estat, wrappers CLI, log sink, nodes del pipeline
│   ├── graph.py        # StateGraph de LangGraph i lògica d'enrutament
│   └── main.py         # Punt d'entrada CLI (sense UI)
├── ui/
│   ├── app.py          # MacroAIApp: layout Textual, worker async, polling de cues
│   ├── runner.py       # GraphRunner: pont asyncio ↔ ThreadPoolExecutor
│   └── widgets/
│       ├── project_panel.py  # Llista de sessions, crear-ne de noves
│       ├── log_panel.py      # Log en temps real amb colors per agent
│       ├── state_panel.py    # Visualitzador del pipeline (nodes completats)
│       └── result_panel.py   # Codi generat amb ressaltat de sintaxi
├── tests/
│   └── test_router.py  # Proves unitàries del router de complexitat
├── .macroai_memory/    # Memòria de sessió (gitignored)
├── main_ui.py          # Punt d'entrada UI: python main_ui.py
├── init.sh             # Script d'instal·lació i arrancada
└── requirements.txt    # langgraph + langchain-core + textual
```

---

## Instal·lació i arrancada

### Prerequisits del sistema

Assegura't de tenir instal·lats i accessibles via `$PATH`:

- `kimi` — [Kimi CLI](https://moonshotai.github.io/kimi-cli/)
- `claude` — [Claude Code CLI](https://docs.anthropic.com/en/docs/agents-and-tools/claude-code/overview) — `npm install -g @anthropic-ai/claude-code`
- `opencode` — [OpenCode](https://opencode.ai) — `npm install -g opencode-ai`
- `python3 >= 3.10`

### Instal·lació amb init.sh (recomanat)

```bash
chmod +x init.sh && ./init.sh
```

El script fa automàticament:
1. Comprova que els tres CLIs siguin al PATH (atura si en falta algun)
2. Crea i activa un entorn virtual Python a `./venv`
3. Instal·la les dependències de `requirements.txt`
4. Ofereix escollir entre **UI** (recomanat) i **CLI simple**

### Instal·lació manual

```bash
python3 -m venv venv
source venv/bin/activate        # Linux/macOS
# o: .\venv\Scripts\activate    # Windows
pip install -r requirements.txt
```

### Dependències Python

```
langgraph>=0.2
langchain-core>=0.3
textual>=0.70
```

---

## Execució

### Mode UI (recomanat)

```bash
source venv/bin/activate
python main_ui.py
```

La UI Textual mostra tres panells:
- **Esquerra**: Llista de sessions (`.macroai_memory/`), creació de noves
- **Centre**: Pipeline de progrés, camp d'entrada del requeriment, log en temps real
- **Dreta**: Codi generat amb ressaltat de sintaxi Python

Dreceres de teclat: `Ctrl+R` executar · `Ctrl+L` netejar log · `Q` sortir.

### Mode CLI (minimal)

```bash
source venv/bin/activate
python src/main.py
```

Per defecte usa la sessió `macroai-session`. Edita `session_id` a `src/main.py` per treballar en sessions paral·leles.

### Projectes múltiples (sessions paral·leles)

Cada `session_id` té el seu propi fitxer de memòria independent:

```
.macroai_memory/
├── macroai-session.md    # projecte principal
├── api-refactor.md       # refactoring paral·lel
└── bugfix-auth.md        # correcció d'error
```

---

## Desenvolupament i qualitat

```bash
# Linter
ruff check src/ ui/

# Anàlisi de seguretat
bandit -r src/ ui/ -ll -ii

# Proves unitàries
pytest tests/ -v
```

---

> **Seguretat**: `.macroai_memory/` és ignorat al `.gitignore`. No el pugis mai a un repositori públic si conté informació sensible del projecte.
