"""
visualizaciones.py — Daniel Cortés Arbeláez (Alumno 1)
=======================================================
Genera las 5 visualizaciones del experimento TFE.
Requiere el CSV de resultados de la simulación.

Uso:
    python analysis/visualizaciones.py logs/simulation_results_XXXXXXXX.csv

Produce (en carpeta figures/):
    1. boxplot_accuracy.png         — Accuracy por episodio, comparativo
    2. evolucion_temporal.png       — Accuracy acumulada a lo largo del experimento
    3. heatmap_decisiones.png       — Decisiones por tipo de caso y configuración
    4. vip_aprendizaje.png          — Accuracy VIP por cuartos del experimento
    5. tmd_comparativo.png          — Tiempo medio de decisión comparativo
"""

import sys
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns

# Estilo limpio para documentos académicos
plt.rcParams.update({
    "font.family": "Arial",
    "font.size": 11,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "figure.dpi": 150,
})

COLOR_MEM  = "#1A6B72"   # verde azulado — configuración con memoria
COLOR_CTRL = "#999999"   # gris          — configuración sin memoria

FIGURES_DIR = "figures"

def load(csv_path):
    df   = pd.read_csv(csv_path)
    df["correct_bin"] = (df["outcome"] == "correcto").astype(int)
    mem  = df[df["config"] == "with_memory"].reset_index(drop=True)
    ctrl = df[df["config"] == "without_memory"].reset_index(drop=True)
    os.makedirs(FIGURES_DIR, exist_ok=True)
    return df, mem, ctrl

# ── 1. Boxplot accuracy por episodio ────────────────────────────────────
def fig_boxplot_accuracy(mem, ctrl):
    fig, ax = plt.subplots(figsize=(6, 4))
    data   = [mem["correct_bin"].values, ctrl["correct_bin"].values]
    labels = ["Con memoria", "Sin memoria"]
    bp = ax.boxplot(data, patch_artist=True, widths=0.4,
                    medianprops=dict(color="white", linewidth=2))
    bp["boxes"][0].set_facecolor(COLOR_MEM)
    bp["boxes"][1].set_facecolor(COLOR_CTRL)
    for whisker in bp["whiskers"]:
        whisker.set_color("#555555")
    for cap in bp["caps"]:
        cap.set_color("#555555")
    ax.set_xticks([1, 2])
    ax.set_xticklabels(labels)
    ax.set_ylabel("Decisión correcta (1=sí, 0=no)")
    ax.set_title("Figura 1 — Distribución de aciertos por configuración")
    acc_m = mem["correct_bin"].mean()
    acc_c = ctrl["correct_bin"].mean()
    ax.text(1, acc_m + 0.03, f"{acc_m:.2f}", ha="center", color=COLOR_MEM, fontweight="bold")
    ax.text(2, acc_c + 0.03, f"{acc_c:.2f}", ha="center", color=COLOR_CTRL, fontweight="bold")
    path = f"{FIGURES_DIR}/boxplot_accuracy.png"
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    print(f"  [OK] {path}")

# ── 2. Evolución temporal — accuracy acumulada ───────────────────────────
def fig_evolucion_temporal(mem, ctrl):
    fig, ax = plt.subplots(figsize=(9, 4))
    acc_mem  = mem["correct_bin"].expanding().mean().values
    acc_ctrl = ctrl["correct_bin"].expanding().mean().values
    x = range(1, len(acc_mem) + 1)
    ax.plot(x, acc_mem,  color=COLOR_MEM,  linewidth=2, label="Con memoria")
    ax.plot(x, acc_ctrl, color=COLOR_CTRL, linewidth=2, linestyle="--", label="Sin memoria")
    ax.axvline(x=10, color="#DDDDDD", linestyle=":", linewidth=1.2)
    ax.axvline(x=25, color="#DDDDDD", linestyle=":", linewidth=1.2)
    ax.axvline(x=40, color="#DDDDDD", linestyle=":", linewidth=1.2)
    ax.text(10.5, 0.5, "1ª repetición", fontsize=8, color="#999999", rotation=90, va="center")
    ax.text(25.5, 0.5, "2ª repetición", fontsize=8, color="#999999", rotation=90, va="center")
    ax.text(40.5, 0.5, "3ª repetición", fontsize=8, color="#999999", rotation=90, va="center")
    ax.set_xlabel("Número de episodio")
    ax.set_ylabel("Accuracy acumulada")
    ax.set_title("Figura 2 — Evolución de la accuracy acumulada por episodio")
    ax.set_ylim(0, 1.05)
    ax.legend(frameon=False)
    path = f"{FIGURES_DIR}/evolucion_temporal.png"
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    print(f"  [OK] {path}")

# ── 3. Heatmap de decisiones por tipo de caso ───────────────────────────
def fig_heatmap_decisiones(df):
    fig, axes = plt.subplots(1, 2, figsize=(12, 5), sharey=True)
    decisions = ["A1", "A2", "A3", "A4"]
    for ax, config, title in zip(
        axes,
        ["with_memory", "without_memory"],
        ["Con memoria", "Sin memoria"]
    ):
        sub = df[df["config"] == config]
        pivot = pd.crosstab(sub["case_type"], sub["decision_agent"])
        for d in decisions:
            if d not in pivot.columns:
                pivot[d] = 0
        pivot = pivot[decisions]
        sns.heatmap(pivot, ax=ax, annot=True, fmt="d", cmap="Blues",
                    linewidths=0.5, cbar=False)
        ax.set_title(f"Figura 3 — Decisiones ({title})")
        ax.set_xlabel("Acción del agente")
        ax.set_ylabel("Tipo de caso" if ax == axes[0] else "")
    path = f"{FIGURES_DIR}/heatmap_decisiones.png"
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    print(f"  [OK] {path}")

# ── 4. Aprendizaje VIP por cuartos ──────────────────────────────────────
def fig_vip_aprendizaje(mem, ctrl):
    def quarters(df):
        vip = df[df["customer_tier"] == "VIP"].reset_index(drop=True)
        if len(vip) < 4:
            return [None, None, None, None]
        n = len(vip)
        q = n // 4
        result = []
        for i in range(4):
            s = i * q
            e = (i + 1) * q if i < 3 else n
            result.append(vip.iloc[s:e]["correct_bin"].mean())
        return result

    q_mem  = quarters(mem)
    q_ctrl = quarters(ctrl)

    x      = np.arange(1, 5)
    width  = 0.35
    fig, ax = plt.subplots(figsize=(7, 4))

    q_mem_valid  = [v if v is not None else 0 for v in q_mem]
    q_ctrl_valid = [v if v is not None else 0 for v in q_ctrl]

    ax.bar(x - width/2, q_mem_valid,  width, color=COLOR_MEM,  label="Con memoria",  alpha=0.9)
    ax.bar(x + width/2, q_ctrl_valid, width, color=COLOR_CTRL, label="Sin memoria", alpha=0.9)
    ax.set_xlabel("Cuarto del experimento")
    ax.set_ylabel("Accuracy en casos VIP")
    ax.set_title("Figura 4 — Aprendizaje de la excepción VIP por cuartos")
    ax.set_xticks(x)
    ax.set_xticklabels(["Cuarto 1\n(0–25%)", "Cuarto 2\n(25–50%)",
                         "Cuarto 3\n(50–75%)", "Cuarto 4\n(75–100%)"])
    ax.set_ylim(0, 1.15)
    ax.legend(frameon=False)
    for xi, ym, yc in zip(x, q_mem_valid, q_ctrl_valid):
        ax.text(xi - width/2, ym + 0.03, f"{ym:.2f}", ha="center", fontsize=9, color=COLOR_MEM)
        ax.text(xi + width/2, yc + 0.03, f"{yc:.2f}", ha="center", fontsize=9, color="#555555")
    path = f"{FIGURES_DIR}/vip_aprendizaje.png"
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    print(f"  [OK] {path}")

# ── 5. TMD comparativo ──────────────────────────────────────────────────
def fig_tmd_comparativo(mem, ctrl):
    fig, ax = plt.subplots(figsize=(9, 4))
    ax.plot(range(1, len(mem)+1),  mem["decision_time_s"],
            color=COLOR_MEM,  alpha=0.7, linewidth=1.5, label="Con memoria")
    ax.plot(range(1, len(ctrl)+1), ctrl["decision_time_s"],
            color=COLOR_CTRL, alpha=0.7, linewidth=1.5, linestyle="--", label="Sin memoria")
    tmd_m = mem["decision_time_s"].mean()
    tmd_c = ctrl["decision_time_s"].mean()
    ax.axhline(tmd_m, color=COLOR_MEM,  linestyle=":", linewidth=1,
               label=f"Media con memoria: {tmd_m:.2f}s")
    ax.axhline(tmd_c, color=COLOR_CTRL, linestyle=":", linewidth=1,
               label=f"Media sin memoria: {tmd_c:.2f}s")
    ax.set_xlabel("Número de episodio")
    ax.set_ylabel("Tiempo de decisión (segundos)")
    ax.set_title("Figura 5 — Tiempo medio de decisión por episodio")
    ax.legend(frameon=False, fontsize=9)
    path = f"{FIGURES_DIR}/tmd_comparativo.png"
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    print(f"  [OK] {path}")

# ── Main ─────────────────────────────────────────────────────────────────
def main():
    if len(sys.argv) < 2:
        print("Uso: python analysis/visualizaciones.py <ruta_al_csv>")
        sys.exit(1)

    csv_path = sys.argv[1]
    print(f"\nGenerando visualizaciones desde: {csv_path}\n")
    df, mem, ctrl = load(csv_path)

    fig_boxplot_accuracy(mem, ctrl)
    fig_evolucion_temporal(mem, ctrl)
    fig_heatmap_decisiones(df)
    fig_vip_aprendizaje(mem, ctrl)
    fig_tmd_comparativo(mem, ctrl)

    print(f"\nListo. Las 5 figuras están en la carpeta '{FIGURES_DIR}/'")
    print("Adjúntalas al capítulo de resultados del TFE.")

if __name__ == "__main__":
    main()
