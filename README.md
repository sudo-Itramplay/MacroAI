# MultiAgent Coder: Sistema d'Orquestració amb LangGraph

Aquest projecte implementa un sistema multiagent heterogeni utilitzant **LangGraph**. Aprofita els punts forts de diferents Models de Llenguatge Gran (LLMs) per automatitzar la planificació i generació de codi de manera eficient i econòmica, delegant tasques segons la seva complexitat.

---

## 🏛️ Arquitectura del Sistema

El sistema es basa en un patró de **Delegació Condicional** mitjançant un Graf d'Estats (*StateGraph*). El cicle de vida d'una petició flueix a través de l'orquestrador i es deriva al programador òptim.

### Rol dels Agents
1. **L'Arquitecte (Kimi - Moonshot 8k):** Llegeix el context global del projecte, defineix la tasca atòmica actual i n'avalua la complexitat taxonòmica (`simple` o `complexa`). **Mai** escriu codi, només planifica.
2. **El Programador Avançat (Claude 3.5 Sonnet):** S'encarrega exclusivament de tasques classificades com a `complexa`. Resol algorismes, lògica de negoci principal i integracions difícils.
3. **El Programador Bàsic (Open Code Go):** S'encarrega de tasques classificades com a `simple`. Redacta codi repetitiu, estructures de dades bàsiques i *boilerplate*.

### Flux de l'Estat (AgentState)
Els agents es comuniquen a través d'un estat compartit estricte:
* `project_requirements`: Descripció general del projecte.
* `current_task`: La tasca atòmica deduïda per l'Arquitecte.
* `complexity`: Veredicte de l'Arquitecte (`simple` | `complexa`).
* `generated_code`: El resultat final redactat pels programadors.

---

## 📂 Estructura del Projecte
```text
multiagent-coder/
├── .github/
│   └── workflows/
│       └── ci.yml          # Integració contínua (Ruff, Bandit, Pytest)
├── src/
│   ├── agents.py           # Definició de l'Estat i connexió amb LLMs
│   ├── graph.py            # Màquina d'estats i lògica d'enrutament
│   └── main.py             # Punt d'entrada de l'aplicació
├── tests/
│   ├── __init__.py
│   └── test_router.py      # Proves unitàries de decisions d'enrutament
├── .env.example            # Plantilla per a les variables d'entorn
├── .gitignore              # Exclusions per a Git
└── README.md               # Aquest document
```

---

## ⚙️ Configuració i Instal·lació

Per començar a treballar amb el projecte des de zero, segueix aquests passos estrictament.

### 1. Clonar el repositori
```bash
git clone <URL_DEL_TEU_REPOSITORI>
cd multiagent-coder
```

### 2. Crear i Activar l'Entorn Virtual (venv)
És imperatiu aïllar les dependències del projecte per evitar conflictes amb el teu sistema operatiu.

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
*(Nota: Sabràs que l'entorn està activat perquè veuràs `(venv)` a l'inici de la línia de la teva terminal).*

### 3. Instal·lació de Dependències
Aquest projecte utilitza el gestor de paquets **Omarchy**. Amb l'entorn virtual activat, executa la següent ordre per instal·lar les llibreries del nucli i de qualitat del codi:
```bash
omarchy install langchain-core langchain-anthropic langchain-openai langgraph python-dotenv ruff bandit pytest pytest-mock
```

### 4. Configuració de les Claus API (Secrets)
El projecte utilitza variables d'entorn per ocultar la informació sensible.
1. Copia l'estructura de l'arxiu d'exemple per crear el teu fitxer d'entorn real:
   ```bash
   cp .env.example .env
   ```
2. Obre l'arxiu `.env` amb el teu editor de text i introdueix les teves claus:
   ```env
   ANTHROPIC_API_KEY=la_teva_clau_claude_aqui
   KIMI_API_KEY=la_teva_clau_moonshot_aqui
   OPENCODE_API_KEY=la_teva_clau_opencode_aqui
   ```
*(Avís de Seguretat: El fitxer `.env` està ignorat a `.gitignore` i **mai** s'ha de pujar a un repositori públic).*

---

## 🚀 Execució

Un cop configurat l'entorn i les claus API, pots iniciar el sistema executant el punt d'entrada principal. Aquest script carregarà el graf, passarà l'estat inicial a l'Arquitecte Kimi i començarà el cicle.
```bash
python src/main.py
```

---

## 🧪 Desenvolupament, Qualitat i Proves

El repositori està configurat amb eines d'anàlisi estàtica i proves unitàries, automatitzades via GitHub Actions per assegurar un codi net i segur. Abans de fer un *push*, s'espera que executis localment les següents ordres dins del teu `venv`:

**1. Analitzador d'Estil (Linter):**
Revisa que el codi segueixi els estàndards PEP-8.
```bash
ruff check src/
```

**2. Anàlisi de Seguretat:**
Busca vulnerabilitats comunes de codi en l'arquitectura de Python.
```bash
bandit -r src/ -ll -ii
```

**3. Proves Unitàries:**
Comprova la integritat de la lògica d'enrutament sense consumir quota d'API.
```bash
pytest tests/ -v
```

````https://github.com/sudo-Itramplay/MacroAI#
