"""Portfolio picture: the even design above the starved one, on the same temperature scale."""
import re
import subprocess
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.tri import Triangulation
from matplotlib.colors import LinearSegmentedColormap


def read_internal(path):
    text = Path(path).read_text()
    body = text[text.index('internalField'):text.index('boundaryField')]
    match = re.search(r'List<(\w+)>\s*(\d+)\s*\(', body)
    kind, count = match.group(1), int(match.group(2))
    numbers = re.findall(r'[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?', body[match.end():])
    values = np.array(numbers, dtype=float)
    return values[:3 * count].reshape(count, 3) if kind == 'vector' else values[:count]


def field(case):
    case = Path(case)
    latest = max((p for p in case.iterdir() if re.fullmatch(r'[\d.]+', p.name)), key=lambda p: float(p.name))
    if not (latest / 'C').exists():
        subprocess.run('postProcess -func writeCellCentres -latestTime', shell=True, cwd=case,
                       check=True, stdout=subprocess.DEVNULL)
    centres = read_internal(latest / 'C')
    x, y = centres[:, 0], centres[:, 1]
    if x.max() < 5:
        x, y = 1000 * x, 1000 * y
    grid = Triangulation(x, y)
    tx, ty = x[grid.triangles], y[grid.triangles]
    edges = np.hypot(tx - np.roll(tx, 1, axis=1), ty - np.roll(ty, 1, axis=1))
    grid.set_mask(edges.max(axis=1) > 4)
    return grid, read_internal(latest / 'T')


colours = LinearSegmentedColormap.from_list('plate', ['#0d366b', '#5aa0e6', '#f5d33f', '#f28e2b', '#c0392b'])
designs = [('runs/check_N16_U0113_heat', '16 channels, 0.113 m/s: even cooling'),
           ('runs/run_009_heat', '8 channels, 0.29 m/s: one channel starved of water')]

fig, axes = plt.subplots(2, 1, figsize=(8, 8.5))
for ax, (case, title) in zip(axes, designs):
    grid, T = field(case)
    picture = ax.tripcolor(grid, T, shading='gouraud', cmap=colours, vmin=25, vmax=45)
    ax.set_title(title, fontsize=13, loc='left')
    ax.set_aspect('equal')
    ax.axis('off')
bar = fig.colorbar(picture, ax=axes, orientation='horizontal', fraction=0.04, pad=0.03, extend='max')
bar.set_label('Coolant temperature (\u00b0C)')
fig.savefig('results/card_comparison.png', dpi=200, bbox_inches='tight')
print("Saved results/card_comparison.png")