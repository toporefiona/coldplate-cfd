"""Run every design in designs.csv and save the results to results.csv."""
import os
import traceback
import pandas as pd
from run_case import run_case

RESULTS_FILE = 'results.csv'

designs = pd.read_csv('designs.csv')
done = set(pd.read_csv(RESULTS_FILE)['run_id']) if os.path.exists(RESULTS_FILE) else set()

for _, design in designs.iterrows():
    run_id = design['run_id']
    if run_id in done:
        print(f'{run_id}: already done, skipping')
        continue

    print(f'{run_id}: N = {design["n_channels"]}, U = {design["u_in"]} m/s', flush=True)
    try:
        result = run_case(run_id, int(design['n_channels']), float(design['u_in']))
        result['set'] = design['set']
        pd.DataFrame([result]).to_csv(RESULTS_FILE, mode='a', index=False,
                                      header=not os.path.exists(RESULTS_FILE))
        print(f'  done in {result["minutes"]} min: dp = {result["dp"]} Pa, '
              f'T max = {result["T_max"]} C, converged = {result["converged"]}', flush=True)
    except Exception:
        with open('failed_runs.log', 'a') as f:
            f.write(f'{run_id}\n{traceback.format_exc()}\n')
        print('  FAILED, details in failed_runs.log', flush=True)
