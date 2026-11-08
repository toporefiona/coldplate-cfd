"""Run one cold plate design from start to finish and return its results."""
import shutil
import subprocess
import sys
import time
from pathlib import Path
from config import load_settings, channel_width
from geometry import build_plate
from case_results import get_results

RHO = 997    # density of water, kg/m3
CP = 4180    # specific heat of water, J/(kg K)
MM = 0.001


def run(command, case, log):
    """Run a shell command inside a case folder, saving its output to a log file."""
    with open(Path(case) / log, 'a') as f:
        subprocess.run(command, cwd=case, shell=True, check=True,
                       stdout=f, stderr=subprocess.STDOUT)


def run_case(run_id, n_channels, u_in, cores=6, travel=1.5, mesh=None):
    """Build, run and measure one design. Returns a dictionary of results."""
    settings = load_settings()
    if mesh:
        settings['mesh']['cell_size'], settings['mesh']['wall_cell_size'] = mesh
    plate = settings['plate']
    physics = settings['physics']
    case = Path('runs') / run_id
    start = time.time()
    shutil.rmtree(case, ignore_errors=True)
    shutil.rmtree(Path('runs') / f'{run_id}_heat', ignore_errors=True)

    # 1. Geometry, mesh and case setup
    case.mkdir(parents=True, exist_ok=True)
    mesh_file = case / 'plate.msh'
    build_plate(n_channels, settings, str(mesh_file))
    subprocess.run(['bash', 'src/make_case.sh', str(mesh_file), run_id],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # 2. Switch to the pseudo-transient settings and set this design's flow
    for name in ['controlDict', 'fvSchemes', 'fvSolution', 'decomposeParDict']:
        shutil.copy(Path('case_template_pseudo') / name, case / 'system' / name)
        end_time = round(travel / u_in, 2)
    run(f'foamDictionary 0/U -entry boundaryField/inlet/value -set "uniform ({u_in} 0 0)"', case, 'log.setup')
    run(f'foamDictionary system/controlDict -entry endTime -set {end_time}', case, 'log.setup')
    run(f'foamDictionary system/controlDict -entry writeInterval -set {end_time / 5:.3f}', case, 'log.setup')
    run(f'foamDictionary system/decomposeParDict -entry numberOfSubdomains -set {cores}', case, 'log.setup')

    # 3. Flow: pseudo-transient on several cores
    run('decomposePar', case, 'log.decomposePar')
    run(f'mpirun -np {cores} pimpleFoam -parallel', case, 'log.pimpleFoam')
    run('reconstructPar', case, 'log.reconstructPar')
    run('rm -rf processor*', case, 'log.cleanup')

    # 4. Temperature on the frozen flow, with the battery heat fixed in watts
    channel_length = plate['length'] - plate['inlet_header'] - plate['outlet_header']
    water_area = n_channels * channel_width(n_channels, plate) * channel_length * MM * MM
    source = physics['heat'] / (RHO * CP * physics['depth'] * MM * water_area)
    subprocess.run(['bash', 'src/frozen_T.sh', run_id, f'{run_id}_heat', f'{source:.6f}'],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # 5. Results, with checks
    flow = get_results(str(case), n_channels)
    heat = get_results(f'runs/{run_id}_heat', n_channels)
    flow_rate = u_in * plate['port_width'] * MM * physics['depth'] * MM
    T_out_expected = physics['inlet_T'] + physics['heat'] / (RHO * CP * flow_rate)

    return {
        'run_id': run_id,
        'n_channels': n_channels,
        'u_in': u_in,
        'dp': round(flow['dp'], 3),
        'T_max': round(heat['T_max'], 3),
        'T_out': round(heat['T_out'], 3),
        'T_out_expected': round(T_out_expected, 3),
        'uniformity': round(flow['uniformity'], 4),
        'split': ' '.join(f'{s:.1f}' for s in flow['split']),
        'dp_change': round(flow['dp_change'], 4),
        'flow_error': round((flow['channel_flow'] - flow['inlet_flow']) / flow['inlet_flow'] * 100, 4),
        'converged': abs(flow['dp_change']) < 0.1 and abs(heat['T_out'] - T_out_expected) < 0.05,
        'cells': flow['cells'],
        'minutes': round((time.time() - start) / 60, 1),
    }


if __name__ == '__main__':
    result = run_case(sys.argv[1], int(sys.argv[2]), float(sys.argv[3]))
    for key, value in result.items():
        print(f'{key:15s} {value}')
