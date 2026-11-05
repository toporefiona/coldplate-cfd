"""Plot the pressure drop against the hottest temperature for every design, with the Pareto front."""
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

results = pd.read_csv('results.csv')

# A design is on the Pareto front if no other design has both a lower dp and a lower T_max
on_front = []
for _, design in results.iterrows():
    beaten = ((results['dp'] <= design['dp']) & (results['T_max'] <= design['T_max']) &
              ((results['dp'] < design['dp']) | (results['T_max'] < design['T_max']))).any()
    on_front.append(not beaten)
results['pareto'] = on_front
front = results[results['pareto']].sort_values('dp')

blues = LinearSegmentedColormap.from_list('blues', ['#86b6ef', '#3987e5', '#1c5cab', '#0d366b'])

fig, ax = plt.subplots(figsize=(8, 5.5))
ax.plot(front['dp'], front['T_max'], color='#5f5f5f', linewidth=2, linestyle='--',
        zorder=1, label='Pareto front')
points = ax.scatter(results['dp'], results['T_max'], c=results['n_channels'], cmap=blues,
                    s=60, edgecolors='white', linewidths=1.5, zorder=2)
ax.scatter(front['dp'], front['T_max'], s=150, facecolors='none', edgecolors='#1f1f1f',
           linewidths=1.5, zorder=3, label='On the Pareto front')

# Keep the axis on the main group of designs, and mark any extreme design at the top edge
typical = results['T_max'].sort_values().iloc[-2]
top = typical + 1.5
ax.set_ylim(results['T_max'].min() - 1, top)
for _, design in results[results['T_max'] > top].iterrows():
    ax.scatter(design['dp'], top - 0.3, marker='^', s=90, color='#1f1f1f', zorder=4, clip_on=False)
    ax.annotate(f"{design['run_id']}: T max {design['T_max']:.0f} \u00b0C, one channel starved of flow",
                xy=(design['dp'], top - 0.3), xytext=(-8, -4), textcoords='offset points', ha='right', va='top', fontsize=9, color='#1f1f1f')
colourbar = fig.colorbar(points, ax=ax)
colourbar.set_label('Number of channels')
ax.set_xlabel('Pressure drop (Pa)')
ax.set_ylabel('Hottest coolant temperature, T max (\u00b0C)')
ax.set_title('Cooling against pumping pressure, 40 cold plate designs')
ax.grid(True, alpha=0.2)
ax.spines[['top', 'right']].set_visible(False)
ax.legend(frameon=False)
fig.tight_layout()
fig.savefig('results/tradeoff.png', dpi=150)
print('Saved results/tradeoff.png')

print('\nDesigns on the Pareto front (best possible trade-offs):')
print(front[['run_id', 'n_channels', 'u_in', 'dp', 'T_max', 'uniformity']].to_string(index=False))
