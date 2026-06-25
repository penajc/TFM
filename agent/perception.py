from enum import Enum
from pydantic import BaseModel, Field

class CustomerTier(str, Enum):
    VIP     = "VIP"
    GOLD    = "gold"
    REGULAR = "regular"

class UrgencyLevel(str, Enum):
    HIGH   = "high"
    MEDIUM = "medium"
    LOW    = "low"

class DecisionType(str, Enum):
    A1 = "A1"   # Reembolso / Compensación directa
    A2 = "A2"   # Escalar a soporte de nivel superior
    A3 = "A3"   # Respuesta estándar / base de conocimiento
    A4 = "A4"   # Rechazar / cerrar sin acción

class Customer(BaseModel):
    customer_id:   str          = Field(..., description="ID único del cliente")
    customer_tier: CustomerTier = Field(..., description="Nivel del cliente: VIP, gold o regular")

class Case(BaseModel):
    case_id:     str          = Field(..., description="ID único del caso")
    customer:    Customer     = Field(..., description="Datos del cliente asociado")
    description: str          = Field(..., description="Descripción del problema en lenguaje natural")
    urgency:     UrgencyLevel = Field(..., description="Nivel de urgencia: high, medium o low")
    category:    str          = Field(..., description="Categoría del caso: Facturación, Técnico, Soporte, Información, Seguridad")
    # Campo de referencia para el simulador — nunca se expone al agente
    expected_decision: str    = Field(default="", description="Decisión normativa correcta (solo para el simulador)")

class AgentDecision(BaseModel):
    decision: DecisionType = Field(..., description="Acción seleccionada: A1, A2, A3 o A4")
    reason:   str          = Field(..., description="Justificación de la decisión tomada")
