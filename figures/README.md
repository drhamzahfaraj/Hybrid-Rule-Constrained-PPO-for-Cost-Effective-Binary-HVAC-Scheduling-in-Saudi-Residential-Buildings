# Publication Figures

This directory contains scripts and outputs for all figures in the paper.

## Figure List

1. **`fig_cost_models.pdf`** (Figure 1): Comparison of Models L, E, and S vs. cumulative energy
2. **`fig_configs.pdf`** (Figure 2): Zone topology diagrams (1×1, 1×4, 2×2)
3. **`fig_savings.pdf`** (Figure 3): Monthly cost trajectories for Riyadh and Jeddah
4. **`fig_ablation.pdf`**: Ablation study visualizations

## Reproducing Figures

Run the following command to regenerate all figures:

```bash
python generate_figures.py --output-dir .
```

Individual figures can be generated:

```bash
python generate_figures.py --figure cost_models --output-dir .
python generate_figures.py --figure savings --output-dir .
```

## Figure Specifications

- **Format**: PDF (vector graphics for publication)
- **Resolution**: 300 DPI (when rasterized)
- **Fonts**: LaTeX-compatible (Computer Modern)
- **Color scheme**: Colorblind-friendly palette

## Dependencies

The figure generation script requires:

```bash
pip install matplotlib seaborn tikzplotlib pandas numpy
```

## LaTeX Integration

Figures are designed to be included in LaTeX documents with:

```latex
\begin{figure}[!t]
\centering
\includegraphics[width=0.9\linewidth]{figures/fig_cost_models.pdf}
\caption{Comparison of cost models...}
\label{fig:costmodels}
\end{figure}
```

## Customization

Edit `generate_figures.py` to modify:
- Figure dimensions
- Color schemes
- Font sizes
- Data sources