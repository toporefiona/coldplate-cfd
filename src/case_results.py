"""Read a finished cold plate case and print its key results."""
import os
import re
import sys
import numpy as np
from config import load_settings, channel_width

MM = 0.001


def read_list(path):
    """Read the main list from an OpenFOAM file (a field or a mesh file)."""
    text = open(path).read()
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.S) #these lines remove comments
    text = re.sub(r'//.*', '', text) #skips the FoamFile header
    text = text[text.index('}') + 1:]
    if 'internalField' in text:
        text = text[text.index('internalField'):]
    start = re.search(r'(\d+)\s*\(', text) #finds the list's length
    n = int(start.group(1))
    body = text[start.end():]
    if body.lstrip().startswith('('): #reads the values inside the brackets
        rows = re.findall(r'\(([^()]*)\)', body)[:n]
        return np.array([[float(v) for v in row.split()] for row in rows])
    if re.match(r'\s*\d+\s*\(', body):
        rows = re.findall(r'\d+\s*\(([^()]*)\)', body)[:n]
        return [[int(v) for v in row.split()] for row in rows]
    return np.array(body[:body.index(')')].split(), dtype=float)[:n]


def patch_range(case, name): #reads constant/polyMesh/boundary and finds where a patch’s faces start (startFace) and how many there are (nFaces)
    """First face number and number of faces of a boundary patch."""
    text = open(f'{case}/constant/polyMesh/boundary').read()
    block = re.search(name + r'\s*\{([^}]*)\}', text).group(1)
    n = int(re.search(r'nFaces\s+(\d+)', block).group(1))
    start = int(re.search(r'startFace\s+(\d+)', block).group(1))
    return start, n


def patch_values(path, name, n_faces): #reads the values a field file stores on one patch. If they’re all the same, OpenFOAM writes uniform and a single number, so the last two lines turn that into a full lis
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


case = sys.argv[1]
n_channels = int(sys.argv[2])
plate = load_settings()['plate']

times = [t for t in os.listdir(case) if re.fullmatch(r'\d+(\.\d+)?', t) and t != '0'] #lists the time folders
times = sorted(times, key=float)
time = times[-1]

points = read_list(f'{case}/constant/polyMesh/points') #these are all the mesh properties
faces = read_list(f'{case}/constant/polyMesh/faces')
owner = read_list(f'{case}/constant/polyMesh/owner').astype(int)
neighbour = read_list(f'{case}/constant/polyMesh/neighbour').astype(int)
n_cells = owner.max() + 1
n_internal = len(neighbour)

face_centres = np.array([points[f].mean(axis=0) for f in faces]) #takes the average of each face's corners, which gives the centre
cell_sum = np.zeros((n_cells, 3)) #all of these average the face centres around each cell to get the cell centres
cell_count = np.zeros(n_cells)
np.add.at(cell_sum, owner, face_centres[:len(owner)])
np.add.at(cell_count, owner, 1)
np.add.at(cell_sum, neighbour, face_centres[:n_internal])
np.add.at(cell_count, neighbour, 1)
cell_centres = cell_sum / cell_count[:, None]

in_start, in_n = patch_range(case, 'inlet')
inlet_cells = owner[in_start:in_start + in_n]
dp = read_list(f'{case}/{time}/p')[inlet_cells].mean() * 997 #the avarage p in those cells
dp_before = read_list(f'{case}/{times[-2]}/p')[inlet_cells].mean() * 997 if len(times) > 1 else dp #to see whether the pressure is still changing
phi = read_list(f'{case}/{time}/phi') #is the flow through every face

cut = plate['inlet_header'] * MM + 0.5 * (plate['length'] - plate['inlet_header'] - plate['outlet_header']) * MM #the x position halfway along the channels (200 mm)
left = cell_centres[:n_cells, 0] < cut
own_left = left[owner[:n_internal]]
nei_left = left[neighbour]
crossing = own_left != nei_left #finds the faces with one cell on each side of the cut. Together, these faces form a wall across the plate
flux = np.where(own_left, phi, -phi)[crossing] #the flow through each of these faces
y = face_centres[:n_internal][crossing, 1] #the height of each crossing face

w = channel_width(n_channels, plate) #it adds up the flux of the faces inside each channel's y range
flows = []
for i in range(n_channels):
    y_bottom = (plate['edge_margin'] + i * (w + plate['wall'])) * MM
    y_top = y_bottom + w * MM
    flows.append(flux[(y >= y_bottom) & (y <= y_top)].sum())
flows = np.array(flows)

inlet_flow = -patch_values(f'{case}/{time}/phi', 'inlet', in_n).sum() #they add up excatly to the inlet flow

print(f'Case:      {case}  (iteration {time}, {n_cells} cells)')
print(f'Delta p:   {dp:.2f} Pa  (change since iteration {times[-2] if len(times) > 1 else time}: {(dp - dp_before) / dp * 100:+.3f}%)')
print(f'Flow check: channels {flows.sum():.4e}, inlet {inlet_flow:.4e} m3/s')
print('Flow split: ' + '  '.join(f'{q / flows.sum() * 100:.1f}%' for q in flows))
print(f'Lowest / highest: {flows.min() / flows.max():.3f}')

if os.path.exists(f'{case}/{time}/T'): #If there's a T file: T max is the hottest cell, and T outlet is the flow weighted outlet temperature (each outlet face's T x its flow, divided by the total flow)
    T = read_list(f'{case}/{time}/T')
    out_start, out_n = patch_range(case, 'outlet')
    out_phi = patch_values(f'{case}/{time}/phi', 'outlet', out_n)
    out_T = T[owner[out_start:out_start + out_n]]
    print(f'T max:     {T.max():.2f} C')
    print(f'T outlet:  {(out_T * out_phi).sum() / out_phi.sum():.2f} C (flow weighted)')
else:
    print('T:         not found in this time folder')
