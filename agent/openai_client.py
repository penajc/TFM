import os
import re
import json
import time
import logging
from dotenv import load_dotenv
from openai import OpenAI
from memori import Memori
from agent.perception import Case, AgentDecision, DecisionType

logger = logging.getLogger("agent.llm")
load_dotenv()

SYSTEM_BASE = """Eres un agente de decisión automatizado para soporte al cliente.
Evalúa el caso y selecciona exactamente UNA de estas acciones:
- A1: Reembolso o compensación directa
- A2: Escalar a soporte de nivel superior
- A3: Respuesta estándar con base de conocimiento
- A4: Rechazar o cerrar sin acción

Responde SOLO con un objeto JSON válido, sin texto adicional:
{"decision": "A1"|"A2"|"A3"|"A4", "reason": "justificación breve"}"""


class LLMClient:
    def __init__(self, memory_enabled: bool = True):
        # Soporta claves genéricas, de NVIDIA NIM o de Hugging Face
        self.llm_key   = os.getenv("LLM_API_KEY") or os.getenv("NVIDIA_API_KEY") or os.getenv("HUGGINGFACE_API_KEY", "")
        self.llm_model = os.getenv("LLM_MODEL") or os.getenv("HF_MODEL", "qwen/qwen3-next-80b-a3b-instruct")
        self.base_url  = os.getenv("LLM_BASE_URL") or os.getenv("HF_BASE_URL", "https://integrate.api.nvidia.com/v1")
        self.mem_key   = os.getenv("MEMORI_API_KEY", "")

        if not self.llm_key or "your_" in self.llm_key.lower():
            raise ValueError("API Key del LLM (LLM_API_KEY / NVIDIA_API_KEY / HUGGINGFACE_API_KEY) no configurada en .env")
        if not self.mem_key or "your-" in self.mem_key.lower():
            raise ValueError("MEMORI_API_KEY no configurada en .env")

        self.client = OpenAI(
            base_url=self.base_url,
            api_key=self.llm_key,
            timeout=30.0
        )
        self.memori_sdk = None
        if memory_enabled:
            self.memori_sdk = Memori()
            self.memori_sdk.llm.register(self.client)
            logger.info(f"LLM: {self.llm_model} vía {self.base_url}. Memori SDK registrado.")
        else:
            logger.info(f"LLM: {self.llm_model} vía {self.base_url}. Memori SDK omitido (sin memoria).")

    def set_entity_id(self, entity_id: str):
        """Asigna la atribución en el SDK de Memori para evitar errores 422 al registrar turnos."""
        if not self.memori_sdk:
            return
        try:
            self.memori_sdk.attribution(entity_id=entity_id, process_id="tfm-support-agent")
            logger.info(f"Memori LLM: Atribución establecida para entidad '{entity_id}'")
        except Exception as e:
            logger.error(f"Error al establecer atribución en Memori LLM: {e}")

    def decide(self, case: Case, memories: list) -> AgentDecision:
        """
        Construye el prompt (sistema + caso + memorias recuperadas) y llama al LLM.
        NO incluye historial conversacional previo — cada llamada es una sesión nueva.
        """
        system_prompt = SYSTEM_BASE

        if memories:
            mem_block = "\n\n=== EXPERIENCIAS ANTERIORES RECUPERADAS ===\n"
            for i, m in enumerate(memories, 1):
                mem_block += f"Experiencia {i}: {m['fact']}\n"
            mem_block += (
                "\nUsa estas experiencias para mejorar tu decisión actual. "
                "Si una experiencia muestra que una decisión fue INCORRECTO, "
                "evita repetir ese error.\n"
            )
            system_prompt += mem_block

        user_msg = (
            f"=== CASO A EVALUAR ===\n"
            f"ID: {case.case_id}\n"
            f"Cliente: {case.customer.customer_tier.value}\n"
            f"Urgencia: {case.urgency.value}\n"
            f"Categoría: {case.category}\n"
            f"Descripción: {case.description}\n\n"
            f"Responde con el JSON de decisión."
        )

        for attempt in range(3):
            try:
                resp = self.client.chat.completions.create(
                    model=self.llm_model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user",   "content": user_msg}
                    ],
                    temperature=0.2
                )
                text = resp.choices[0].message.content.strip()
                # Extraer JSON robusto
                m = re.search(r"\{.*\}", text, re.DOTALL)
                if m:
                    text = m.group(0)
                elif text.startswith("```"):
                    text = re.sub(r"^```(?:json)?\n?", "", text)
                    text = re.sub(r"\n?```$", "", text).strip()
                data = json.loads(text)
                return AgentDecision(**data)
            except Exception as e:
                if attempt < 2:
                    wait = 5 * (2 ** attempt)
                    logger.warning(f"Error de red/LLM ({e}). Reintentando en {wait}s (intento {attempt+2}/3)...")
                    time.sleep(wait)
                else:
                    logger.error(f"LLM error tras {attempt+1} intentos: {e}")
                    raise
