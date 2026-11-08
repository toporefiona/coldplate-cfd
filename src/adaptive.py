"""Adaptive sampling: let the surrogate choose which designs to simulate next."""
import os
import sys
import warnings
import numpy as np
import pandas as pd
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import RBF, WhiteKernel, ConstantKernel

sys.path.insert(0, 'src')
from run_case import run_case

warnings.filterwarnings('ignore')
START, NEW = 10, 8 #start with 10 designs and then add 8 more
OUT = 'adaptive_results.csv'

designs = pd.read_csv('designs.csv')
results = pd.read_csv('results.csv')
data = results if 'set' in results.columns else results.merge(designs[['run_id', 'set']], on='run_id')
pool = data[(data['set'] == 'train') & (data['run_id'] != 'run_009')]
test = data[data['set'] == 'test']
start = pool.iloc[np.random.default_rng(0).choice(len(pool), size=START, replace=False)]


def scale(df):
    return np.column_stack([(df['n_channels'] - 6) / (16 - 6), (df['u_in'] - 0.1) / (0.3 - 0.1)])


def fit(X, y, noise_min=1e-8):
    kernel = (ConstantKernel(1.0) * RBF(length_scale=[0.5, 0.5], length_scale_bounds=(1e-2, 1e2))
              + WhiteKernel(max(1e-4, noise_min), noise_level_bounds=(noise_min, 1e-1)))
    gp = GaussianProcessRegressor(kernel=kernel, normalize_y=True, n_restarts_optimizer=10, random_state=0)
    gp.fit(X, y)
    return gp


def evaluate(train):
    usable = train[train['uniformity'] >= 0.05] #it leaves out any design where a channel is badly starved
    gp_dp = fit(scale(train), np.log(train['dp'])) #the 2 winning models from phase 6
    gp_T = fit(scale(usable), usable['T_max'], noise_min=1e-2)
    dp_error = 100 * np.mean(np.abs(np.exp(gp_dp.predict(scale(test))) - test['dp']) / test['dp']) #the avg error on the 10 test designs
    T_error = np.mean(np.abs(gp_T.predict(scale(test)) - test['T_max']))
    return gp_T, dp_error, T_error


n_values = np.arange(6, 17) #the same 891 possible designs
u_values = np.linspace(0.1, 0.3, 81)
N, U = np.meshgrid(n_values, u_values)
grid = pd.DataFrame({'n_channels': N.ravel(), 'u_in': U.ravel()})

new = pd.read_csv(OUT) if os.path.exists(OUT) else pd.DataFrame()
history = []

for step in range(NEW + 1): #goes round 9 times: once to measure the starting error, then once after each of the 8 new designs.
    train = pd.concat([start, new.iloc[:step]]) #the 10 starting designs plus the new ones
    gp_T, dp_error, T_error = evaluate(train)
    history.append({'simulations': len(train), 'dp_error': dp_error, 'T_error': T_error})
    print(f"{len(train)} simulations: test error \u0394p {dp_error:.1f}%, T max {T_error:.2f} \u00b0C", flush=True)
    if step == NEW: #after the last measurements it stops
        break
    if step < len(new): #if this design was already simulated in an earlier session, skip running it again
        continue
    _, sd = gp_T.predict(scale(grid), return_std=True)
    done = set(zip(train['n_channels'], train['u_in'].round(4)))
    sd[[(n, round(u, 4)) in done for n, u in zip(grid['n_channels'], grid['u_in'])]] = 0
    pick = grid.iloc[np.argmax(sd)] #the design with the biggest uncertainty
    n, u = int(pick['n_channels']), round(float(pick['u_in']), 4)
    print(f"  next: {n} channels at {u} m/s (T max uncertainty \u00b1{2 * sd.max():.2f} \u00b0C)", flush=True)
    result = run_case(f'adapt_{step + 1:02d}', n, u) #runs the CFD on it
    if not result['converged']:
        print("  not converged, running again for longer", flush=True)
        result = run_case(f'adapt_{step + 1:02d}', n, u, travel=4.5)
    new = pd.concat([new, pd.DataFrame([result])], ignore_index=True)
    new.to_csv(OUT, index=False)

pd.DataFrame(history).to_csv('adaptive_history.csv', index=False)
print("\nDesigns the surrogate chose:")
print(new[['run_id', 'n_channels', 'u_in', 'dp', 'T_max', 'uniformity', 'converged']].to_string(index=False))
print("\nFor comparison, random picks in step D: 10 sims 1.38 \u00b0C, 15 sims 1.32, 20 sims 1.16, 25 sims 0.69")