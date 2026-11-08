"""Run every study design again on the coarse M1 mesh, for the multi-fidelity surrogate."""
import os
import sys
import pandas as pd

sys.path.insert(0, 'src')
from run_case import run_case

OUT = 'results_M1.csv'
M1 = (2.0, 2.0)

designs = pd.read_csv('designs.csv')
done = set(pd.read_csv(OUT)['run_id']) if os.path.exists(OUT) else set()

for _, design in designs.iterrows():
    run_id = f"{design['run_id']}_M1"
    if run_id in done:
        continue
    try:
        n, u = int(design['n_channels']), float(design['u_in'])
        result = run_case(run_id, n, u, mesh=M1)
        if not result['converged']:
            result = run_case(run_id, n, u, mesh=M1, travel=4.5)
        pd.DataFrame([result]).to_csv(OUT, mode='a', header=not os.path.exists(OUT), index=False)
        print(f"{run_id}: dp {result['dp']:.2f} Pa, T max {result['T_max']:.2f} \u00b0C, "
              f"converged {result['converged']}, {result['minutes']:.1f} min", flush=True)
    except Exception as error:
        print(f"{run_id} failed: {error}", flush=True)
        with open('failed_runs_M1.log', 'a') as log:
            log.write(f"{run_id}: {error}\n")