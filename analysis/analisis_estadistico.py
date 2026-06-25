"""
analisis_estadistico.py — Daniel Cortés Arbeláez (Alumno 1)
=============================================================
Script de análisis estadístico del experimento TFE.
Ejecutar después de recibir el CSV de José Luis:

    python analysis/analisis_estadistico.py logs/simulation_results_XXXXXXXX.csv

Protocolo estadístico condicional (aprobado por Rafael):
    1. Shapiro-Wilk → verifica normalidad
    2. Levene       → verifica homocedasticidad
    3. t-Student o Mann-Whitney U según los resultados anteriores
    4. Siempre: Mann-Whitney U como verificación de robustez
    5. Tamaño del efecto: d de Cohen (paramétrico) o r de Rosenthal (no param.)
"""

import sys
import pandas as pd
import numpy as np
from scipy import stats

ALPHA = 0.05

# ── Cargar datos ──────────────────────────────────────────────────────────
def load_data(csv_path: str) -> tuple:
    df = pd.read_csv(csv_path)
    mem  = df[df["config"] == "with_memory"].copy()
    ctrl = df[df["config"] == "without_memory"].copy()
    print(f"\nDatos cargados: {len(mem)} episodios con memoria, {len(ctrl)} sin memoria.")
    return df, mem, ctrl

# ── Métricas ──────────────────────────────────────────────────────────────
def compute_ter(df_config: pd.DataFrame) -> float:
    """
    Tasa de Errores Repetidos (TER):
    % de errores que repiten el mismo tipo de error previamente observado.
    """
    errors = df_config[df_config["outcome"] == "incorrecto"].copy()
    if len(errors) == 0:
        return 0.0
    # Un error se considera repetido si el mismo error_type ya apareció antes
    errors = errors.reset_index(drop=True)
    seen_errors = set()
    repeated = 0
    for _, row in errors.iterrows():
        key = (row["case_type"].split("_")[0], row["error_type"])
        if key in seen_errors:
            repeated += 1
        seen_errors.add(key)
    return round(repeated / len(errors), 4)

def compute_accuracy(df_config: pd.DataFrame) -> float:
    return round((df_config["outcome"] == "correcto").mean(), 4)

def compute_tmd(df_config: pd.DataFrame) -> float:
    return round(df_config["decision_time_s"].mean(), 4)

def compute_accuracy_vip_by_quarter(df_config: pd.DataFrame) -> list:
    """Accuracy en casos VIP por cuartos del experimento."""
    vip = df_config[df_config["customer_tier"] == "VIP"].reset_index(drop=True)
    if len(vip) == 0:
        return []
    n = len(vip)
    q = n // 4
    quarters = []
    for i in range(4):
        start = i * q
        end   = (i + 1) * q if i < 3 else n
        subset = vip.iloc[start:end]
        acc    = (subset["outcome"] == "correcto").mean() if len(subset) > 0 else None
        quarters.append(round(acc, 3) if acc is not None else None)
    return quarters

# ── Prueba estadística condicional ────────────────────────────────────────
def statistical_test(series_mem: pd.Series, series_ctrl: pd.Series,
                     metric_name: str) -> dict:
    """
    Protocolo condicional:
    Shapiro-Wilk → Levene → t-Student o Welch → Mann-Whitney U (siempre)
    """
    print(f"\n{'='*60}")
    print(f"MÉTRICA: {metric_name}")
    print(f"{'='*60}")

    # Estadísticos descriptivos
    print(f"\nDescriptivos:")
    print(f"  Con memoria : media={series_mem.mean():.4f}, sd={series_mem.std():.4f}, n={len(series_mem)}")
    print(f"  Sin memoria : media={series_ctrl.mean():.4f}, sd={series_ctrl.std():.4f}, n={len(series_ctrl)}")

    # 1. Shapiro-Wilk
    sw_mem  = stats.shapiro(series_mem)
    sw_ctrl = stats.shapiro(series_ctrl)
    normal_mem  = sw_mem.pvalue  > ALPHA
    normal_ctrl = sw_ctrl.pvalue > ALPHA
    print(f"\n1. Shapiro-Wilk:")
    print(f"   Con memoria : W={sw_mem.statistic:.4f}, p={sw_mem.pvalue:.4f}  -> {'Normal' if normal_mem else 'NO normal'}")
    print(f"   Sin memoria : W={sw_ctrl.statistic:.4f}, p={sw_ctrl.pvalue:.4f}  -> {'Normal' if normal_ctrl else 'NO normal'}")
    both_normal = normal_mem and normal_ctrl

    # 2. Levene (solo si ambos normales)
    equal_var = False
    if both_normal:
        lev = stats.levene(series_mem, series_ctrl)
        equal_var = lev.pvalue > ALPHA
        print(f"\n2. Levene: F={lev.statistic:.4f}, p={lev.pvalue:.4f}  -> {'Varianzas iguales' if equal_var else 'Varianzas distintas (Welch)'}")
    else:
        print("\n2. Levene: omitido (distribución no normal -> se usa Mann-Whitney U)")

    # 3. t-Student / Welch (si normalidad) o Mann-Whitney U (si no)
    if both_normal:
        t_res = stats.ttest_ind(series_mem, series_ctrl, equal_var=equal_var)
        test_name = "t-Student" if equal_var else "t-Welch"
        sig = t_res.pvalue < ALPHA
        print(f"\n3. {test_name}: t={t_res.statistic:.4f}, p={t_res.pvalue:.4f}  -> {'SIGNIFICATIVO [OK]' if sig else 'No significativo'}")
        # Cohen's d
        pooled_std = np.sqrt((series_mem.std()**2 + series_ctrl.std()**2) / 2)
        d = (series_mem.mean() - series_ctrl.mean()) / pooled_std if pooled_std > 0 else 0
        effect_label = "pequeño" if abs(d) < 0.5 else ("medio" if abs(d) < 0.8 else "grande")
        print(f"   Tamaño del efecto (d de Cohen): {d:.4f} → efecto {effect_label}")
        primary_result = {"test": test_name, "statistic": t_res.statistic, "p": t_res.pvalue, "effect_d": d, "significant": sig}
    else:
        primary_result = None

    # 4. Mann-Whitney U — siempre (robustez)
    mw = stats.mannwhitneyu(series_mem, series_ctrl, alternative="two-sided")
    mw_sig = mw.pvalue < ALPHA
    n1, n2 = len(series_mem), len(series_ctrl)
    r_effect = mw.statistic / (n1 * n2)  # r de Rosenthal
    print(f"\n4. Mann-Whitney U (robustez): U={mw.statistic:.1f}, p={mw.pvalue:.4f}  -> {'SIGNIFICATIVO [OK]' if mw_sig else 'No significativo'}")
    print(f"   Tamaño del efecto (r de Rosenthal): {r_effect:.4f}")

    return {
        "metric":          metric_name,
        "mean_mem":        series_mem.mean(),
        "mean_ctrl":       series_ctrl.mean(),
        "diff":            series_mem.mean() - series_ctrl.mean(),
        "primary":         primary_result,
        "mann_whitney_p":  mw.pvalue,
        "mann_whitney_sig": mw_sig,
        "r_effect":        r_effect
    }

# ── Main ──────────────────────────────────────────────────────────────────
def main():
    if len(sys.argv) < 2:
        print("Uso: python analysis/analisis_estadistico.py <ruta_al_csv>")
        sys.exit(1)

    csv_path = sys.argv[1]
    df, mem, ctrl = load_data(csv_path)

    print("\n" + "="*60)
    print("ANÁLISIS ESTADÍSTICO — TFE UNIR")
    print(f"Archivo: {csv_path}")
    print("="*60)

    # ── TER ───────────────────────────────────────────────────────────────
    print("\n--- TASA DE ERRORES REPETIDOS (TER) ---")
    ter_mem  = compute_ter(mem)
    ter_ctrl = compute_ter(ctrl)
    print(f"TER con memoria : {ter_mem:.4f} ({ter_mem*100:.1f}%)")
    print(f"TER sin memoria : {ter_ctrl:.4f} ({ter_ctrl*100:.1f}%)")
    print("Nota: TER es un valor único por configuración — no admite t-test directo.")
    print(f"Diferencia absoluta: {ter_ctrl - ter_mem:.4f} (positiva = memoria reduce errores repetidos)")

    # ── ACCURACY por episodio (para t-test) ───────────────────────────────
    mem["correct_bin"]  = (mem["outcome"]  == "correcto").astype(int)
    ctrl["correct_bin"] = (ctrl["outcome"] == "correcto").astype(int)
    stat_acc = statistical_test(mem["correct_bin"], ctrl["correct_bin"], "ACCURACY POR EPISODIO")

    # ── TMD ───────────────────────────────────────────────────────────────
    stat_tmd = statistical_test(mem["decision_time_s"], ctrl["decision_time_s"], "TIEMPO MEDIO DE DECISIÓN (segundos)")

    # ── VIP por cuartos ────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print("APRENDIZAJE DE EXCEPCIÓN VIP (por cuartos del experimento)")
    print(f"{'='*60}")
    q_mem  = compute_accuracy_vip_by_quarter(mem)
    q_ctrl = compute_accuracy_vip_by_quarter(ctrl)
    for i, (qm, qc) in enumerate(zip(q_mem, q_ctrl), 1):
        mem_str  = f"{qm:.3f}" if qm is not None else "N/A"
        ctrl_str = f"{qc:.3f}" if qc is not None else "N/A"
        trend_note = "↑ memoria mejora" if (qm is not None and qc is not None and qm > qc) else ""
        print(f"  Cuarto {i}: con memoria={mem_str}  sin memoria={ctrl_str}  {trend_note}")

    # ── Control aislados ───────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print("CASOS DE CONTROL AISLADOS (validación experimental)")
    print(f"{'='*60}")
    ctrl_aislados_mem  = mem[mem["case_type"]  == "control_aislado"]
    ctrl_aislados_ctrl = ctrl[ctrl["case_type"] == "control_aislado"]
    acc_aislados_mem  = compute_accuracy(ctrl_aislados_mem)
    acc_aislados_ctrl = compute_accuracy(ctrl_aislados_ctrl)
    print(f"  Accuracy con memoria : {acc_aislados_mem:.3f}")
    print(f"  Accuracy sin memoria : {acc_aislados_ctrl:.3f}")
    if abs(acc_aislados_mem - acc_aislados_ctrl) < 0.1:
        print("  -> Diferencia < 0.1 -> validación OK: la mejora es específica, no global.")
    else:
        print("  -> ATENCIÓN: diferencia > 0.1 -> posible factor confusor. Investigar.")

    # ── Tabla resumen ──────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print("TABLA RESUMEN DE RESULTADOS")
    print(f"{'='*60}")
    print(f"{'Métrica':<30} {'Con mem':<12} {'Sin mem':<12} {'p-valor':>10} {'Signif.'}")
    print("-"*70)
    print(f"{'Accuracy (mean)':<30} {stat_acc['mean_mem']:<12.4f} {stat_acc['mean_ctrl']:<12.4f} "
          f"{stat_acc['mann_whitney_p']:>10.4f} {'SÍ' if stat_acc['mann_whitney_sig'] else 'NO'}")
    print(f"{'TMD (segundos)':<30} {stat_tmd['mean_mem']:<12.4f} {stat_tmd['mean_ctrl']:<12.4f} "
          f"{stat_tmd['mann_whitney_p']:>10.4f} {'SÍ' if stat_tmd['mann_whitney_sig'] else 'NO'}")
    print(f"{'TER':<30} {ter_mem:<12.4f} {ter_ctrl:<12.4f} {'—':>10} {'—'}")
    print("="*70)
    print("\nAnálisis completado. Usa visualizaciones.py para generar las gráficas.")


if __name__ == "__main__":
    main()
