"""Draw the temperature or velocity field of a finished case as a picture, without ParaView."""
import re
import subprocess
import sys
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


case, field, out = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
low, high = (float(sys.argv[4]), float(sys.argv[5])) if len(sys.argv) > 5 else (None, None)

latest = max((p for p in case.iterdir() if re.fullmatch(r'[\d.]+', p.name)), key=lambda p: float(p.name))
if not (latest / 'C').exists():
    subprocess.run('postProcess -func writeCellCentres -latestTime', shell=True, cwd=case,
                   check=True, stdout=subprocess.DEVNULL)
centres = read_internal(latest / 'C')
x, y = centres[:, 0], centres[:, 1]
if x.max() < 5:
    x, y = 1000 * x, 1000 * y

values = read_internal(latest / field)
if values.ndim == 2:
    values = np.linalg.norm(values, axis=1)

grid = Triangulation(x, y)
tx, ty = x[grid.triangles], y[grid.triangles]
edges = np.hypot(tx - np.roll(tx, 1, axis=1), ty - np.roll(ty, 1, axis=1))
grid.set_mask(edges.max(axis=1) > 4)

colours = LinearSegmentedColormap.from_list('plate', ['#0d366b', '#5aa0e6', '#f5d33f', '#f28e2b', '#c0392b'])

fig, ax = plt.subplots(figsize=(11, 5))
picture = ax.tripcolor(grid, values, shading='gouraud', cmap=colours,
                       vmin=low, vmax=high)
beyond = high is not None and values.max() > high
bar = fig.colorbar(picture, ax=ax, shrink=0.8, extend='max' if beyond else 'neither')
bar.set_label('Temperature (\u00b0C)' if field == 'T' else 'Velocity (m/s)')
ax.set_aspect('equal')
ax.set_xlabel('x (mm)')
ax.set_ylabel('y (mm)')
ax.spines[['top', 'right']].set_visible(False)
fig.tight_layout()
fig.savefig(out, dpi=200)
print(f"Saved {out} (time {latest.name}, {len(values)} cells, {field} from {values.min():.3g} to {values.max():.3g})")