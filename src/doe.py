"""Choose the designs for the study with a Latin hypercube."""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import qmc #stands for “quasi Monte Carlo”, a family of methods for spreading points evenly
from config import load_settings

N_DESIGNS = 40
N_TRAIN = 30

settings = load_settings()
n_min, n_max = settings['channels']['min'], settings['channels']['max']
u_min, u_max = settings['flow']['u_min'], settings['flow']['u_max']

sampler = qmc.LatinHypercube(d=2, seed=42) #in 2 dimensions, N and U
sample = sampler.random(n=N_DESIGNS) #picks 40 points, each with 2 numbers between 0 and 1
scaled = qmc.scale(sample, [n_min - 0.5, u_min], [n_max + 0.5, u_max]) #after rounding, each whole number from 6 to 16 is about equally likely (each one gets a slice 1 wide)

designs = pd.DataFrame({
    'run_id': [f'run_{i:03d}' for i in range(1, N_DESIGNS + 1)],
    'n_channels': np.clip(np.round(scaled[:, 0]), n_min, n_max).astype(int),
    'u_in': np.round(scaled[:, 1], 3),
    'set': ['train'] * N_TRAIN + ['test'] * (N_DESIGNS - N_TRAIN), #train for the first 30 and test for the last 10
})
designs.to_csv('designs.csv', index=False) #saves the table
print(designs.to_string(index=False))

for name, group in designs.groupby('set'): #plots the training and test designs
    plt.scatter(group['n_channels'], group['u_in'], label=name)
plt.xlabel('Number of channels')
plt.ylabel('Inlet velocity (m/s)')
plt.title('Study designs (Latin hypercube)')
plt.legend()
plt.grid(True, alpha=0.3)
plt.savefig('results/designs.png', dpi=150)
print('Saved designs.csv and results/designs.png')