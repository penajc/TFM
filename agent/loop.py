import os
import csv
import time
import logging
from typing import Dict, Any

from dotenv import load_dotenv
from agent.perception import Case, Customer
from agent.memory import MemoriClient
from agent.openai_client import LLMClient
from simulator.rules import SimulatorRules

logger = logging.getLogger("agent.loop")
load_dotenv()


class AgentLoop:
    """
    Implementa el ciclo decisional de 5 fases del agente.
    Cada llamada a run_episode() es una sesión completamente independiente:
    el agente no recibe ningún historial conversacional previo en el prompt.
    La única diferencia entre configuraciones es si MemoriClient está activo.
    """

    def __init__(self,
                 memory_enabled: bool,
                 entity_id:      str,
                 log_path:       str = "logs/simulation_results.csv"):
        self.memory_enabled = memory_enabled
        self.memori         = MemoriClient(entity_id=entity_id,
                                           enabled=memory_enabled)
        self.llm            = LLMClient(memory_enabled=memory_enabled)
        if hasattr(self.llm, "set_entity_id") and memory_enabled:
            self.llm.set_entity_id(entity_id)
        self.simulator      = SimulatorRules()
        self.log_path       = log_path
        self._init_csv()

    def _init_csv(self):
        os.makedirs(os.path.dirname(self.log_path), exist_ok=True)
        if not os.path.exists(self.log_path):
            with open(self.log_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "episode_id", "case_id", "case_type",
                    "customer_tier", "urgency", "category",
                    "decision_agent", "expected_decision",
                    "outcome", "error_type",
                    "decision_time_s", "memories_retrieved_n",
                    "config"
                ])

    def run_episode(self,
                    episode_id: str,
                    case_type:  str,
                    raw_case:   Dict[str, Any]) -> Dict[str, Any]:
        """
        Ejecuta un episodio completo: nueva sesión sin historial previo.
        """
        t0 = time.time()
        config = "with_memory" if self.memory_enabled else "without_memory"
        logger.info(f"\n--- [{config}] EPISODIO {episode_id} ({case_type}) ---")

        # ── FASE 1: Percepción ────────────────────────────────────────────
        case = Case(**raw_case)
        logger.info(f"Fase 1: caso {case.case_id} parseado.")

        # ── FASE 2: Consulta de memoria ───────────────────────────────────
        memories = self.memori.retrieve_context(
            case_description=case.description,
            k=5
        )
        n_mem = len(memories)

        # ── FASE 3: Razonamiento LLM ──────────────────────────────────────
        decision = self.llm.decide(case=case, memories=memories)
        logger.info(f"Fase 3: decisión → {decision.decision.value} | {decision.reason}")

        # ── FASE 4: Evaluación del simulador ──────────────────────────────
        eval_result = self.simulator.evaluate(case, decision.decision)
        outcome      = eval_result["outcome"]
        error_type   = eval_result["error_type"]
        expected     = eval_result["expected"]
        logger.info(f"Fase 4: {outcome.upper()}" +
                    (f" [{error_type}]" if error_type else "") +
                    f" | esperado: {expected}")

        # ── FASE 5: Actualización de memoria y log ────────────────────────
        if self.memory_enabled:
            self.memori.record(
                case_id=case.case_id,
                description=case.description,
                customer_tier=case.customer.customer_tier.value,
                decision=decision.decision.value,
                outcome=outcome
            )

        decision_time = round(time.time() - t0, 4)

        with open(self.log_path, "a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow([
                episode_id, case.case_id, case_type,
                case.customer.customer_tier.value,
                case.urgency.value,
                case.category,
                decision.decision.value, expected,
                outcome, error_type or "N/A",
                decision_time, n_mem,
                config
            ])

        return {
            "episode_id":        episode_id,
            "case_id":           case.case_id,
            "case_type":         case_type,
            "customer_tier":     case.customer.customer_tier.value,
            "decision":          decision.decision.value,
            "expected":          expected,
            "outcome":           outcome,
            "error_type":        error_type,
            "decision_time":     decision_time,
            "memories_retrieved": n_mem,
            "config":            config
        }
