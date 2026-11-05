"""Use the surrogate to map pressure drop and T max over every design, and find the best design for each pressure budget."""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import RBF, WhiteKernel, ConstantKernel

results = pd.read_csv('results.csv')
data = results[results['run_id'] != 'run_009']


def scale(n, u):
    return np.column_stack([(n - 6) / (16 - 6), (u - 0.1) / (0.3 - 0.1)])


def fit(X, y, noise_min=1e-8):
    kernel = (ConstantKernel(1.0) * RBF(length_scale=[0.5, 0.5], length_scale_bounds=(1e-2, 1e2))
              + WhiteKernel(max(1e-4, noise_min), noise_level_bounds=(noise_min, 1e-1)))
    gp = GaussianProcessRegressor(kernel=kernel, normalize_y=True, n_restarts_optimizer=10, random_state=0)
    gp.fit(X, y)
    return gp


gp_dp = fit(scale(data['n_channels'], data['u_in']), np.log(data['dp']))
gp_T = fit(scale(data['n_channels'], data['u_in']), data['T_max'], noise_min=1e-2)

n_values = np.arange(6, 17)
u_values = np.linspace(0.1, 0.3, 81)
N, U = np.meshgrid(n_values, u_values) #makes every combination
X = scale(N.ravel(), U.ravel())
dp = np.exp(gp_dp.predict(X)).reshape(N.shape)
T, T_sd = gp_T.predict(X, return_std=True)
T, T_sd = T.reshape(N.shape), T_sd.reshape(N.shape)

fig, axes = plt.subplots(1, 3, figsize=(17, 5))
for ax, values, title, colours in [(axes[0], dp, 'Pressure drop (Pa)', 'Blues'), (axes[1], T, 'T max (\u00b0C)', 'Reds')]:
    mesh = ax.pcolormesh(n_values, u_values, values, shading='nearest', cmap=colours)
    lines = ax.contour(n_values, u_values, values, colors='black', linewidths=0.6, alpha=0.6)
    ax.clabel(lines, fontsize=8)
    ax.scatter(data['n_channels'], data['u_in'], s=14, c='white', edgecolors='black', linewidths=0.6, label='Simulated designs')
    fig.colorbar(mesh, ax=ax)
    ax.set_title(f'{title}, surrogate')
    ax.set_xlabel('Number of channels')
    ax.set_ylabel('Inlet velocity (m/s)')
axes[0].legend(frameon=False, loc='upper left')

for speed, colour in [(0.1, '#86b6ef'), (0.2, '#3987e5'), (0.3, '#0d366b')]:
    row = np.argmin(np.abs(u_values - speed))
    axes[2].errorbar(n_values, T[row], yerr=2 * T_sd[row], fmt='o-', color=colour, capsize=3, label=f'{speed:.1f} m/s')
axes[2].set_title('T max against number of channels (bars \u00b12 sd)')
axes[2].set_xlabel('Number of channels')
axes[2].set_ylabel('T max (\u00b0C)')
axes[2].grid(True, alpha=0.2)
axes[2].spines[['top', 'right']].set_visible(False)
axes[2].legend(frameon=False, title='Inlet velocity')

fig.tight_layout()
fig.savefig('results/surrogate_maps.png', dpi=150)
print("Saved results/surrogate_maps.png")

print("\nBest design for each pressure budget, according to the surrogate:")
for budget in [30, 50, 80, 120]:
    T_allowed = np.where(dp <= budget, T, np.inf)
    i, j = np.unravel_index(np.argmin(T_allowed), T.shape) #finds the coolest allowed design
    print(f"  {budget} Pa: {N[i, j]} channels at {U[i, j]:.3f} m/s, dp {dp[i, j]:.1f} Pa, "
          f"T max {T[i, j]:.2f} \u00b1 {2 * T_sd[i, j]:.2f} \u00b0C")