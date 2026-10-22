"""Makale grafikleri: Linux/Windows gecikme CDF'i ve hls4ml tasarim noktalari.

Kullanim:  python figures/src/grafikler.py
Cikti   :  figures/lat_cdf_os.pdf, figures/hls4ml_points.pdf
Veri    :  D:/30-akademik/hft-nn/hft-vitis/pc_test (native Linux ve Windows host koşumlari)
"""
import csv
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.dirname(HERE)
PC = "D:/30-akademik/hft-nn/hft-vitis/pc_test"

# Kategorik sira sabit: mavi, turuncu, aqua, sari (dataviz referans paleti)
C = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]
INK, MUTED, GRID = "#222222", "#666666", "#dddddd"

plt.rcParams.update({
    "font.family": "serif", "font.serif": ["Times New Roman", "Times", "DejaVu Serif"],
    "mathtext.fontset": "stix", "font.size": 9, "axes.labelsize": 9,
    "xtick.labelsize": 8.5, "ytick.labelsize": 8.5, "legend.fontsize": 8.5,
    "axes.edgecolor": MUTED, "axes.linewidth": 0.6, "xtick.color": MUTED,
    "ytick.color": MUTED, "axes.labelcolor": INK, "pdf.fonttype": 42,
})
# Iki sekil de iki sutunu kaplar (figure*); 1:1 basildigi icin yazi boyu metinle uyumlu.
TEXT_W = 6.40  # inch, sn-jnl iicol metin genisligi


def latencies(path):
    with open(path, newline="") as f:
        return sorted(float(r["Latency_us"]) for r in csv.DictReader(f))


def cdf_plot():
    runs = [("Linux host", C[0], f"{PC}/linux/native_64_32_16.csv"),
            ("Windows host", C[1], f"{PC}/win_shape_64_32_16.csv")]
    fig, ax = plt.subplots(figsize=(TEXT_W, 2.45))
    for name, col, path in runs:
        x = latencies(path)
        n = len(x)
        ax.step(x, [(i + 1) / n for i in range(n)], where="post", color=col, lw=1.6)
        med = x[n // 2]
        linux = name.startswith("Linux")
        # etiket egrilerin arasindaki bos bolgede: Linux sagda, Windows solda
        ax.annotate(f"{name}\nmedian {med:.1f} µs", xy=(med, 0.5),
                    xytext=(med * 1.45, 0.30) if linux else (med / 1.45, 0.70),
                    fontsize=9, color=INK, ha="left" if linux else "right", va="center",
                    arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.6))
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
ENGINE_DSP = 192
MARK = ["o", "s", "^", "D"]


def hls_plot():
    # Ag basina bir panel: hls4ml egrisi (her nokta ayri bitstream) ve motorun tek noktasi
    fig, axs = plt.subplots(2, 2, figsize=(TEXT_W, 4.3), sharex=True, sharey=True)
    for k, (ax, (net, pts)) in enumerate(zip(axs.flat, HLS.items())):
        ax.plot([p[1] for p in pts], [p[2] for p in pts], color=C[0], lw=1.0, zorder=2)
        for rf, dsp, ns, ok in pts:
            ax.scatter(dsp, ns, s=30, marker="o", linewidths=1.1,
                       facecolor=C[0] if ok else "white", edgecolor=C[0], zorder=3)
        ax.scatter(ENGINE_DSP, ENGINE_NS[k], s=60, marker="s", facecolor=C[1],
                   edgecolor=INK, linewidths=0.9, zorder=4)
        ax.annotate(f"{ENGINE_NS[k]} ns", xy=(ENGINE_DSP, ENGINE_NS[k]),
                    xytext=(-8, 0), textcoords="offset points", fontsize=8.5,
                    color=INK, ha="right", va="center")
        ax.axvline(220, color=MUTED, lw=0.6, ls=":")
        ax.set_title(net, fontsize=9, color=INK, pad=3)
        ax.set_yscale("log")
        ax.set_xlim(0, 235)
        ax.set_ylim(350, 6500)
        ax.set_yticks([400, 1000, 2000, 4000])
        ax.set_yticklabels(["400", "1000", "2000", "4000"])
        ax.minorticks_off()
        ax.grid(True, which="major", color=GRID, lw=0.5)
        ax.set_axisbelow(True)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
    axs[0, 0].text(218, 5600, "DSP limit", fontsize=7.5, color=MUTED, ha="right", va="top")
    for ax in axs[1]:
        ax.set_xlabel("DSP slices")
    for ax in axs[:, 0]:
        ax.set_ylabel("Latency (ns)")
    h = [Line2D([], [], marker="o", color=C[0], lw=1.0, markersize=5.5,
                markerfacecolor=C[0], label="hls4ml, meets 125 MHz"),
         Line2D([], [], marker="o", color=C[0], lw=1.0, markersize=5.5,
                markerfacecolor="white", label="hls4ml, misses 125 MHz"),
         Line2D([], [], marker="s", color=INK, lw=0, markersize=6.5,
                markerfacecolor=C[1], markeredgewidth=0.9,
                label="this engine (one bitstream for all four)")]
    fig.legend(handles=h, loc="upper center", ncol=3, frameon=False,
               bbox_to_anchor=(0.5, 1.0), handlelength=1.8)
    fig.tight_layout(pad=0.3, rect=(0, 0, 1, 0.94))
    fig.savefig(os.path.join(OUT, "hls4ml_points.pdf"))
    plt.close(fig)


if __name__ == "__main__":
    cdf_plot()
    hls_plot()
    print("yazildi:", os.path.join(OUT, "lat_cdf_os.pdf"), os.path.join(OUT, "hls4ml_points.pdf"))
