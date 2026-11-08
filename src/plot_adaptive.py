"""Compare adaptive sampling with random sampling: test error against number of simulations."""
import pandas as pd
import matplotlib.pyplot as plt

adaptive = pd.read_csv('adaptive_history.csv')
random_picks = pd.read_csv('sampling_errors.csv')
random_picks = random_picks[random_picks['size'] >= 10]
random_mean = random_picks.groupby('size').mean()

fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
for ax, column, label in [(axes[0], 'dp_error', 'Pressure drop error (%)'), (axes[1], 'T_error', 'T max error (\u00b0C)')]:
    ax.scatter(random_picks['size'], random_picks[column], s=18, color='#c9c9c9', label='Random, one pick')
    ax.plot(random_mean.index, random_mean[column], 'o-', color='#7a7a7a', linewidth=2, label='Random, average')
    ax.plot(adaptive['simulations'], adaptive[column], 'o-', color='#1c5cab', linewidth=2.5, label='Adaptive')
    ax.set_xlabel('Number of training simulations')
    ax.set_xticks([10, 12, 14, 16, 18, 20, 25, 29])
    ax.set_ylabel(label)
    ax.set_ylim(bottom=0)
    ax.grid(True, alpha=0.2)
    ax.spines[['top', 'right']].set_visible(False)
axes[1].legend(frameon=False)
fig.suptitle('Adaptive against random sampling (tested on the same 10 unseen designs)')
fig.tight_layout()
fig.savefig('results/adaptive_vs_random.png', dpi=150)
print("Saved results/adaptive_vs_random.png")