"""Surrogate for flow uniformity, used to flag designs where the inlet jet may starve a channel."""
import warnings
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import RBF, WhiteKernel, ConstantKernel

warnings.filterwarnings('ignore')
LIMIT = 0.2 #limit for inlet speed

designs = pd.read_csv('designs.csv')
results = pd.read_csv('results.csv')
data = results if 'set' in results.columns else results.merge(designs[['run_id', 'set']], on='run_id') #a small table with the 2 CFD runs from phase 6
checks = pd.DataFrame({'run_id': ['check_N16_U0113', 'check_N11_U0285_long'],
                       'n_channels': [16, 11], 'u_in': [0.113, 0.285], 'uniformity': [0.5551, 0.168]})
train = data[data['set'] == 'train'] #all 30 training designs as run 9 was fine for flow uniformity
test = pd.concat([data[data['set'] == 'test'], checks]) #the 10 test designs plus the 2 check runs. concat stacks two tables on top of each other. The check runs are the most important tests, because one of them is the failure we want to catch


def scale(df):
    return np.column_stack([(df['n_channels'] - 6) / (16 - 6), (df['u_in'] - 0.1) / (0.3 - 0.1)])


def fit(X, y, noise_min=1e-8):
    kernel = (ConstantKernel(1.0) * RBF(length_scale=[0.5, 0.5], length_scale_bounds=(1e-2, 1e2))
              + WhiteKernel(max(1e-4, noise_min), noise_level_bounds=(noise_min, 1e-1)))
    gp = GaussianProcessRegressor(kernel=kernel, normalize_y=True, n_restarts_optimizer=10, random_state=0)
    gp.fit(X, y)
    return gp


gp = fit(scale(train), np.log(train['uniformity'])) ##trains on th elog of uniformity
mean, sd = gp.predict(scale(test), return_std=True) #predictions and uncertainties
print(f"Uniformity surrogate (trained on the 30 training designs): {gp.kernel_}")
for run, true, m, s in zip(test['run_id'], test['uniformity'], mean, sd): #goes through the 12 test designs
    lower, upper = np.exp(m - 2 * s), np.exp(m + 2 * s) #the 95% range
    flag = 'FLAG' if lower < LIMIT else ''
    print(f"  {run:22s} true {true:.3f}, predicted {np.exp(m):.3f} (range {lower:.3f} to {upper:.3f}) {flag}")

gp_40 = fit(scale(data), np.log(data['uniformity'])) #retrains on all 40 study designs
picks = pd.DataFrame({'n_channels': [16, 16, 16, 11], 'u_in': [0.113, 0.160, 0.212, 0.285]}) #the 4 best picks it chose
p_mean, p_sd = gp_40.predict(scale(picks), return_std=True) #predicts their uniformity
print("\nWould the flag have warned us about the Phase 6 picks? (trained on the 40 study designs only)")
for n, u, m, s in zip(picks['n_channels'], picks['u_in'], p_mean, p_sd):
    lower = np.exp(m - 2 * s)
    verdict = 'FLAG: check with CFD' if lower < LIMIT else 'OK'
    print(f"  N{n} at {u:.3f} m/s: uniformity {np.exp(m):.3f}, could be as low as {lower:.3f}  {verdict}")

n_values = np.arange(6, 17) #the 891 design grid
u_values = np.linspace(0.1, 0.3, 81)
N, U = np.meshgrid(n_values, u_values)
grid = pd.DataFrame({'n_channels': N.ravel(), 'u_in': U.ravel()}) #puts the grid into a table
g_mean, g_sd = gp_40.predict(scale(grid), return_std=True) #predicts all 891
uniformity = np.exp(g_mean).reshape(N.shape) #the best guess
lowest = np.exp(g_mean - 2 * g_sd).reshape(N.shape) #the low end of each design

fig, ax = plt.subplots(figsize=(8.5, 5.5))
mesh = ax.pcolormesh(n_values, u_values, uniformity, shading='nearest', cmap='Blues')
ax.contourf(n_values, u_values, (lowest < LIMIT).astype(float), levels=[0.5, 1.5], hatches=['//'], colors='none')
ax.contour(n_values, u_values, lowest, levels=[LIMIT], colors='#c0392b', linewidths=1.5)
ax.scatter(data['n_channels'], data['u_in'], s=14, c='white', edgecolors='black', linewidths=0.6, label='Study designs')
ax.scatter(picks['n_channels'], picks['u_in'], marker='*', s=220, c='#f1c40f', edgecolors='black', label='Surrogate picks (Phase 6)')
fig.colorbar(mesh, ax=ax).set_label('Flow uniformity (lowest / highest channel flow)')
ax.set_title(f'Flow uniformity, surrogate. Hatched: could be below {LIMIT}, check with CFD')
ax.set_xlabel('Number of channels')
ax.set_ylabel('Inlet velocity (m/s)')
ax.legend(frameon=False, loc='upper center', bbox_to_anchor=(0.5, -0.12), ncol=2)
fig.tight_layout()
fig.savefig('results/uniformity_map.png', dpi=150)
print("\nSaved results/uniformity_map.png")