# MultiAgent Coder: Sistema d'Orquestració amb LangGraph

Aquest projecte implementa un sistema multiagent heterogeni utilitzant **LangGraph**. Aprofita els punts forts de diferents Models de Llenguatge Gran (LLMs) per automatitzar la planificació i generació de codi de manera eficient i econòmica, delegant tasques segons la seva complexitat.

L'arquitectura actual **no requereix claus API**. En lloc de cridar serveis en núvol via SDK, invoca directament els intèrprets de línia de comandes (CLI) que ja tens instal·lats al sistema: **Kimi**, **Claude** i **OpenCode**. Això elimina quotes, latència de xarxa innecessària i la gestió de secrets.

---

## 🏛️ Arquitectura del Sistema

El sistema es basa en un patró de **Delegació Condicional** mitjançant un Graf d'Estats (*StateGraph*). El cicle de vida d'una petició flueix a través de l'orquestrador, es deriva al programador òptim i finalment es preserva la memòria de sessió per a execucions futures.

### Rol dels Agents

1. **L'Arquitecte (Kimi — CLI):** Llegeix el context global del projecte (incloent memòria de sessions anteriors), defineix la tasca atòmica actual i n'avalua la complexitat taxonòmica (`simple` o `complexa`). **Mai** escriu codi, només planifica.
2. **El Programador Avançat (Claude — CLI):** S'encarrega exclusivament de tasques classificades com a `complexa`. Resol algorismes, lògica de negoci principal i integracions difícils.
3. **El Programador Bàsic (OpenCode — CLI):** S'encarrega de tasques classificades com a `simple`. Redacta codi repetitiu, estructures de dades bàsiques i *boilerplate*.
4. **L'Arxiver de Memòria (Kimi — CLI):** Executat sempre al final. Comprimeix tot el context de treball en un paquet dens (`<MEMORY_DUMP>`) que permet reprendre el projecte després sense perdre estat.

### Flux de l'Estat (AgentState)

Els agents es comuniquen a través d'un estat compartit estricte:

| Camp | Descripció |
|------|------------|
| `project_requirements` | Descripció general del projecte. |
| `current_task` | La tasca atòmica deduïda per l'Arquitecte. |
| `complexity` | Veredicte de l'Arquitecte (`simple` \| `complexa`). |
| `generated_code` | El resultat final redactat pels programadors. |
| `session_id` | Identificador de sessió (ex: `macroai-session`). Permet contexts paral·lels. |
| `memory_context` | Memòria comprimida de sessions anteriors, injectada a cada prompt. |

### Comunicació amb els LLMs (Subprocessos)

En lloc de SDKs amb claus API, es fan crides directes als binaris CLI:

| Agente | Crida CLI | Flag de sessió | Comportament |
|--------|-----------|----------------|--------------|
| **Kimi** (Arquitecte) | `kimi --quiet --afk --prompt "..."` | `--session <id>` | Missatge final només, aprovació automàtica, sessió nativa. |
| **Claude** (Complex) | `claude --print -p "..."` | *via prompt* | Sortida no interactiva. La memòria es injecta directament al prompt perquè el CLI de Claude no exposa sessió nativa en aquesta versió. |
| **OpenCode** (Simple) | `opencode run "missatge"` | `--session <id>` | No interactiva per defecte, sessió nativa. |

### Persistència de Memòria

Cada execució acaba amb un **node finalitzador** que demana a Kimi que generi un `<MEMORY_DUMP>`. Aquest paquet inclou:

- `[PROJECT_STATE]` — fitxers actius, decisions d'arquitectura, components inacabats.
- `[TASK_STACK]` — tasques fetes, en progrés i pendents.
- `[KEY_DECISIONS]` — decisions importants amb la seva justificació.
- `[SCRATCHPAD]` — notes de depuració, hipòtesis i callejons sense sortida.
- `[NEXT_ACTION]` — el següent pas prioritari.

El dump es desa a `.macroai_memory/<session_id>.md` i es carrega automàticament en la següent execució, fent que el sistema sigui **stateful** malgrat que cada crida CLI sigui un procés independent.

---

## 📂 Estructura del Projecte

```text
multiagent-coder/
├── .github/
│   └── workflows/
│       └── ci.yml              # Integració contínua (Ruff, Bandit, Pytest)
├── src/
│   ├── agents.py               # Estat, wrappers CLI i gestió de memòria
│   ├── graph.py                # Màquina d'estats i lògica d'enrutament
│   └── main.py                 # Punt d'entrada amb càrrega de memòria
├── tests/
│   ├── __init__.py
│   └── test_router.py          # Proves unitàries de decisions d'enrutament
├── .macroai_memory/            # Memòria de sessió (gitignored)
├── .env.example                # Plantilla legacy (no necessari)
├── .gitignore
├── requirements.txt            # Només langgraph + langchain-core
├── CHANGELOG.md                # Historial de canvis
└── README.md                   # Aquest document
```

---

## ⚙️ Configuració i Instal·lació

### Requisits Previs

Assegura't de tenir instal·lats i accessibles via `$PATH`:

- `kimi` — [Kimi CLI](https://www.moonshot.cn/)
- `claude` — [Claude Code CLI](https://docs.anthropic.com/en/docs/agents-and-tools/claude-code/overview)
- `opencode` — [OpenCode CLI](https://github.com/opencode-ai/opencode)

### 1. Clonar el repositori

```bash
git clone <URL_DEL_TEU_REPOSITORI>
cd multiagent-coder
```

### 2. Crear i Activar l'Entorn Virtual (venv)

**En Linux / macOS:**
```bash
python3 -m venv venv
source venv/bin/activate
```

**En Windows:**
```bash
python -m venv venv
.\venv\Scripts\activate
```

### 3. Instal·lació de Dependències

Ara només es necessiten dues llibreries de LangGraph:

```bash
pip install -r requirements.txt
```

Contingut de `requirements.txt`:
```text
langgraph>=0.2
langchain-core>=0.3
```

> **Nota:** No calen claus API, fitxers `.env`, ni SDKs de proveïdors. Els agents consumeixen les teves sessions CLI locals ja pagades.

---

## 🚀 Execució

### Execució bàsica

```bash
python src/main.py
```

Per defecte utilitza la sessió `macroai-session`. En la primera execució la memòria estarà buida; en execucions posteriors carregarà automàticament el context acumulat.

### Canviar de sessió (projectes paral·lels)

Edita `src/main.py` o passa un argument (si estàs ampliant el codi):

```python
session_id = "projecte-alpha"   # o "projecte-beta", "bugfix-123", etc.
```

Cada `session_id` té el seu propi fitxer `.macroai_memory/<session_id>.md`, així que pots treballar en múltiples projectes sense que la memòria es barregi.

### Visualitzar la memòria actual

```bash
cat .macroai_memory/macroai-session.md
```

---

## 🧪 Desenvolupament, Qualitat i Proves

Abans de fer un *push*, executa localment dins del teu `venv`:

**1. Analitzador d'Estil (Linter):**
```bash
ruff check src/
```

**2. Anàlisi de Seguretat:**
```bash
bandit -r src/ -ll -ii
```

**3. Proves Unitàries:**
```bash
pytest tests/ -v
```

---

## 📝 Canvis Recents

Vegeu [CHANGELOG.md](./CHANGELOG.md) per a un detall complet de la migració des de l'arquitectura amb claus API fins a la nova arquitectura basada en subprocessos CLI amb memòria persistent.

---

> *Avis de Seguretat: El directori `.macroai_memory/` està ignorat a `.gitignore`. No el puguis mai a un repositori públic si conté informació sensible del teu projecte.*
