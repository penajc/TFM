import logging
from typing import List, Dict, Any
from memori import Memori

logger = logging.getLogger("agent.memory")


class MemoriClient:
    """
    Adaptador sobre el SDK oficial de Memori Labs.
    Usa un entity_id único por ejecución para garantizar que cada experimento
    comience con una memoria limpia y no exista contaminación entre runs.
    """

    def __init__(self, entity_id: str, enabled: bool = True):
        self.enabled  = enabled
        self.entity_id = entity_id
        if self.enabled:
            logger.info(f"Memori: memoria ACTIVA — entidad '{entity_id}'")
        else:
            logger.info("Memori: memoria DESACTIVADA (configuración de control)")

    def retrieve_context(self,
                         case_description: str,
                         k: int = 5) -> List[Dict[str, Any]]:
        """
        Consulta Memori para recuperar recuerdos semánticamente similares.
        Devuelve lista vacía si la memoria está desactivada.
        """
        if not self.enabled:
            return []
        try:
            sdk = Memori()
            sdk.attribution(entity_id=self.entity_id,
                            process_id="tfm-support-agent")
            results  = sdk.recall(query=case_description, limit=k)
            memories = []
            for r in results:
                fact = getattr(r, "fact", str(r))
                memories.append({"fact": fact})
            logger.info(f"Memori: {len(memories)} recuerdos recuperados.")
            return memories
        except Exception as e:
            logger.error(f"Memori retrieve error: {e}")
            return []

    def record(self,
               case_id:       str,
               description:   str,
               customer_tier: str,
               decision:      str,
               outcome:       str):
        """
        Registra el episodio completo (descripción + decisión + resultado)
        en Memori para aprendizaje futuro.
        """
        if not self.enabled:
            return
        try:
            sdk = Memori()
            sdk.attribution(entity_id=self.entity_id,
                            process_id="tfm-support-agent")

            feedback = (
                f"Caso {case_id} | Cliente {customer_tier} | "
                f"Descripción: '{description}' | "
                f"Decisión tomada: {decision} | "
                f"Resultado: {outcome.upper()}."
            )
            sdk.agent_feedback(feedback)
            sdk.capture_agent_turn(
                user_content=description,
                assistant_content=(
                    f"Decisión: {decision}. "
                    f"Resultado: {outcome.upper()}. "
                    f"Cliente: {customer_tier}."
                ),
                project_id="tfm-support-agent",
                session_id=case_id
            )
            logger.info(f"Memori: episodio {case_id} registrado.")
        except Exception as e:
            logger.error(f"Memori record error: {e}")
