# MacroAI — Sistema d'Orquestracio Multiagent

Sistema que coordina multiples agents d'IA mitjancant **LangGraph**, automatitzant la planificacio i generacio de codi de forma eficient: cada tasca es delega a l'agent optim segons la seva complexitat.

Tots els agents utilitzen un unic CLI (**opencode**) amb diferents flags `--model` per rol. La seleccio de models es completament configurable via variables d'entorn.

---

## Arquitectura del Sistema

### Pipeline amb bucle de tasques

```
optimizer -> planner -> scaffolder -> executor ─┐
                                    ▲            │
                                    └──┐         │
                                       │         ▼
                              complex ◄─┤  ┌─────────┐
                              simple  ◄─┘  │ finalize│ -> END
                                           └─────────┘
```

| Node | Model | Funcio |
|------|-------|--------|
| **optimizer** | fast (flash) | Refina el requeriment brut de l'usuari a una spec estructurada |
| **planner** | powerful (pro) | Crea el pla complet amb tasques `[COMPLEX]`/`[SIMPLE]` |
| **scaffolder** | cap (deterministic) | Pre-crea directoris i fitxers buits del pla |
| **executor** | cap (deterministic) | Escriu codi generat (Safe mode), marca tasques, despacha la seguent |
| **complex** | powerful (pro) | Codifica tasques complexes: algorismes, logica de negoci, integracions |
| **simple** | fast (flash) | Codifica tasques simples: boilerplate, data classes, config |
| **finalizer** | powerful (pro) | Comprimeix tot el context en un `<MEMORY_DUMP>` i el desa a disc |

### Agents i models per defecte

Tots els agents utilitzen `opencode run --model provider/model`:

| Rol | Variable d'entorn | Model per defecte |
|-----|-------------------|-------------------|
| Optimizer | `MACROAI_OPTIMIZER_MODEL` | `opencode-go/deepseek-v4-flash` |
| Architect | `MACROAI_ARCHITECT_MODEL` | `opencode-go/deepseek-v4-pro` |
| Complex Coder | `MACROAI_COMPLEX_MODEL` | `opencode-go/deepseek-v4-pro` |
| Simple Coder | `MACROAI_SIMPLE_MODEL` | `opencode-go/deepseek-v4-flash` |
| Finalizer | `MACROAI_FINALIZER_MODEL` | `opencode-go/kimi-K2.6` |

### Estat compartit (AgentState)

Els nodes es comuniquen a traves d'un diccionari compartit que LangGraph passa de node en node:

| Camp | Descripcio |
|------|------------|
| `project_requirements` | Requeriment de l'usuari (optimitzat pel node `optimizer`) |
| `current_task` | Descripcio de la tasca actualment en codificacio |
| `complexity` | `"complexa"` (-> complex coder) o `"simple"` (-> simple coder) |
| `generated_code` | Codi produït pel codificador actiu (mode Safe) |
| `session_id` | Identificador de sessio; permet projectes paral·lels |
| `memory_context` | Memoria comprimida de sessions anteriors |
| `plan_md` | Pla complet en markdown amb les tasques `[COMPLEX]`/`[SIMPLE]` |
| `task_index` | Posicio actual a la llista de tasques |
| `total_tasks` | Nombre total de tasques del pla |
| `target_file` | Ruta relativa del fitxer a generar |
| `output_dir` | Ruta absoluta al directori de sortida del projecte |

### Persistencia de memoria entre sessions

Cada execucio acaba amb el node `finalize` que demana a un model powerful que produeixi un `<MEMORY_DUMP>` estructurat. El dump s'escriu a `.macroai_memory/<session_id>.md` i es carrega automaticament a la propera execucio, fent el sistema **stateful** malgrat que cada crida CLI sigui un proces independent.

### Modes de permisos (Safe / Auto)

| Mode | Comportament | Indicador UI |
|------|-------------|--------------|
| **Safe** (defecte) | opencode retorna codi com a text; l'executor escriu el fitxer | `[SAFE]` verd |
| **Auto** | opencode escriu fitxers directament amb la seva eina nativa | `[AUTO]` vermell |

Canvia entre modes amb la tecla `a` a la UI.

---

## SOLID Map

| Principi | On |
|----------|-----|
| **S** (SRP) | `OpenCodeClient` te una sola rao de canviar: la interficie CLI de opencode. `MemoryStore` encapsula tota la persistencia. |
| **O** (OCP) | `AgentFactory` obert per extensio (nous rols/models) tancat per modificacio. |
| **L** (LSP) | Qualsevol implementacio d'`AgentClient` pot substituir una altra transparentment. |
| **I** (ISP) | `AgentClient` nomes exposa `run(prompt, session_id, files, cwd)`. |
| **D** (DIP) | Els nodes reben `AgentClient` i `MemoryStore` via injeccio, no importen wrappers concrets. |

---

## Estructura del Projecte

```
MacroAI/
├── src/
│   ├── clients.py      # AgentClient ABC, OpenCodeClient, ModelConfig, AgentFactory
│   ├── agents.py       # AgentState, MemoryStore, plan parser, node factories
│   ├── graph.py        # StateGraph de LangGraph, route_next(), build_graph()
│   └── main.py         # Punt d'entrada CLI (sense UI)
├── ui/
│   ├── app.py          # MacroAIApp: layout Textual, worker async, polling de cues
│   ├── runner.py       # GraphRunner: pont asyncio <-> ThreadPoolExecutor
│   └── widgets/
│       ├── project_panel.py  # Llista de sessions, crear-ne de noves
│       ├── log_panel.py      # Log en temps real amb colors per agent + copy (c)
│       ├── state_panel.py    # Visualitzador del pipeline (nodes completats)
│       └── result_panel.py   # Codi generat amb ressaltat de sintaxi
├── tests/
│   ├── test_modes.py       # Proves dels modes Safe/Auto i configuracio CLI
│   ├── test_router.py      # Proves del router de complexitat
│   └── test_scaffolder.py  # Proves del node scaffolder
├── .macroai_memory/    # Memoria de sessio (gitignored)
├── main_ui.py          # Punt d'entrada UI: python main_ui.py
├── init.sh             # Script d'instalacio i arrancada
└── requirements.txt    # langgraph + langchain-core + textual
```

---

## Instalacio i arrancada

### Prerequisits del sistema

Assegura't de tenir instal·lats i accessibles via `$PATH`:

- `opencode` — [OpenCode](https://opencode.ai)
- `python3 >= 3.10`

També necesites configurar la clau API:
```bash
export OPENCODE_API_KEY="la-teva-clau"
```

### Instalacio amb init.sh (recomanat)

```bash
chmod +x init.sh && ./init.sh
```

El script fa automaticament:
1. Comprova que `opencode` sigui al PATH
2. Crea i activa un entorn virtual Python a `./venv`
3. Instal·la les dependencies de `requirements.txt`
4. Ofereix escollir entre **UI** (recomanat) i **CLI simple**

### Instalacio manual

```bash
python3 -m venv venv
source venv/bin/activate        # Linux/macOS
pip install -r requirements.txt
```

### Dependencies Python

```
langgraph>=0.2
langchain-core>=0.3
textual>=0.70
```

---

## Execucio

### Mode UI (recomanat)

```bash
source venv/bin/activate
python main_ui.py
```

La UI Textual mostra tres panells:
- **Esquerra**: Llista de sessions (`.macroai_memory/`), creacio de noves
- **Centre**: Pipeline de progres, camp d'entrada del requeriment, log en temps real
- **Dreta**: Codi generat amb ressaltat de sintaxi Python

Dreceres de teclat:

| Tecla | Accio |
|-------|-------|
| `Ctrl+R` | Executar el graf |
| `Ctrl+L` | Netejar log |
| `a` | Toggle Safe/Auto mode |
| `c` | Copiar log al clipboard |
| `Q` | Sortir |

### Mode CLI (minimal)

```bash
source venv/bin/activate
python src/main.py
```

Per defecte usa la sessio `macroai-session`. Edita `session_id` a `src/main.py` per treballar en sessions paral·lels.

### Projectes multiples (sessions paral·lels)

Cada `session_id` te el seu propi fitxer de memoria independent:

```
.macroai_memory/
├── macroai-session.md    # projecte principal
├── api-refactor.md       # refactoring paral·lel
└── bugfix-auth.md        # correccio d'error
```

---

## Desenvolupament i qualitat

```bash
# Linter
ruff check .

# Analisi de seguretat
bandit -r . -ll -ii

# Proves (des del venv)
./venv/bin/python -m pytest tests/ -v
```

---

> **Seguretat**: `.macroai_memory/` es ignorat al `.gitignore`. No el pugis mai a un repositori public si conte informacio sensible del projecte.
