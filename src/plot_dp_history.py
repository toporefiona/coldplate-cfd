"""Plot the inlet pressure (the pressure drop) over time from a transient run."""
import sys
import glob
import numpy as np
import matplotlib.pyplot as plt

case = sys.argv[1]
files = sorted(glob.glob(f'{case}/postProcessing/inletPressure/*/surfaceFieldValue.dat'))
data = np.vstack([np.loadtxt(f) for f in files])
time, dp = data[:, 0], data[:, 1] * 997

plt.plot(time, dp)
plt.xlabel('Time (s)')
plt.ylabel('Pressure drop (Pa)')
plt.title('Pressure drop over time')
plt.grid(True, alpha=0.3)
out_file = sys.argv[2] if len(sys.argv) > 2 else 'dp_history.png'
plt.savefig(out_file, dpi=150)
print(f'Saved {out_file}')
