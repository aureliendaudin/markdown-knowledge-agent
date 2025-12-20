"""Planner-Executor module for query decomposition and structured execution."""
import json
import logging
from datetime import datetime
from typing import Any, Literal, Optional
from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage, SystemMessage
from .base import BaseModule

logger = logging.getLogger(__name__)


class SubTask(BaseModel):
    """Represents a single sub-task in the execution plan."""
    id: int
    description: str
    tool: Optional[str] = None
    parameters: dict = Field(default_factory=dict)
    expected_outcome: str
    dependencies: list[int] = Field(default_factory=list)
    status: Literal["pending", "running", "completed", "failed"] = "pending"
    result: Optional[str] = None
    error: Optional[str] = None


class Plan(BaseModel):
    """Represents the complete execution plan."""
    goal: str
    subtasks: list[SubTask]
    created_at: str
    status: Literal["pending", "executing", "completed", "failed"] = "pending"


class Planner:
    """
    Generates structured execution plans from user queries.
    
    Uses an LLM to decompose complex questions into sequential sub-tasks.
    """
    
    def __init__(self, model, config: dict[str, Any]):
        """
        Initialize the Planner.
        
        Args:
            model: LLM model instance
            config: Configuration dictionary
        """
        self.model = model
        self.config = config
        self.max_subtasks = config.get("max_subtasks", 10)
    
    def generate_plan(self, question: str) -> Plan:
        """
        Generate an execution plan for the given question.
        
        Args:
            question: User's question
            
        Returns:
            Structured Plan object
        """
        logger.info(f"Generating plan for: {question}")
        
        system_prompt = self._build_planner_prompt()
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Question: {question}\n\nGénère un plan structuré au format JSON.")
        ]
        
        try:
            response = self.model.invoke(messages)
            plan_data = self._parse_plan_response(response.content, question)
            plan = Plan(**plan_data)
            
            # Verbose logging of the created plan
            print("\n" + "="*60)
            print(f"📋 PLAN GENERATED: {plan.goal}")
            print("="*60)
            print(f"\n🎯 Objective: {plan.goal}")
            print(f"📊 Total subtasks: {len(plan.subtasks)}\n")
            
            for subtask in plan.subtasks:
                print(f"  [{subtask.id}] {subtask.description}")
                if subtask.tool:
                    print(f"      🔧 Tool: {subtask.tool}")
                    print(f"      📥 Parameters: {subtask.parameters}")
                if subtask.dependencies:
                    print(f"      🔗 Dependencies: {subtask.dependencies}")
                print(f"      ✓ Expected: {subtask.expected_outcome}")
                print()
            
            print("="*60 + "\n")
            
            logger.info(f"Plan generated with {len(plan.subtasks)} sub-tasks")
            return plan
            
        except Exception as e:
            logger.error(f"Failed to generate plan: {e}")
            # Fallback: create a simple single-step plan
            return self._create_fallback_plan(question)
    
    def _build_planner_prompt(self) -> str:
        """Build the system prompt for plan generation."""
        return """Tu es un planificateur expert qui décompose des questions complexes en sous-tâches structurées.

**Objectif**: Générer un plan d'exécution séquentiel pour répondre à la question de l'utilisateur.

**Outils disponibles**:

1. `list_folder(path)`: Lister les fichiers et dossiers dans un chemin
   - Paramètres: path (string, optionnel, défaut="")

2. `search_notes(keyword)`: Chercher des fichiers par NOM/CHEMIN (pas par contenu!)
   - Paramètres: keyword (string, obligatoire)
   - Utiliser pour: Trouver un fichier comme "TODO.md", "PyTorch", etc.
   - Exemple: {"keyword": "TODO"} pour trouver TODO.md

3. `read_note(file_path, max_lines)`: Lire le contenu d'un fichier markdown
   - Paramètres: 
     * file_path (string, obligatoire)
     * max_lines (int, obligatoire, recommandé: 50-100)
   - IMPORTANT: Toujours fournir max_lines (ex: 50, 100)

4. `grep_content(search_term, folder)`: Chercher du TEXTE À L'INTÉRIEUR des fichiers
   - Paramètres:
     * search_term (string, obligatoire)  
     * folder (string, optionnel, défaut="")
   - Utiliser pour: Trouver où un concept/mot est mentionné dans le contenu

**RÈGLES IMPORTANTES**:

🔍 **Chercher un FICHIER par nom** → Utilise `search_notes`
   - Exemple: "Trouve TODO.md" → search_notes(keyword="TODO")
   - Exemple: "Trouve mes notes PyTorch" → search_notes(keyword="PyTorch")

📝 **Chercher du TEXTE dans les fichiers** → Utilise `grep_content`
   - Exemple: "Où est mentionné 'deadline'?" → grep_content(search_term="deadline")

📖 **Lire un fichier** → Utilise `read_note` avec max_lines
   - Exemple: read_note(file_path="TODO.md", max_lines=100)
   - ⚠️  TOUJOURS spécifier max_lines (jamais None ou null)

5. `get_document_structure(file_path)`: Voir la structure (titres) d'un fichier
   - Paramètres: file_path (string, obligatoire)
   - Utiliser pour: Comprendre l'organisation d'un long document avant de lire une section
   - Exemple: get_document_structure("Notes/AI.md")

6. `read_section(file_path, section_title, max_lines)`: Lire UNE SECTION spécifique
   - Paramètres: 
     * file_path (string, obligatoire)
     * section_title (string, obligatoire) - Titre exact ou partiel du header
     * max_lines (int, obligatoire, défaut=50)
   - Utiliser pour: Lire juste ce qui est nécessaire sans charger tout le fichier
   - Exemple: read_section("AI.md", "Introduction", 50)

7. `get_headers_with_preview(file_path, preview_lines)`: Aperçu du contenu
   - Paramètres: file_path (string), preview_lines (int, recommandé 2-5)
   - Utiliser pour: Scanner rapidement le contenu d'un fichier

8. `search_in_headers(keyword, folder)`: Chercher dans les TITRES seulement
   - Paramètres: keyword (string), folder (string, optionnel)
   - Utiliser pour: Trouver des concepts spécifiques mentionnés dans les titres


**Format JSON requis**:
{
  "goal": "Description de l'objectif global",
  "subtasks": [
    {
      "id": 1,
      "description": "Description de la sous-tâche",
      "tool": "nom_outil",
      "parameters": {"param1": "value1"},
      "expected_outcome": "Ce que cette tâche devrait produire",
      "dependencies": []
    }
  ]
}

**Exemples**:

Question: "Trouve ma TODO list et dis-moi ce qui est urgent"
{
  "goal": "Trouver TODO.md et identifier les tâches urgentes",
  "subtasks": [
    {
      "id": 1,
      "description": "Chercher le fichier TODO dans le vault",
      "tool": "search_notes",
      "parameters": {"keyword": "TODO"},
      "expected_outcome": "Chemin vers TODO.md",
      "dependencies": []
    },
    {
      "id": 2,
      "description": "Lire le contenu du fichier TODO",
      "tool": "read_note",
      "parameters": {"file_path": "from_task_1", "max_lines": 100},
      "expected_outcome": "Contenu de la TODO list",
      "dependencies": [1]
    },
    {
      "id": 3,
      "description": "Identifier les tâches urgentes selon les deadlines",
      "tool": null,
      "parameters": {},
      "expected_outcome": "Liste des tâches urgentes",
      "dependencies": [2]
    }
  ]
}

Question: "Trouve mes notes sur PyTorch et résume-les"
{
  "goal": "Trouver et résumer les notes sur PyTorch",
  "subtasks": [
    {
      "id": 1,
      "description": "Chercher les fichiers avec PyTorch dans le nom",
      "tool": "search_notes",
      "parameters": {"keyword": "PyTorch"},
      "expected_outcome": "Liste des fichiers PyTorch",
      "dependencies": []
    },
    {
      "id": 2,
      "description": "Lire le premier fichier trouvé",
      "tool": "read_note",
      "parameters": {"file_path": "from_task_1", "max_lines": 50},
      "expected_outcome": "Contenu du fichier",
      "dependencies": [1]
    },
    {
      "id": 3,
      "description": "Générer un résumé",
      "tool": null,
      "parameters": {},
      "expected_outcome": "Résumé synthétique",
      "dependencies": [2]
    }
  ]
}

Question: "Que dit le cours de ML sur les arbres de décision ?"
{
  "goal": "Trouver la section sur les arbres de décision dans le cours de ML et en extraire le contenu",
  "subtasks": [
    {
      "id": 1,
      "description": "Trouver le fichier du cours de ML",
      "tool": "search_notes",
      "parameters": {"keyword": "Machine Learning"},
      "expected_outcome": "Chemin du fichier (ex: Notes/ML.md)",
      "dependencies": []
    },
    {
      "id": 2,
      "description": "Analyser la structure du document pour trouver la section",
      "tool": "get_document_structure",
      "parameters": {"file_path": "from_task_1"},
      "expected_outcome": "Structure du document avec les titres",
      "dependencies": [1]
    },
    {
      "id": 3,
      "description": "Lire la section spécifique sur les arbres de décision",
      "tool": "read_section",
      "parameters": {"file_path": "from_task_1", "section_title": "Decision Trees", "max_lines": 50},
      "expected_outcome": "Contenu de la section",
      "dependencies": [1]
    }
  ]
}

**RÈGLE CRITIQUE pour les dépendances entre tâches:**
- Pour utiliser le résultat d'une tâche précédente: "from_task_X" où X est l'ID
- Exemple: "file_path": "from_task_1" utilise le résultat de la tâche 1
- NE PAS utiliser: $(task_1), {task_1}, etc.

Réponds UNIQUEMENT avec le JSON, sans markdown ni texte additionnel."""
    
    def _parse_plan_response(self, response: str, question: str) -> dict:
        """Parse the LLM response into a plan dictionary."""
        # Remove markdown code blocks if present
        response = response.strip()
        if response.startswith("```"):
            # Extract content between code fences
            lines = response.split("\n")
            response = "\n".join(lines[1:-1]) if len(lines) > 2 else response
            response = response.replace("```json", "").replace("```", "").strip()
        
        try:
            plan_data = json.loads(response)
            plan_data["created_at"] = datetime.now().isoformat()
            return plan_data
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON plan: {e}. Using fallback.")
            return self._create_fallback_plan(question).model_dump()
    
    def _create_fallback_plan(self, question: str) -> Plan:
        """Create a simple fallback plan when generation fails."""
        return Plan(
            goal=question,
            subtasks=[
                SubTask(
                    id=1,
                    description="Répondre directement à la question",
                    tool=None,
                    expected_outcome="Réponse à la question",
                    dependencies=[]
                )
            ],
            created_at=datetime.now().isoformat(),
            status="pending"
        )


class Executor:
    """
    Executes a structured plan step by step.
    
    Runs sub-tasks sequentially, verifies results, and handles failures.
    """
    
    def __init__(self, model, tools: list, config: dict[str, Any]):
        """
        Initialize the Executor.
        
        Args:
            model: LLM model instance
            tools: List of available tools
            config: Configuration dictionary
        """
        self.model = model
        self.tools = tools
        self.config = config
        self.max_retries = config.get("max_retries_per_task", 2)
        self.verification_mode = config.get("verification_mode", "flexible")
        
        # Build tool lookup
        self.tool_map = {tool.name: tool for tool in tools}
    
    def execute_plan(self, plan: Plan, original_question: str) -> dict[str, Any]:
        """
        Execute the plan and return results.
        
        Args:
            plan: Plan to execute
            original_question: Original user question
            
        Returns:
            Dictionary with execution results
        """
        logger.info(f"Executing plan with {len(plan.subtasks)} sub-tasks")
        plan.status = "executing"
        
        results = {
            "plan": plan,
            "subtask_results": {},
            "final_answer": None,
            "success": False
        }
        
        for subtask in plan.subtasks:
            # Check dependencies
            if not self._check_dependencies(subtask, results["subtask_results"]):
                logger.warning(f"Subtask {subtask.id} dependencies not met")
                subtask.status = "failed"
                subtask.error = "Dependencies not satisfied"
                
                print(f"\n⚠️  SUBTASK {subtask.id} SKIPPED")
                print(f"   Reason: Dependencies not satisfied")
                print("=" * 60)
                
                continue
            
            # Execute subtask
            success = self._execute_subtask(subtask, results["subtask_results"])
            results["subtask_results"][subtask.id] = {
                "description": subtask.description,
                "status": subtask.status,
                "result": subtask.result,
                "error": subtask.error
            }
            
            if not success and subtask.tool is not None:
                logger.warning(f"Subtask {subtask.id} failed: {subtask.error}")
                # In flexible mode, continue; in strict mode, stop
                if self.verification_mode == "strict":
                    plan.status = "failed"
                    break
        
        # Print summary
        print("\n" + "="*60)
        print("📊 EXECUTION SUMMARY")
        print("="*60)
        completed_count = sum(1 for r in results["subtask_results"].values() if r["status"] == "completed")
        failed_count = sum(1 for r in results["subtask_results"].values() if r["status"] == "failed")
        print(f"✅ Completed: {completed_count}/{len(plan.subtasks)}")
        print(f"❌ Failed: {failed_count}/{len(plan.subtasks)}")
        print("="*60 + "\n")
        
        # Generate final answer
        plan.status = "completed"
        results["final_answer"] = self._generate_final_answer(
            plan, results["subtask_results"], original_question
        )
        results["success"] = plan.status == "completed"
        
        return results
    
    def _check_dependencies(self, subtask: SubTask, completed: dict) -> bool:
        """Check if all dependencies are satisfied."""
        for dep_id in subtask.dependencies:
            if dep_id not in completed:
                return False
            if completed[dep_id]["status"] != "completed":
                return False
        return True
    
    def _execute_subtask(self, subtask: SubTask, completed: dict) -> bool:
        """
        Execute a single subtask.
        
        Returns:
            True if successful, False otherwise
        """
        subtask.status = "running"
        
        # Verbose logging at start of subtask
        print(f"\n🔄 EXECUTING SUBTASK {subtask.id}")
        print(f"   Description: {subtask.description}")
        if subtask.tool:
            print(f"   Tool: {subtask.tool}")
        print("-" * 60)
        
        logger.info(f"Executing subtask {subtask.id}: {subtask.description}")
        
        # If no tool specified, use LLM to process based on previous results
        if not subtask.tool:
            try:
                subtask.result = self._process_with_llm(subtask, completed)
                subtask.status = "completed"
                
                # Verbose success logging
                print(f"✅ SUBTASK {subtask.id} COMPLETED")
                print(f"   Result: {subtask.result[:150]}..." if len(subtask.result) > 150 else f"   Result: {subtask.result}")
                print("=" * 60)
                
                return True
            except Exception as e:
                subtask.status = "failed"
                subtask.error = str(e)
                
                # Verbose failure logging
                print(f"❌ SUBTASK {subtask.id} FAILED")
                print(f"   Error: {str(e)}")
                print("=" * 60)
                
                return False
        
        # Execute with tool
        tool = self.tool_map.get(subtask.tool)
        if not tool:
            logger.error(f"Tool not found: {subtask.tool}")
            subtask.status = "failed"
            subtask.error = f"Tool '{subtask.tool}' not available"
            return False
        
        # Resolve parameters from previous tasks
        params = self._resolve_parameters(subtask.parameters, completed)
        
        # Execute tool with retries
        for attempt in range(self.max_retries):
            try:
                result = tool.invoke(params)
                subtask.result = str(result)
                subtask.status = "completed"
                
                # Verbose success logging
                print(f"✅ SUBTASK {subtask.id} COMPLETED")
                print(f"   Result: {subtask.result[:150]}..." if len(subtask.result) > 150 else f"   Result: {subtask.result}")
                print("=" * 60)
                
                logger.info(f"Subtask {subtask.id} completed: {subtask.result[:100]}...")
                return True
            except Exception as e:
                logger.warning(f"Subtask {subtask.id} attempt {attempt + 1} failed: {e}")
                if attempt == self.max_retries - 1:
                    subtask.status = "failed"
                    subtask.error = str(e)
                    
                    # Verbose failure logging
                    print(f"❌ SUBTASK {subtask.id} FAILED")
                    print(f"   Error: {str(e)}")
                    print("=" * 60)
                    
                    return False
        
        return False
    
    def _resolve_parameters(self, params: dict, completed: dict) -> dict:
        """Resolve parameters that reference previous task results."""
        resolved = {}
        for key, value in params.items():
            if isinstance(value, str):
                # Handle from_task_X pattern
                if value.startswith("from_task_"):
                    try:
                        task_id = int(value.replace("from_task_", ""))
                        if task_id in completed:
                            result = completed[task_id]["result"]
                            # Extract first line if multi-line result (for file paths)
                            if "\n" in result:
                                result = result.split("\n")[0].strip()
                            resolved[key] = result
                        else:
                            resolved[key] = value
                    except ValueError:
                        resolved[key] = value
                # Handle other patterns like $(task_X), {task_X}, etc.
                elif "task" in value.lower() and any(c in value for c in ['$', '(', ')', '[', ']', '{', '}']):
                    # Try to extract task ID from various formats
                    import re
                    match = re.search(r'task[_\s]*([0-9]+)', value, re.IGNORECASE)
                    if match:
                        task_id = int(match.group(1))
                        if task_id in completed:
                            result = completed[task_id]["result"]
                            # Extract first line if multi-line result
                            if "\n" in result:
                                result = result.split("\n")[0].strip()
                            resolved[key] = result
                            logger.info(f"Resolved '{value}' to '{result}' from task {task_id}")
                        else:
                            resolved[key] = value
                    else:
                        resolved[key] = value
                else:
                    resolved[key] = value
            else:
                resolved[key] = value
        return resolved
    
    def _process_with_llm(self, subtask: SubTask, completed: dict) -> str:
        """Process subtask using LLM (for tasks without specific tools)."""
        context = "\n".join([
            f"Task {tid}: {data['result']}"
            for tid, data in completed.items()
            if data['status'] == 'completed'
        ])
        
        prompt = f"""Contexte des tâches précédentes:
{context}

Tâche actuelle: {subtask.description}
Résultat attendu: {subtask.expected_outcome}

Génère le résultat pour cette tâche basé sur le contexte."""
        
        response = self.model.invoke([HumanMessage(content=prompt)])
        return response.content
    
    def _generate_final_answer(
        self, plan: Plan, subtask_results: dict, original_question: str
    ) -> str:
        """Generate final answer by synthesizing all subtask results."""
        results_summary = "\n".join([
            f"- Tâche {tid}: {data['description']}\n  Résultat: {data['result'][:200]}..."
            for tid, data in subtask_results.items()
            if data['status'] == 'completed' and data['result']
        ])
        
        prompt = f"""Question originale: {original_question}

Objectif: {plan.goal}

Résultats des sous-tâches:
{results_summary}

Synthétise ces informations pour répondre à la question originale de manière claire et concise."""
        
        try:
            response = self.model.invoke([HumanMessage(content=prompt)])
            return response.content
        except Exception as e:
            logger.error(f"Failed to generate final answer: {e}")
            return f"Exécution terminée avec {len([r for r in subtask_results.values() if r['status'] == 'completed'])} tâches réussies."


class PlannerExecutorModule(BaseModule):
    """
    Module implementing the Planner-Executor pattern.
    
    Separates query planning from execution for better traceability
    and error handling.
    """
    
    def __init__(self, model, tools: list, config: dict[str, Any] | None = None):
        """
        Initialize the Planner-Executor module.
        
        Args:
            model: LLM model instance
            tools: List of available tools
            config: Module configuration
        """
        super().__init__(config)
        self.model = model
        self.tools = tools
        self.planner = Planner(model, self.config)
        self.executor = Executor(model, tools, self.config)
    
    def initialize(self) -> None:
        """Initialize the module."""
        logger.info(f"Initializing {self.name}")
        logger.info(f"Planning mode: max_subtasks={self.config.get('max_subtasks', 10)}")
    
    def process(self, state: dict[str, Any]) -> dict[str, Any]:
        """
        Process a question through planning and execution.
        
        Args:
            state: Current state with 'question' key
            
        Returns:
            Updated state with planning results
        """
        question = state.get("question", "")
        
        # Generate plan
        plan = self.planner.generate_plan(question)
        state["plan"] = plan
        
        # Execute plan
        results = self.executor.execute_plan(plan, question)
        state["planning_results"] = results
        state["answer"] = results["final_answer"]
        
        return state
    
    def ask(self, question: str) -> str:
        """
        Convenience method to ask a question directly.
        
        Args:
            question: User's question
            
        Returns:
            Final answer
        """
        state = {"question": question}
        result_state = self.process(state)
        return result_state.get("answer", "No answer generated")
