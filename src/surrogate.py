"""Train a Gaussian process surrogate on the training designs and test it on the test designs."""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import RBF, WhiteKernel, ConstantKernel

designs = pd.read_csv('designs.csv')
results = pd.read_csv('results.csv')
data = results if 'set' in results.columns else results.merge(designs[['run_id', 'set']], on='run_id') #joins the 2 tables to see which result is train or test
odd = data[data['run_id'] == 'run_009']
print(f"run_009 is in the {odd['set'].iloc[0]} set")


def scale(df): #a small function that turns N and U into numbers between 0 and 1
    n = (df['n_channels'] - 6) / (16 - 6) #6 channels become 0 and 16 become 1
    u = (df['u_in'] - 0.1) / (0.3 - 0.1) #same thing here
    return np.column_stack([n, u]) #puts the 2 side by side as a table with 2 columns, which i the shape scikit-learn wants


def fit(X, y, noise_min=1e-8):
    kernel = (ConstantKernel(1.0) * RBF(length_scale=[0.5, 0.5], length_scale_bounds=(1e-2, 1e2))
              + WhiteKernel(max(1e-4, noise_min), noise_level_bounds=(noise_min, 1e-1))) #allows a tiny amount of scatter, so the surface doesn't have to pass exactly through every point. Our runs have small numerical wobbles (about 0.5%), and this stops the model twisting itself to fit them
    gp = GaussianProcessRegressor(kernel=kernel, normalize_y=True, n_restarts_optimizer=10, random_state=0) #makes the model try 10 different starting points when learning its settings and keep the best. This avoids getting stuck on a poor answer. #random_state=0 makes those restarts the same every run, so the results are repeatable
    gp.fit(X, y) #the learning step. It picks the length scales, the swing size and the noise level that best explain the training data
    return gp #hands back the trained model


train = data[(data['set'] == 'train') & (data['run_id'] != 'run_009')]
test = data[(data['set'] == 'test') & (data['run_id'] != 'run_009')]
print(f"Training on {len(train)} designs, testing on {len(test)}")

cases = [('dp', True), ('T_max', False)]
fits = {} #empty dictionary to keep each model's predictions in, so the plot can use them later

for output, use_log in cases: #goes through the cases
    name = f"log {output}" if use_log else output
    base = 25 if output == 'T_max' else 0
    y = np.log(train[output] - base) if use_log else train[output] #the values to learn
    gp = fit(scale(train), y, noise_min=1e-2 if output == 'T_max' else 1e-8) #trains the model
    mean, sd = gp.predict(scale(test), return_std=True) #predicts the train designs along with the uncertainty
    odd_mean = gp.predict(scale(odd))[0] #the prediction for case 9
    if use_log: #converts the values back into pascals for p
        predicted, spread, odd_pred = np.exp(mean) + base, np.exp(mean) * sd, np.exp(odd_mean) + base
    else:
        predicted, spread, odd_pred = mean, sd, odd_mean
    fits[name] = (predicted, spread) #stores the model's predictions under its name
    error = predicted - test[output]
    outside = (np.abs(error) > 2 * spread).sum() #counts how many errors are bigger than 2 standard deviations
    print(f"\n{name}: learned kernel {gp.kernel_}")
    print(f"  mean error {np.abs(error).mean():.2f}, worst {np.abs(error).max():.2f}, average bias {error.mean():+.2f}")
    print(f"  {outside} of {len(test)} test designs outside \u00b12 standard deviations")
    print(f"  run_009 (left out): true {odd[output].iloc[0]:.2f}, predicted {odd_pred:.2f}")

labels = {'dp': 'Pressure drop (Pa)', 'log dp': 'Pressure drop (Pa), trained on log',
          'T_max': 'T max (\u00b0C)', 'log T_max': 'T max (\u00b0C), trained on log of rise'}
fig, axes = plt.subplots(1, 2, figsize=(10, 4.8))
for ax, (output, use_log) in zip(axes, cases):
    name = f"log {output}" if use_log else output
    predicted, spread = fits[name]
    true = test[output]
    ax.errorbar(true, predicted, yerr=2 * spread, fmt='o', color='#1c5cab', ecolor='#86b6ef', elinewidth=2, capsize=3)
    pad = 0.05 * (true.max() - true.min())
    line = [true.min() - pad, true.max() + pad]
    ax.plot(line, line, color='#5f5f5f', linestyle='--', linewidth=1, label='Perfect prediction')
    ax.set_title(labels[name])
    ax.set_xlabel('Simulated')
    ax.set_ylabel('Surrogate prediction')
    ax.grid(True, alpha=0.2)
    ax.spines[['top', 'right']].set_visible(False)
axes[0].legend(frameon=False)
fig.suptitle('Surrogate against simulation on the 10 test designs (bars show \u00b12 standard deviations)')
fig.tight_layout()
fig.savefig('results/surrogate_test.png', dpi=150)
print("\nSaved results/surrogate_test.png")