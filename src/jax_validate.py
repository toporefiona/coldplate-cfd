"""Step D: check the JAX solver against an exact solution and against the OpenFOAM study."""
import jax.numpy as jnp
import pandas as pd
import matplotlib.pyplot as plt
from config import load_settings, channel_width
from jax_solver import plate_grid, solve_flow, channel_shares, MU

settings = load_settings()
depth = settings['physics']['depth'] * 1e-3

L, w, u = 300, 20, 0.05 #a channel 300 long, 20 wide and speed of 0.05
water = jnp.zeros((L, w + 10)).at[:, 5:5 + w].set(1.0) #builds its grid directly
channel = {**settings, 'plate': {**settings['plate'], 'port_width': w}} #a copy of the settings with width port chnages to 20
_, _, dp = solve_flow(water, u, channel) #runs the solver
exact = 12 * MU * u * (L - 0.5) * 1e-3 / depth ** 2 #the exact answer for flow in a thin gap
print(f"Straight channel: JAX {dp:.4f} Pa, exact {exact:.4f} Pa, difference {100 * (dp / exact - 1):+.3f}%")

results = pd.read_csv('results.csv') #the openfoam study results
rows = []
for _, design in results.iterrows(): #goes through all the 40 designs
    n, u = int(design['n_channels']), float(design['u_in'])
    widths = jnp.full(n, channel_width(n, settings['plate'])) #builds the plate and solves it
    x, y, water = plate_grid(widths, settings)
    p, kx, dp = solve_flow(water, u, settings)
    shares = channel_shares(p, kx, x, y, widths, settings)
    rows.append({'run_id': design['run_id'], 'n_channels': n, 'u_in': u,
                 'dp_openfoam': design['dp'], 'dp_jax': float(dp),
                 'uniformity_openfoam': design['uniformity'], 'uniformity_jax': float(shares.min() / shares.max())})
compare = pd.DataFrame(rows)
compare['dp_ratio'] = compare['dp_jax'] / compare['dp_openfoam']
compare.to_csv('results_jax.csv', index=False)
print(compare[['dp_ratio']].describe().round(3).T.to_string())

fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
points = axes[0].scatter(compare['u_in'], 100 * compare['dp_ratio'], c=compare['n_channels'], cmap='Blues', edgecolors='#333333', s=45)
axes[0].set_xlabel('Inlet velocity (m/s)')
axes[0].set_ylabel('JAX pressure drop as % of OpenFOAM')
axes[0].set_ylim(0, 100)
fig.colorbar(points, ax=axes[0]).set_label('Number of channels')
axes[1].scatter(compare['uniformity_openfoam'], compare['uniformity_jax'], c=compare['n_channels'], cmap='Blues', edgecolors='#333333', s=45)
axes[1].plot([0, 1], [0, 1], color='#7a7a7a', linestyle='--', linewidth=1)
axes[1].set_xlabel('Flow uniformity, OpenFOAM')
axes[1].set_ylabel('Flow uniformity, JAX (no inertia)')
for ax in axes:
    ax.grid(True, alpha=0.2)
    ax.spines[['top', 'right']].set_visible(False)
fig.suptitle('Where the no inertia model agrees with OpenFOAM, and where it does not')
fig.tight_layout()
fig.savefig('results/jax_vs_openfoam.png', dpi=150)
print("Saved results/jax_vs_openfoam.png")