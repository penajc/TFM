"""
run_simulation.py
=================
Script principal del experimento.
Ejecuta los 50 casos en DOS configuraciones (con memoria / sin memoria)
y genera el CSV de resultados para el análisis estadístico.

Correcciones respecto a la versión anterior:
- entity_id único por ejecución → sin contaminación entre runs
- 50 casos según distribución del plan: 15 base, 15 similares repetidos,
  10 VIP (excepción aprendible), 10 ambiguos, 10 control aislados
- CSV completo con columnas aligned al protocolo de análisis de Daniel
"""

import os
import logging
import datetime
from agent.loop import AgentLoop

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logging.getLogger("openai").setLevel(logging.WARNING)

# ── ID único para este run ─────────────────────────────────────────────────
# Garantiza que la memoria de Memori cloud no se contamine entre ejecuciones.
RUN_TIMESTAMP = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
ENTITY_WITH    = f"tfm_exp_with_{RUN_TIMESTAMP}"
ENTITY_WITHOUT = f"tfm_exp_ctrl_{RUN_TIMESTAMP}"   # no se usa (memoria off), solo informativo

CSV_PATH = f"logs/simulation_results_{RUN_TIMESTAMP}.csv"

# ── 50 CASOS DE PRUEBA ─────────────────────────────────────────────────────
# Distribución acordada:
#   - 15 base        (regla clara, sin ambigüedad)      posiciones 1–9, 16–21
#   - 15 repetidos   (similares, distribuidos ~10/25/40) posiciones 10–14, 25–29, 40–44 → 5 grupos × 3
#   - 10 VIP         (excepción aprendible)              posiciones 17–26  (mezclados con repetidos)
#   - 10 ambiguos    (regla no inmediata)                posiciones 30–39
#   - 10 control     (aislados, sin precedentes útiles)  posiciones 45–50 + 4 intercalados
#
# Los casos repetidos se intercalan: primera aparición ~pos10, segunda ~pos25, tercera ~pos40.
# expected_decision: solo lo usa el simulador, nunca el agente.

CASES = [
    # ── POSICIONES 1–9: BASE ──────────────────────────────────────────────
    {
        "case_id": "C001", "customer": {"customer_id": "CLI001", "customer_tier": "regular"},
        "description": "Buenos días, ¿me pueden decir cuáles son sus horarios de atención al cliente?",
        "urgency": "low", "category": "Información", "expected_decision": "A3"
    },
    {
        "case_id": "C002", "customer": {"customer_id": "CLI002", "customer_tier": "regular"},
        "description": "Hola, ¿podrían indicarme la dirección física de sus oficinas centrales?",
        "urgency": "low", "category": "Información", "expected_decision": "A3"
    },
    {
        "case_id": "C003", "customer": {"customer_id": "CLI003", "customer_tier": "regular"},
        "description": "¿Cómo puedo crear una cuenta nueva en la plataforma?",
        "urgency": "low", "category": "Información", "expected_decision": "A3"
    },
    {
        "case_id": "C004", "customer": {"customer_id": "CLI004", "customer_tier": "regular"},
        "description": "Me han cobrado dos veces la suscripción mensual en mi tarjeta. Exijo el reembolso del cobro duplicado.",
        "urgency": "high", "category": "Facturación", "expected_decision": "A1"
    },
    {
        "case_id": "C005", "customer": {"customer_id": "CLI005", "customer_tier": "gold"},
        "description": "Hay un error de cobro en mi cuenta, aparece un cargo duplicado del mes pasado.",
        "urgency": "high", "category": "Facturación", "expected_decision": "A1"
    },
    {
        "case_id": "C006", "customer": {"customer_id": "CLI006", "customer_tier": "regular"},
        "description": "¡Urgente! Mi servidor de producción está completamente caído y mis usuarios no pueden acceder.",
        "urgency": "high", "category": "Técnico", "expected_decision": "A2"
    },
    {
        "case_id": "C007", "customer": {"customer_id": "CLI007", "customer_tier": "gold"},
        "description": "Nuestro sistema de pagos dejó de funcionar completamente. Necesitamos soporte técnico inmediato.",
        "urgency": "high", "category": "Técnico", "expected_decision": "A2"
    },
    {
        "case_id": "C008", "customer": {"customer_id": "CLI008", "customer_tier": "gold"},
        "description": "Creo que alguien ha hackeado mi cuenta. Aparecen transacciones que yo no realicé.",
        "urgency": "high", "category": "Seguridad", "expected_decision": "A2"
    },
    {
        "case_id": "C009", "customer": {"customer_id": "CLI009", "customer_tier": "regular"},
        "description": "Quiero solicitar un reembolso de mi última factura porque no me gustó el servicio.",
        "urgency": "low", "category": "Facturación", "expected_decision": "A4"
    },

    # ── POSICIÓN 10–14: PRIMERA APARICIÓN SIMILARES REPETIDOS (Grupos A–E) ─
    {
        "case_id": "C010", "customer": {"customer_id": "CLI010", "customer_tier": "VIP"},
        "description": "Soy cliente VIP. Necesito saber cómo renovar mi plan desde la aplicación móvil.",
        "urgency": "medium", "category": "Soporte", "expected_decision": "A2"
    },  # GRUPO A — VIP consulta simple → A2 (no A3)
    {
        "case_id": "C011", "customer": {"customer_id": "CLI011", "customer_tier": "regular"},
        "description": "Me hicieron un cargo doble en mi tarjeta este mes por la suscripción. Por favor compensen el error.",
        "urgency": "medium", "category": "Facturación", "expected_decision": "A1"
    },  # GRUPO B — cobro duplicado → A1
    {
        "case_id": "C012", "customer": {"customer_id": "CLI012", "customer_tier": "regular"},
        "description": "Mi aplicación no carga, muestra un error 503. Es urgente, trabajo con ella diariamente.",
        "urgency": "high", "category": "Técnico", "expected_decision": "A2"
    },  # GRUPO C — urgencia alta técnico → A2
    {
        "case_id": "C013", "customer": {"customer_id": "CLI013", "customer_tier": "gold"},
        "description": "He visto alertas de seguridad en mi cuenta y temo que hayan comprometido mis datos.",
        "urgency": "high", "category": "Seguridad", "expected_decision": "A2"
    },  # GRUPO D — seguridad → A2
    {
        "case_id": "C014", "customer": {"customer_id": "CLI014", "customer_tier": "regular"},
        "description": "Quiero que me devuelvan el dinero de este mes. No creo que el servicio valga lo que cobran.",
        "urgency": "low", "category": "Facturación", "expected_decision": "A4"
    },  # GRUPO E — reembolso injustificado → A4

    # ── POSICIONES 15–16: BASE ─────────────────────────────────────────────
    {
        "case_id": "C015", "customer": {"customer_id": "CLI015", "customer_tier": "regular"},
        "description": "¿Cómo puedo cambiar mi foto de perfil en la plataforma?",
        "urgency": "low", "category": "Soporte", "expected_decision": "A3"
    },
    {
        "case_id": "C016", "customer": {"customer_id": "CLI016", "customer_tier": "gold"},
        "description": "Necesito información sobre los planes de precios disponibles.",
        "urgency": "low", "category": "Información", "expected_decision": "A3"
    },

    # ── POSICIONES 17–24: VIP EXCEPCIÓN ───────────────────────────────────
    {
        "case_id": "C017", "customer": {"customer_id": "CLI017", "customer_tier": "VIP"},
        "description": "Buenas tardes, como cliente VIP quisiera saber cuándo abren sus oficinas hoy.",
        "urgency": "low", "category": "Información", "expected_decision": "A2"
    },
    {
        "case_id": "C018", "customer": {"customer_id": "CLI018", "customer_tier": "VIP"},
        "description": "Tengo un problema con la factura de este mes. Aparece un monto que no reconozco.",
        "urgency": "medium", "category": "Facturación", "expected_decision": "A2"
    },
    {
        "case_id": "C019", "customer": {"customer_id": "CLI019", "customer_tier": "VIP"},
        "description": "Quiero consultar el estado de mi último pedido de soporte técnico.",
        "urgency": "low", "category": "Soporte", "expected_decision": "A2"
    },
    {
        "case_id": "C020", "customer": {"customer_id": "CLI020", "customer_tier": "VIP"},
        "description": "Soy VIP desde hace 3 años. Necesito ayuda para configurar la integración API.",
        "urgency": "medium", "category": "Técnico", "expected_decision": "A2"
    },
    {
        "case_id": "C021", "customer": {"customer_id": "CLI021", "customer_tier": "VIP"},
        "description": "Me han cobrado dos veces la cuota mensual. Soy cliente VIP y exijo solución inmediata.",
        "urgency": "high", "category": "Facturación", "expected_decision": "A1"
    },
    {
        "case_id": "C022", "customer": {"customer_id": "CLI022", "customer_tier": "VIP"},
        "description": "Necesito saber cómo acceder al portal exclusivo para clientes VIP.",
        "urgency": "low", "category": "Información", "expected_decision": "A2"
    },
    {
        "case_id": "C023", "customer": {"customer_id": "CLI023", "customer_tier": "VIP"},
        "description": "Hay un problema técnico con mi panel de control. Como VIP necesito resolución prioritaria.",
        "urgency": "medium", "category": "Técnico", "expected_decision": "A2"
    },
    {
        "case_id": "C024", "customer": {"customer_id": "CLI024", "customer_tier": "VIP"},
        "description": "Quisiera conocer las opciones de upgrade disponibles para mi plan actual como cliente VIP.",
        "urgency": "low", "category": "Información", "expected_decision": "A2"
    },

    # ── POSICIÓN 25–29: SEGUNDA APARICIÓN SIMILARES REPETIDOS ─────────────
    {
        "case_id": "C025", "customer": {"customer_id": "CLI025", "customer_tier": "VIP"},
        "description": "Soy cliente VIP. ¿Cómo actualizo mi plan desde la app?",
        "urgency": "medium", "category": "Soporte", "expected_decision": "A2"
    },  # GRUPO A segunda vez
    {
        "case_id": "C026", "customer": {"customer_id": "CLI026", "customer_tier": "regular"},
        "description": "Me cobraron dos veces esta semana. Necesito que revisen mi factura y compensen el error.",
        "urgency": "medium", "category": "Facturación", "expected_decision": "A1"
    },  # GRUPO B segunda vez
    {
        "case_id": "C027", "customer": {"customer_id": "CLI027", "customer_tier": "regular"},
        "description": "El sistema arroja error 503 constantemente y necesito solución urgente para continuar trabajando.",
        "urgency": "high", "category": "Técnico", "expected_decision": "A2"
    },  # GRUPO C segunda vez
    {
        "case_id": "C028", "customer": {"customer_id": "CLI028", "customer_tier": "gold"},
        "description": "Recibí alertas de que accedieron a mi cuenta desde un dispositivo desconocido.",
        "urgency": "high", "category": "Seguridad", "expected_decision": "A2"
    },  # GRUPO D segunda vez
    {
        "case_id": "C029", "customer": {"customer_id": "CLI029", "customer_tier": "regular"},
        "description": "Exijo que me reembolsen la suscripción de este mes. No estoy satisfecho con lo que ofrecen.",
        "urgency": "low", "category": "Facturación", "expected_decision": "A4"
    },  # GRUPO E segunda vez

    # ── POSICIONES 30–39: AMBIGUOS ────────────────────────────────────────
    {
        "case_id": "C030", "customer": {"customer_id": "CLI030", "customer_tier": "gold"},
        "description": "Llevo dos días sin poder iniciar sesión y ya intenté recuperar mi contraseña.",
        "urgency": "medium", "category": "Técnico", "expected_decision": "A2"
    },
    {
        "case_id": "C031", "customer": {"customer_id": "CLI031", "customer_tier": "regular"},
        "description": "El mes pasado pagué y ahora dicen que no tengo acceso. No entiendo qué pasó.",
        "urgency": "medium", "category": "Facturación", "expected_decision": "A2"
    },
    {
        "case_id": "C032", "customer": {"customer_id": "CLI032", "customer_tier": "gold"},
        "description": "Algunos datos de mi perfil aparecen incorrectos y no puedo editarlos yo solo.",
        "urgency": "medium", "category": "Soporte", "expected_decision": "A2"
    },
    {
        "case_id": "C033", "customer": {"customer_id": "CLI033", "customer_tier": "regular"},
        "description": "Me llegó un correo diciendo que mi cuenta sería suspendida pero no sé por qué.",
        "urgency": "medium", "category": "Información", "expected_decision": "A3"
    },
    {
        "case_id": "C034", "customer": {"customer_id": "CLI034", "customer_tier": "gold"},
        "description": "La integración con mi CRM dejó de funcionar desde la última actualización de la plataforma.",
        "urgency": "medium", "category": "Técnico", "expected_decision": "A2"
    },
    {
        "case_id": "C035", "customer": {"customer_id": "CLI035", "customer_tier": "regular"},
        "description": "Recibí una notificación de pago que no reconozco. No sé si es legítima o un error.",
        "urgency": "medium", "category": "Facturación", "expected_decision": "A2"
    },
    {
        "case_id": "C036", "customer": {"customer_id": "CLI036", "customer_tier": "gold"},
        "description": "Las notificaciones que me llegan están en un idioma incorrecto. ¿Cómo puedo cambiarlo?",
        "urgency": "low", "category": "Soporte", "expected_decision": "A3"
    },
    {
        "case_id": "C037", "customer": {"customer_id": "CLI037", "customer_tier": "regular"},
        "description": "Me generaron una factura por un servicio que no contraté. Quiero una explicación.",
        "urgency": "medium", "category": "Facturación", "expected_decision": "A2"
    },
    {
        "case_id": "C038", "customer": {"customer_id": "CLI038", "customer_tier": "gold"},
        "description": "El reporte mensual tiene datos que no coinciden con lo que veo en el panel.",
        "urgency": "medium", "category": "Técnico", "expected_decision": "A2"
    },
    {
        "case_id": "C039", "customer": {"customer_id": "CLI039", "customer_tier": "regular"},
        "description": "Cancelé mi suscripción pero siguen cobrándome cada mes.",
        "urgency": "medium", "category": "Facturación", "expected_decision": "A1"
    },

    # ── POSICIÓN 40–44: TERCERA APARICIÓN SIMILARES REPETIDOS ─────────────
    {
        "case_id": "C040", "customer": {"customer_id": "CLI040", "customer_tier": "VIP"},
        "description": "Como VIP, quisiera saber los pasos para actualizar mi plan desde el móvil.",
        "urgency": "medium", "category": "Soporte", "expected_decision": "A2"
    },  # GRUPO A tercera vez
    {
        "case_id": "C041", "customer": {"customer_id": "CLI041", "customer_tier": "regular"},
        "description": "Aparecen dos cargos idénticos en mi extracto bancario por la misma suscripción.",
        "urgency": "medium", "category": "Facturación", "expected_decision": "A1"
    },  # GRUPO B tercera vez
    {
        "case_id": "C042", "customer": {"customer_id": "CLI042", "customer_tier": "regular"},
        "description": "Urgente: el sistema devuelve error 503 y no podemos operar con normalidad.",
        "urgency": "high", "category": "Técnico", "expected_decision": "A2"
    },  # GRUPO C tercera vez
    {
        "case_id": "C043", "customer": {"customer_id": "CLI043", "customer_tier": "gold"},
        "description": "Hay actividad sospechosa en mi cuenta. Veo accesos desde IPs que no reconozco.",
        "urgency": "high", "category": "Seguridad", "expected_decision": "A2"
    },  # GRUPO D tercera vez
    {
        "case_id": "C044", "customer": {"customer_id": "CLI044", "customer_tier": "regular"},
        "description": "Quiero que me devuelvan el dinero. Simplemente no me convenció el servicio.",
        "urgency": "low", "category": "Facturación", "expected_decision": "A4"
    },  # GRUPO E tercera vez

    # ── POSICIONES 45–50: CONTROL AISLADOS (sin precedentes útiles) ────────
    # Predicción: sin diferencia entre configuraciones con/sin memoria
    {
        "case_id": "C045", "customer": {"customer_id": "CLI045", "customer_tier": "gold"},
        "description": "Necesito exportar un informe personalizado de mis últimos 6 meses de actividad.",
        "urgency": "low", "category": "Soporte", "expected_decision": "A3"
    },
    {
        "case_id": "C046", "customer": {"customer_id": "CLI046", "customer_tier": "regular"},
        "description": "¿Puedo añadir varios usuarios administradores a mi cuenta empresarial?",
        "urgency": "low", "category": "Información", "expected_decision": "A3"
    },
    {
        "case_id": "C047", "customer": {"customer_id": "CLI047", "customer_tier": "gold"},
        "description": "La opción de guardar preferencias no persiste entre sesiones en mi navegador.",
        "urgency": "medium", "category": "Técnico", "expected_decision": "A2"
    },
    {
        "case_id": "C048", "customer": {"customer_id": "CLI048", "customer_tier": "regular"},
        "description": "¿Tienen disponible algún tutorial en vídeo para aprender a usar el panel de control?",
        "urgency": "low", "category": "Información", "expected_decision": "A3"
    },
    {
        "case_id": "C049", "customer": {"customer_id": "CLI049", "customer_tier": "gold"},
        "description": "El módulo de estadísticas avanzadas no muestra datos de los últimos tres días.",
        "urgency": "medium", "category": "Técnico", "expected_decision": "A2"
    },
    {
        "case_id": "C050", "customer": {"customer_id": "CLI050", "customer_tier": "regular"},
        "description": "Quisiera saber si ofrecen descuento por pago anual en lugar de mensual.",
        "urgency": "low", "category": "Información", "expected_decision": "A3"
    },
]

# Clasificar los tipos de caso para el CSV
CASE_TYPES = (
    ["base"] * 9 +
    ["repetido_A", "repetido_B", "repetido_C", "repetido_D", "repetido_E"] +
    ["base"] * 2 +
    ["VIP"] * 8 +
    ["repetido_A", "repetido_B", "repetido_C", "repetido_D", "repetido_E"] +
    ["ambiguo"] * 10 +
    ["repetido_A", "repetido_B", "repetido_C", "repetido_D", "repetido_E"] +
    ["control_aislado"] * 6
)


def run_simulation():
    n = len(CASES)
    print("=" * 70)
    print(f"TFE — EXPERIMENTO COMPLETO | n={n} casos | Run: {RUN_TIMESTAMP}")
    print("=" * 70)

    # ── CONFIG A: CON MEMORIA ─────────────────────────────────────────────
    print(f"\n>>> CONFIGURACIÓN: MEMORIA ACTIVA (entity: {ENTITY_WITH})")
    loop_mem = AgentLoop(
        memory_enabled=True,
        entity_id=ENTITY_WITH,
        log_path=CSV_PATH
    )
    results_mem = []
    for i, case in enumerate(CASES):
        ep_id = f"EP_MEM_{i+1:03d}"
        res = loop_mem.run_episode(
            episode_id=ep_id,
            case_type=CASE_TYPES[i],
            raw_case=case
        )
        results_mem.append(res)

    # ── CONFIG B: SIN MEMORIA ─────────────────────────────────────────────
    print(f"\n>>> CONFIGURACIÓN: MEMORIA DESACTIVADA (control)")
    loop_ctrl = AgentLoop(
        memory_enabled=False,
        entity_id=ENTITY_WITHOUT,
        log_path=CSV_PATH
    )
    results_ctrl = []
    for i, case in enumerate(CASES):
        ep_id = f"EP_CTRL_{i+1:03d}"
        res = loop_ctrl.run_episode(
            episode_id=ep_id,
            case_type=CASE_TYPES[i],
            raw_case=case
        )
        results_ctrl.append(res)

    # ── RESUMEN ───────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("RESUMEN COMPARATIVO")
    print("=" * 70)
    print(f"{'Caso':<8} {'Con memoria':<22} {'Sin memoria':<22} {'Esperado'}")
    print("-" * 70)

    ok_mem = ok_ctrl = 0
    for i in range(n):
        m, c = results_mem[i], results_ctrl[i]
        ok_mem  += 1 if m["outcome"] == "correcto" else 0
        ok_ctrl += 1 if c["outcome"] == "correcto" else 0
        flag = "OK" if m["outcome"] == "correcto" else "ERR"
        flag_c = "OK" if c["outcome"] == "correcto" else "ERR"
        print(f"{CASES[i]['case_id']:<8} {flag:<3} {m['decision']} ({m['outcome'][:3]:<10}) "
              f"{flag_c:<3} {c['decision']} ({c['outcome'][:3]:<10}) {m['expected']}")

    print("-" * 70)
    print(f"Accuracy  | Con memoria: {ok_mem}/{n} ({int(ok_mem/n*100)}%)"
          f" | Sin memoria: {ok_ctrl}/{n} ({int(ok_ctrl/n*100)}%)")
    print("=" * 70)
    print(f"\nCSV guardado en: {os.path.abspath(CSV_PATH)}")
    print("Entrega este CSV a Daniel para el análisis estadístico.")


if __name__ == "__main__":
    run_simulation()
