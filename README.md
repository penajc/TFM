# TFE — Agente Autónomo con Memoria Estructurada (Memori)

Repositorio del experimento comparativo: agente con memoria vs. agente sin memoria.

---

## Estructura del proyecto

```
├── agent/
│   ├── perception.py      # Modelos Pydantic (Case, Customer, Decision)
│   ├── memory.py          # Adaptador Memori Labs (entity_id único por run)
│   ├── openai_client.py   # Cliente LLM vía Hugging Face + Memori SDK
│   └── loop.py            # Ciclo decisional de 5 fases
├── simulator/
│   └── rules.py           # 6 reglas normativas (juez objetivo del experimento)
├── analysis/
│   ├── analisis_estadistico.py   # Daniel: Shapiro-Wilk, t-test, Mann-Whitney
│   └── visualizaciones.py        # Daniel: 5 figuras para el capítulo de resultados
├── logs/                  # CSV de resultados (generados automáticamente)
├── figures/               # Gráficas generadas por visualizaciones.py
├── run_simulation.py      # Script principal — ejecutar aquí
├── requirements.txt
└── .env.example           # Copiar a .env y rellenar las claves
```

---

## Instalación

```powershell
python -m venv venv
.\venv\Scripts\activate          # Windows
# source venv/bin/activate       # Mac/Linux

pip install -r requirements.txt
cp .env.example .env
# Editar .env con las claves reales
```

---

## Ejecución del experimento

```powershell
python run_simulation.py
```

Genera un CSV en `logs/simulation_results_TIMESTAMP.csv` con los 50 casos × 2 configuraciones.

---

## Análisis (Daniel)

Una vez recibido el CSV:

```bash
python analysis/analisis_estadistico.py logs/simulation_results_TIMESTAMP.csv
python analysis/visualizaciones.py      logs/simulation_results_TIMESTAMP.csv
```

Las figuras se guardan en `figures/`.

---

## Correcciones respecto a la versión anterior

| Problema | Solución |
|---|---|
| n=11 casos (insuficiente para estadística) | 50 casos según distribución del plan de acción |
| entity_id fijo → contaminación entre runs | entity_id único por ejecución con timestamp |
| memories_retrieved_n=2 desde el caso 1 (imposible) | Corregido: memoria empieza vacía en cada run |
| Configuración sin memoria incompleta (8/11 filas) | Loop completo garantizado para ambas configs |
| CSV sin columna expected_decision | Añadida para análisis de TER por tipo de error |
| threshold no pasado a sdk.recall() | Eliminado (sdk.recall solo acepta limit) |

---

## Notas técnicas

- **LLM**: Hugging Face Serverless (Qwen2.5-72B-Instruct) — gratuito
- **Memoria**: Memori Labs SDK — requiere API key de app.memorilabs.ai
- **Temperatura**: 0.2 (baja variabilidad, alta reproducibilidad)
- **Aislamiento**: cada run usa entity_id único → sin contaminación entre experimentos
- **Semilla**: random_seed=42 documentada en el código para reproducibilidad
