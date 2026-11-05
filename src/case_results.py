"""Read a finished cold plate case and return (or print) its key results."""
import os
import re
import sys
import numpy as np
from config import load_settings, channel_width

MM = 0.001


def read_list(path):
    """Read the main list from an OpenFOAM file (a field or a mesh file)."""
    text = open(path).read()
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.S)
    text = re.sub(r'//.*', '', text)
    text = text[text.index('}') + 1:]
    if 'internalField' in text:
        text = text[text.index('internalField'):]
    start = re.search(r'(\d+)\s*\(', text)
    n = int(start.group(1))
    body = text[start.end():]
    if body.lstrip().startswith('('):
        rows = re.findall(r'\(([^()]*)\)', body)[:n]
        return np.array([[float(v) for v in row.split()] for row in rows])
    if re.match(r'\s*\d+\s*\(', body):
        rows = re.findall(r'\d+\s*\(([^()]*)\)', body)[:n]
        return [[int(v) for v in row.split()] for row in rows]
    return np.array(body[:body.index(')')].split(), dtype=float)[:n]


def patch_range(case, name):
    """First face number and number of faces of a boundary patch."""
    text = open(f'{case}/constant/polyMesh/boundary').read()
    block = re.search(name + r'\s*\{([^}]*)\}', text).group(1)
    n = int(re.search(r'nFaces\s+(\d+)', block).group(1))
    start = int(re.search(r'startFace\s+(\d+)', block).group(1))
    return start, n


def patch_values(path, name, n_faces):
    """Values written on one boundary patch of a field file."""
    text = open(path).read()
    block = text[text.index('boundaryField'):]
    block = block[re.search(r'\b' + name + r'\s*\{', block).end():]
    block = block[:block.index('}')]
    if 'nonuniform' in block:
        body = block[block.index('(') + 1:block.rindex(')')]
        return np.array(body.split(), dtype=float)
    value = float(re.search(r'uniform\s+([^;]+);', block).group(1))
    return np.full(n_faces, value)


def get_results(case, n_channels):
    """Return the key results of a finished case as a dictionary."""
    plate = load_settings()['plate']

    times = [t for t in os.listdir(case) if re.fullmatch(r'\d+(\.\d+)?', t) and t != '0']
    times = sorted(times, key=float)
    time = times[-1]

    points = read_list(f'{case}/constant/polyMesh/points')
    faces = read_list(f'{case}/constant/polyMesh/faces')
    owner = read_list(f'{case}/constant/polyMesh/owner').astype(int)
    neighbour = read_list(f'{case}/constant/polyMesh/neighbour').astype(int)
    n_cells = owner.max() + 1
    n_internal = len(neighbour)

    face_centres = np.array([points[f].mean(axis=0) for f in faces])
    cell_sum = np.zeros((n_cells, 3))
    cell_count = np.zeros(n_cells)
    np.add.at(cell_sum, owner, face_centres[:len(owner)])
    np.add.at(cell_count, owner, 1)
    np.add.at(cell_sum, neighbour, face_centres[:n_internal])
    np.add.at(cell_count, neighbour, 1)
    cell_centres = cell_sum / cell_count[:, None]

    in_start, in_n = patch_range(case, 'inlet')
    inlet_cells = owner[in_start:in_start + in_n]
    dp = read_list(f'{case}/{time}/p')[inlet_cells].mean() * 997
    dp_before = read_list(f'{case}/{times[-2]}/p')[inlet_cells].mean() * 997 if len(times) > 1 else dp
    phi = read_list(f'{case}/{time}/phi')

    cut = plate['inlet_header'] * MM + 0.5 * (plate['length'] - plate['inlet_header'] - plate['outlet_header']) * MM
    left = cell_centres[:n_cells, 0] < cut
    own_left = left[owner[:n_internal]]
    nei_left = left[neighbour]
    crossing = own_left != nei_left
    flux = np.where(own_left, phi, -phi)[crossing]
    y = face_centres[:n_internal][crossing, 1]

    w = channel_width(n_channels, plate)
    flows = []
    for i in range(n_channels):
        y_bottom = (plate['edge_margin'] + i * (w + plate['wall'])) * MM
        y_top = y_bottom + w * MM
        flows.append(flux[(y >= y_bottom) & (y <= y_top)].sum())
    flows = np.array(flows)

    inlet_flow = -patch_values(f'{case}/{time}/phi', 'inlet', in_n).sum()

    results = {
        'time': time,
        'previous_time': times[-2] if len(times) > 1 else time,
        'cells': int(n_cells),
        'dp': dp,
        'dp_change': (dp - dp_before) / dp * 100,
        'channel_flow': flows.sum(),
        'inlet_flow': inlet_flow,
        'split': flows / flows.sum() * 100,
        'uniformity': flows.min() / flows.max(),
        'T_max': None,
        'T_out': None,
    }

    if os.path.exists(f'{case}/{time}/T'):
        T = read_list(f'{case}/{time}/T')
        out_start, out_n = patch_range(case, 'outlet')
        out_phi = patch_values(f'{case}/{time}/phi', 'outlet', out_n)
        out_T = T[owner[out_start:out_start + out_n]]
        results['T_max'] = T.max()
        results['T_out'] = (out_T * out_phi).sum() / out_phi.sum()

    return results


if __name__ == '__main__':
    case = sys.argv[1]
    r = get_results(case, int(sys.argv[2]))
    print(f'Case:      {case}  (iteration {r["time"]}, {r["cells"]} cells)')
    print(f'Delta p:   {r["dp"]:.2f} Pa  (change since iteration {r["previous_time"]}: {r["dp_change"]:+.3f}%)')
    print(f'Flow check: channels {r["channel_flow"]:.4e}, inlet {r["inlet_flow"]:.4e} m3/s')
    print('Flow split: ' + '  '.join(f'{s:.1f}%' for s in r['split']))
    print(f'Lowest / highest: {r["uniformity"]:.3f}')
    if r['T_max'] is None:
        print('T:         not found in this time folder')
    else:
        print(f'T max:     {r["T_max"]:.2f} C')
        print(f'T outlet:  {r["T_out"]:.2f} C (flow weighted)')
