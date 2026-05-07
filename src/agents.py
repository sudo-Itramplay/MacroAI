import os
from typing import TypedDict
from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI

# 1. Càrrega de variables
load_dotenv()

# 2. Definició de l'Estat
class AgentState(TypedDict):
    project_requirements: str
    current_task: str
    complexity: str
    generated_code: str

# 3. Inicialització dels Models
claude = ChatAnthropic(
    model="claude-3-5-sonnet-20240620", 
    api_key=os.getenv("ANTHROPIC_API_KEY")
)

kimi = ChatOpenAI(
    model="moonshot-v1-8k", 
    openai_api_key=os.getenv("KIMI_API_KEY"), 
    base_url="https://api.moonshot.cn/v1"
)

open_code_go = ChatOpenAI(
    model="open-code-go", 
    openai_api_key=os.getenv("OPENCODE_API_KEY"), 
    base_url="URL_DEL_TEU_ENDPOINT" # Modifica això amb l'URL real
)

# 4. Funcions dels Nodes
def architect_node(state: AgentState):
    prompt = f"""
    Ets l'Arquitecte del programari. Analitza aquest requisit: {state['project_requirements']}
    1. Defineix la tasca a fer ({state['current_task']}).
    2. Classifica la complexitat estrictament com a "complexa" o "simple".
    Respon NOMÉS amb la paraula de la complexitat a la primera línia, i la descripció de la tasca a la segona.
    """
    response = kimi.invoke(prompt).content.split('\n')
    complexity = response[0].strip().lower()
    task_description = "\n".join(response[1:])
    return {"complexity": complexity, "current_task": task_description}

def claude_coder_node(state: AgentState):
    response = claude.invoke(f"Ets un expert. Resol aquesta tasca complexa: {state['current_task']}")
    return {"generated_code": response.content}

def opencode_coder_node(state: AgentState):
    response = open_code_go.invoke(f"Escriu el codi bàsic per aquesta tasca: {state['current_task']}")
    return {"generated_code": response.content}
