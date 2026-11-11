"""Step E: use JAX gradients to choose channel widths that share the flow evenly."""
import jax
import jax.numpy as jnp
import matplotlib.pyplot as plt
from config import load_settings
from jax_solver import plate_grid, solve_flow, channel_shares

settings = load_settings()
plate = settings['plate']
n, u_in, steps, rate = 6, 0.1, 10, 2.0 #6 channels at 0.1 m/s, 10 optimisation steps and a step size of 2
total = plate['width'] - 2 * plate['edge_margin'] - (n - 1) * plate['wall'] #the total width available for water


def widths_from(z):
    return total * jax.nn.softmax(z) #turns any 6 numbers into 6 positive numbers that add up to 1


def evaluate(widths): #the whole simulation for this plate
    x, y, water = plate_grid(widths, settings)
    p, kx, dp = solve_flow(water, u_in, settings)
    return channel_shares(p, kx, x, y, widths, settings), dp


def unevenness(z):
    shares, _ = evaluate(widths_from(z))
    return jnp.var(shares) / jnp.mean(shares) ** 2 #how far the shares are from their avg


slope = jax.value_and_grad(unevenness) #makes a function that returns both the score and its 6 slopes, in one go
z = jnp.zeros(n) #starts at allthe same widths
history = []
for step in range(steps): #repeats 10 times
    value, g = slope(z) #the current score, and the slopes for all 6 dials.
    history.append(float(value))
    print(f"step {step}: unevenness {value:.6f}, widths {jnp.round(widths_from(z), 2)}", flush=True)
    z = z - rate * g #Move every dial against its slope, scaled by the step size. A positive slope means “turning this up makes things worse”, so turn it down, and the other way round.

start, best = widths_from(jnp.zeros(n)), widths_from(z) #the equal widths, and the final optimised widths
shares_start, dp_start = evaluate(start)
shares_best, dp_best = evaluate(best)
print(f"\nEqual widths:     uniformity {shares_start.min() / shares_start.max():.3f}, dp {dp_start:.2f} Pa")
print(f"Optimised widths: uniformity {shares_best.min() / shares_best.max():.3f}, dp {dp_best:.2f} Pa")
print("Optimised widths (mm):", jnp.round(best, 2))

channels = jnp.arange(1, n + 1)
fig, axes = plt.subplots(1, 3, figsize=(14, 4))
axes[0].plot(range(steps), history, 'o-', color='#1c5cab')
axes[0].set_yscale('log')
axes[0].set_xlabel('Optimisation step')
axes[0].set_ylabel('Unevenness of the flow split')
axes[1].bar(channels - 0.2, start, 0.4, color='#c9c9c9', label='Equal widths')
axes[1].bar(channels + 0.2, best, 0.4, color='#1c5cab', label='Optimised')
axes[1].set_xlabel('Channel')
axes[1].set_ylabel('Channel width (mm)')
axes[2].bar(channels - 0.2, shares_start, 0.4, color='#c9c9c9', label='Equal widths')
axes[2].bar(channels + 0.2, shares_best, 0.4, color='#1c5cab', label='Optimised')
axes[2].axhline(100 / n, color='#7a7a7a', linestyle='--', linewidth=1)
axes[2].set_xlabel('Channel')
axes[2].set_ylabel('Share of the flow (%)')
axes[2].legend(frameon=False)
for ax in axes:
    ax.grid(True, alpha=0.2)
    ax.spines[['top', 'right']].set_visible(False)
fig.suptitle(f'Optimising {n} channel widths with JAX gradients (no inertia model, {u_in} m/s)')
fig.tight_layout()
fig.savefig('results/jax_optimised_widths_U01.png', dpi=150)
print("Saved results/jax_optimised_widths_U01.png")