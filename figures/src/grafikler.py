"""Makale grafikleri: Linux/Windows gecikme CDF'i ve hls4ml tasarim noktalari.

Kullanim:  python figures/src/grafikler.py
Cikti   :  figures/lat_cdf_os.pdf, figures/hls4ml_points.pdf
Veri    :  D:/vitis_projects/pc_test (native Linux ve Windows host koşumlari)
"""
import csv
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.dirname(HERE)
PC = "D:/vitis_projects/pc_test"

# Kategorik sira sabit: mavi, turuncu, aqua, sari (dataviz referans paleti)
C = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]
INK, MUTED, GRID = "#222222", "#666666", "#dddddd"

plt.rcParams.update({
    "font.family": "serif", "font.serif": ["Times New Roman", "Times", "DejaVu Serif"],
    "mathtext.fontset": "stix", "font.size": 8, "axes.labelsize": 8,
    "xtick.labelsize": 7, "ytick.labelsize": 7, "legend.fontsize": 7,
    "axes.edgecolor": MUTED, "axes.linewidth": 0.6, "xtick.color": MUTED,
    "ytick.color": MUTED, "axes.labelcolor": INK, "pdf.fonttype": 42,
})
COL_W = 3.30  # inch, iki sutunlu duzende bir sutun


def latencies(path):
    with open(path, newline="") as f:
        return sorted(float(r["Latency_us"]) for r in csv.DictReader(f))


def cdf_plot():
    runs = [("Linux host", C[0], f"{PC}/linux/native_64_32_16.csv"),
            ("Windows host", C[1], f"{PC}/win_shape_64_32_16.csv")]
    fig, ax = plt.subplots(figsize=(COL_W, 2.05))
    for name, col, path in runs:
        x = latencies(path)
        n = len(x)
        ax.step(x, [(i + 1) / n for i in range(n)], where="post", color=col, lw=1.4)
        med = x[n // 2]
        linux = name.startswith("Linux")
        # etiket egrilerin arasindaki bos bolgede: Linux sagda, Windows solda
        ax.annotate(f"{name}\nmedian {med:.1f} µs", xy=(med, 0.5),
                    xytext=(med * 1.45, 0.30) if linux else (med / 1.45, 0.70),
                    fontsize=7, color=INK, ha="left" if linux else "right", va="center",
                    arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.5))
    ax.set_xscale("log")
    ax.set_xlim(40, 5000)
    ax.set_xticks([50, 100, 200, 500, 1000, 2000, 5000])
    ax.set_xticklabels(["50", "100", "200", "500", "1000", "2000", "5000"])
    ax.minorticks_off()
    ax.set_ylim(0, 1.0)
    ax.set_xlabel("End-to-end latency (µs, log scale)")
    ax.set_ylabel("Cumulative fraction")
    ax.grid(True, which="major", color=GRID, lw=0.5)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    fig.tight_layout(pad=0.3)
    fig.savefig(os.path.join(OUT, "lat_cdf_os.pdf"))
    plt.close(fig)


# Tablo hls4ml: (ag, RF, DSP, zaman ns, 125 MHz kapatti mi); sigmayanlar yok
HLS = {
    "40-10-16-8-3": [(8, 84, 457, True), (16, 39, 734, False), (32, 19, 1344, False),
                     (64, 10, 2766, False), (128, 8, 5201, False)],
    "40-32-16-8-3": [(8, 201, 456, True), (16, 108, 654, True), (32, 53, 1326, False),
                     (64, 27, 2493, False), (128, 14, 4676, False)],
    "40-64-32-16-3": [(16, 220, 1026, False), (32, 148, 1146, False),
                      (64, 73, 2630, False), (128, 37, 4691, False)],
    "40-64-64-32-3": [(32, 220, 1758, False), (64, 131, 2531, False),
                      (128, 65, 4841, False)],
}
ENGINE_NS = [560, 616, 768, 896]
MARK = ["o", "s", "^", "D"]


def hls_plot():
    fig, ax = plt.subplots(figsize=(COL_W, 2.45))
    for k, (net, pts) in enumerate(HLS.items()):
        for rf, dsp, ns, ok in pts:
            ax.scatter(dsp, ns, s=26, marker=MARK[k], linewidths=1.0,
                       facecolor=C[k] if ok else "white", edgecolor=C[k], zorder=3)
        ax.plot([p[1] for p in pts], [p[2] for p in pts], color=C[k], lw=0.7,
                alpha=0.6, zorder=2)
        # motor: ayni ag, 192 DSP
        ax.scatter(192, ENGINE_NS[k], s=70, marker="*", color=C[k],
                   edgecolor=INK, linewidths=0.5, zorder=4)
    ax.axvline(220, color=MUTED, lw=0.6, ls=":")
    ax.text(216, 5600, "device\nDSP limit", fontsize=6.5, color=MUTED, ha="right", va="top")
    ax.set_yscale("log")
    ax.set_xlim(0, 235)
    ax.set_ylim(350, 6500)
    ax.set_yticks([400, 600, 1000, 2000, 4000])
    ax.set_yticklabels(["400", "600", "1000", "2000", "4000"])
    ax.minorticks_off()
    ax.set_xlabel("DSP slices")
    ax.set_ylabel("Latency at $f_{\\max}$ (ns, log scale)")
    ax.grid(True, which="major", color=GRID, lw=0.5)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    from matplotlib.lines import Line2D
    h = [Line2D([], [], marker=MARK[k], color=C[k], lw=0.7, markersize=4.5,
                markerfacecolor=C[k], label=net) for k, net in enumerate(HLS)]
    h += [Line2D([], [], marker="*", color=INK, lw=0, markersize=8, label="this engine"),
          Line2D([], [], marker="o", color=MUTED, lw=0, markersize=4.5,
                 markerfacecolor="white", label="hls4ml, misses 125 MHz")]
    ax.legend(handles=h, loc="upper center", ncol=2, frameon=False,
              bbox_to_anchor=(0.5, 1.33), handlelength=1.6, columnspacing=1.0)
    fig.tight_layout(pad=0.3)
    fig.savefig(os.path.join(OUT, "hls4ml_points.pdf"))
    plt.close(fig)


if __name__ == "__main__":
    cdf_plot()
    hls_plot()
    print("yazildi:", os.path.join(OUT, "lat_cdf_os.pdf"), os.path.join(OUT, "hls4ml_points.pdf"))
