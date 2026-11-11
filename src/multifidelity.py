"""Multi-fidelity surrogate: many cheap M1 runs plus a few accurate M3 runs."""
import warnings
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import RBF, WhiteKernel, ConstantKernel

warnings.filterwarnings('ignore')

designs = pd.read_csv('designs.csv') #the M3 study results
results = pd.read_csv('results.csv')
data = results if 'set' in results.columns else results.merge(designs[['run_id', 'set']], on='run_id')
m1 = pd.read_csv('results_M1.csv') #the 40 M1 results
m1['run_id'] = m1['run_id'].str.replace('_M1', '', regex=False)
m1 = m1.merge(designs[['run_id', 'set']], on='run_id') #gives each M1 result its train or test label

pool = data[(data['set'] == 'train') & (data['run_id'] != 'run_009')] #the 29 M3 designs
test = data[data['set'] == 'test'] #the 10 M3 designs
cheap = m1[(m1['set'] == 'train') & (m1['run_id'] != 'run_009')] #the 29 M1 designs


def scale(df):
    return np.column_stack([(df['n_channels'] - 6) / (16 - 6), (df['u_in'] - 0.1) / (0.3 - 0.1)])


def fit(X, y, noise_min=1e-8):
    kernel = (ConstantKernel(1.0) * RBF(length_scale=[0.5, 0.5], length_scale_bounds=(1e-2, 1e2))
              + WhiteKernel(max(1e-4, noise_min), noise_level_bounds=(noise_min, 1e-1)))
    gp = GaussianProcessRegressor(kernel=kernel, normalize_y=True, n_restarts_optimizer=10, random_state=0)
    gp.fit(X, y)
    return gp


outputs = {'dp': (True, 1e-8), 'T_max': (False, 1e-2)}


def transform(y, use_log):
    return np.log(y) if use_log else y


def untransform(y, use_log):
    return np.exp(y) if use_log else y


def error(name, predicted):
    if name == 'dp':
        return 100 * np.mean(np.abs(predicted - test['dp']) / test['dp'])
    return np.mean(np.abs(predicted - test['T_max']))


low = {name: fit(scale(cheap), transform(cheap[name], use_log), noise_min)
       for name, (use_log, noise_min) in outputs.items()} #trains one M1 surrogate for each output on the 29 cheap runs

print(f"Cheap runs: {len(cheap)} M1 designs, {cheap['minutes'].sum():.0f} minutes in total "
      f"({cheap['minutes'].mean():.1f} min each). M3 runs average {pool['minutes'].mean():.1f} min each.")
print("M1 surrogate alone, compared with the M3 test results:")
for name, (use_log, noise_min) in outputs.items(): #how wrong the M1 surrogate is on its own against the M3 results
    print(f"  {name}: error {error(name, untransform(low[name].predict(scale(test)), use_log)):.2f}")

rng = np.random.default_rng(0) #fixed random picks, so it's repeatable
rows = []
for size in [3, 5, 10, 15, 20, len(pool)]: #the numbers of M3 runs to try. 3 is new, to see how far multi-fidelity can go with almost no expensive runs
    for repeat in range(10 if size < len(pool) else 1):
        picked = pool.iloc[rng.choice(len(pool), size=size, replace=False)]
        row = {'size': size}
        for name, (use_log, noise_min) in outputs.items(): #does dp and then Tmax
            y_high = transform(picked[name], use_log).values #the M3 values for the picked designs
            only = fit(scale(picked), y_high, noise_min) #method 1, M3 only
            gap = y_high - low[name].predict(scale(picked)) #method 2, step 1: at each picked design, the difference between the true M3 value and what the cheap surrogate predicts. For dp on log, this is how many percent M1 is off
            correction = fit(scale(picked), gap, noise_min) #method 2, step 2: a surrogate that learns that gap across the design space
            combined = low[name].predict(scale(test)) + correction.predict(scale(test)) #method 2's prediction: the cheap prediction plus the learned gap, at the test designs
            row[f'{name} M3 only'] = error(name, untransform(only.predict(scale(test)), use_log))
            row[f'{name} multi-fidelity'] = error(name, untransform(combined, use_log))
        rows.append(row)
    print(f"{size} M3 runs done", flush=True)

summary = pd.DataFrame(rows).groupby('size').mean() #averages the 10 picks at each size
print("\nAverage test error (\u0394p in %, T max in \u00b0C):")
print(summary.round(2).to_string())

fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
for ax, name, label in [(axes[0], 'dp', 'Pressure drop error (%)'), (axes[1], 'T_max', 'T max error (\u00b0C)')]:
    ax.plot(summary.index, summary[f'{name} M3 only'], 'o-', color='#7a7a7a', linewidth=2, label='M3 runs only')
    ax.plot(summary.index, summary[f'{name} multi-fidelity'], 'o-', color='#1c5cab', linewidth=2.5,
            label='29 M1 runs + M3 runs')
    ax.set_xlabel('Number of accurate (M3) simulations')
    ax.set_ylabel(label)
    ax.set_xticks(list(summary.index))
    ax.set_ylim(bottom=0)
    ax.grid(True, alpha=0.2)
    ax.spines[['top', 'right']].set_visible(False)
axes[1].legend(frameon=False)
fig.suptitle('Multi-fidelity against M3 only (tested on the same 10 unseen designs)')
fig.tight_layout()
fig.savefig('results/multifidelity.png', dpi=150)
print("\nSaved results/multifidelity.png")