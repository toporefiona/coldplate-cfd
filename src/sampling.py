"""Sampling experiment: how does the surrogate's error fall as it gets more simulations to learn from?"""
import warnings
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import RBF, WhiteKernel, ConstantKernel

warnings.filterwarnings('ignore')

designs = pd.read_csv('designs.csv')
results = pd.read_csv('results.csv')
data = results if 'set' in results.columns else results.merge(designs[['run_id', 'set']], on='run_id')
pool = data[(data['set'] == 'train') & (data['run_id'] != 'run_009')] #the 29 training designs
test = data[data['set'] == 'test']


def scale(df):
    return np.column_stack([(df['n_channels'] - 6) / (16 - 6), (df['u_in'] - 0.1) / (0.3 - 0.1)])


def fit(X, y, noise_min=1e-8):
    kernel = (ConstantKernel(1.0) * RBF(length_scale=[0.5, 0.5], length_scale_bounds=(1e-2, 1e2))
              + WhiteKernel(max(1e-4, noise_min), noise_level_bounds=(noise_min, 1e-1)))
    gp = GaussianProcessRegressor(kernel=kernel, normalize_y=True, n_restarts_optimizer=10, random_state=0)
    gp.fit(X, y)
    return gp


sizes = [5, 10, 15, 20, 25, len(pool)] #the training set sizes to try out of 29 training models
repeats = 10 #how many different sets to try at each size
rng = np.random.default_rng(0)
rows = [] #an empty list to collect one result per model

for size in sizes:
    for repeat in range(repeats if size < len(pool) else 1):
        train = pool.iloc[rng.choice(len(pool), size=size, replace=False)] #picks size different random row numbers from 0 to 28
        gp_dp = fit(scale(train), np.log(train['dp']))
        gp_T = fit(scale(train), train['T_max'], noise_min=1e-2)
        dp_pred = np.exp(gp_dp.predict(scale(test))) #turns dp back into pascals
        T_pred = gp_T.predict(scale(test))
        rows.append({'size': size,
                     'dp_error': 100 * np.mean(np.abs(dp_pred - test['dp']) / test['dp']),
                     'T_error': np.mean(np.abs(T_pred - test['T_max']))})
    print(f"{size} designs done")

errors = pd.DataFrame(rows) #turns the list of results into a table
summary = errors.groupby('size').mean() #groups the roles and averages each group
print("\nAverage test error for each number of training simulations:")
for size, row in summary.iterrows():
    print(f"  {size:2d} simulations: \u0394p {row['dp_error']:.1f}%, T max {row['T_error']:.2f} \u00b0C")

fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
for ax, column, label in [(axes[0], 'dp_error', 'Pressure drop error (%)'), (axes[1], 'T_error', 'T max error (\u00b0C)')]:
    ax.scatter(errors['size'], errors[column], s=18, color='#86b6ef', alpha=0.7, label='One random pick')
    ax.plot(summary.index, summary[column], 'o-', color='#1c5cab', linewidth=2, label='Average')
    ax.set_xlabel('Number of training simulations')
    ax.set_ylabel(label)
    ax.set_ylim(bottom=0)
    ax.grid(True, alpha=0.2)
    ax.spines[['top', 'right']].set_visible(False)
axes[0].axhline(3, color='#5f5f5f', linestyle='--', linewidth=1, label='M3 mesh error (about 3%)')
axes[0].legend(frameon=False)
fig.suptitle('How the surrogate improves with more simulations (tested on the same 10 unseen designs)')
fig.tight_layout()
fig.savefig('results/sampling.png', dpi=150)
print("\nSaved results/sampling.png")