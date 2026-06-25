import logging
from typing import Dict, Any
from agent.perception import Case, DecisionType

logger = logging.getLogger("simulator.rules")


class SimulatorRules:
    """
    Motor de 6 reglas normativas que determina la decisión correcta para cada caso.
    Este componente actúa como juez objetivo del experimento.
    El agente nunca accede directamente a estas reglas; debe inferirlas.
    """

    def evaluate(self, case: Case, decision: DecisionType) -> Dict[str, Any]:
        """
        Evalúa la decisión del agente y devuelve:
        - outcome: 'correcto' | 'incorrecto'
        - error_type: código del error o None
        - expected: la decisión normativa correcta
        """
        expected = self._expected_decision(case)
        if decision == expected:
            return {"outcome": "correcto", "error_type": None, "expected": expected.value}
        else:
            error = self._classify_error(case, decision, expected)
            return {"outcome": "incorrecto", "error_type": error, "expected": expected.value}

    def _expected_decision(self, case: Case) -> DecisionType:
        """
        Determina la decisión normativamente correcta aplicando las 6 reglas en orden de prioridad.
        """
        desc     = case.description.lower()
        tier     = case.customer.customer_tier.value
        urgency  = case.urgency.value
        category = case.category.lower()

        # Si el campo expected_decision viene informado, usarlo directamente
        if case.expected_decision:
            try:
                return DecisionType(case.expected_decision)
            except Exception:
                pass

        # REGLA 1 — Seguridad: siempre escalar o rechazar
        if any(kw in desc for kw in ["hack", "fraude", "contraseña robada", "transacciones extrañas", "alertas de seguridad"]):
            return DecisionType.A2

        # REGLA 2 — Clientes VIP: nunca respuesta estándar ni rechazo
        # (Excepción aprendible: los VIP tienen tratamiento preferencial incluso en consultas simples)
        if tier == "VIP":
            if any(kw in desc for kw in ["cobro duplicado", "cargo por duplicado", "error de cobro"]):
                return DecisionType.A1
            return DecisionType.A2  # VIP siempre escala o recibe compensación directa

        # REGLA 3 — Urgencia alta: siempre escalar o compensar
        if urgency == "high":
            if any(kw in desc for kw in ["cobro duplicado", "cargo por duplicado", "error de cobro"]):
                return DecisionType.A1
            return DecisionType.A2

        # REGLA 4 — Error de facturación (cobro duplicado): siempre reembolso
        if any(kw in desc for kw in ["cobro duplicado", "cargo por duplicado", "error de cobro", "me cobraron dos"]):
            return DecisionType.A1

        # REGLA 5 — Consultas informativas simples: respuesta estándar
        if any(kw in desc for kw in ["horario", "dirección", "cómo crear", "cómo renovar",
                                      "cómo cambiar", "dónde están", "cuándo abren", "foto de perfil",
                                      "cambiar mi foto", "renovar mi plan"]):
            return DecisionType.A3

        # REGLA 6 — Cliente regular, urgencia baja, soporte estándar: respuesta estándar
        if tier == "regular" and urgency == "low":
            return DecisionType.A3

        # REGLA 6b — Solicitud de reembolso injustificada (cliente regular, sin motivo válido): rechazar
        if tier == "regular" and any(kw in desc for kw in ["reembolso", "devuélvame", "quiero mi dinero"]):
            if not any(kw in desc for kw in ["cobro duplicado", "error", "fallo"]):
                return DecisionType.A4

        # Por defecto: escalar
        return DecisionType.A2

    def _classify_error(self, case: Case, decision: DecisionType,
                         expected: DecisionType) -> str:
        tier    = case.customer.customer_tier.value
        desc    = case.description.lower()
        urgency = case.urgency.value

        if tier == "VIP" and decision in [DecisionType.A3, DecisionType.A4]:
            return "ERROR_VIP_DESATENDIDO"
        if urgency == "high" and decision in [DecisionType.A3, DecisionType.A4]:
            return "ERROR_URGENCIA_IGNORADA"
        if any(kw in desc for kw in ["cobro duplicado", "cargo por duplicado"]) and decision != DecisionType.A1:
            return "ERROR_FACTURACION_NO_COMPENSADA"
        if any(kw in desc for kw in ["hack", "fraude"]) and decision == DecisionType.A1:
            return "ERROR_SEGURIDAD_COMPENSADA_INCORRECTAMENTE"
        if decision == DecisionType.A1 and expected == DecisionType.A3:
            return "ERROR_SOBRECOMPENSACION"
        if decision == DecisionType.A4 and expected != DecisionType.A4:
            return "ERROR_RECHAZO_INJUSTIFICADO"
        return "ERROR_DECISION_INCORRECTA"
