"""Compare the pressure gradient in the straight validation channel with theory."""
import sys
import glob #finds files by pattern, like * in Ubuntu
import numpy as np

NU = 8.9e-7   # kinematic viscosity of water, m2/s
W = 0.0258    # channel width, m
H = 0.003     # channel depth, m (sets the depth friction)

case = sys.argv[1] #is the case folder you type, for example runs/val_friction
U = float(sys.argv[2]) #is the inlet velocity you type
friction = sys.argv[3] == 'yes'

files = sorted(glob.glob(f'{case}/postProcessing/singleGraph*/*/*p*.xy')) #finds the samp led pressure file
data = np.loadtxt(files[-1]) #reads the file into a table of numbers
x, p = data[:, 0], data[:, -1] #takes the first column (distance along the line, which equals x here) and the last column (pressure). : meansevery ro
 
inside = (x > 0.5) & (x < 0.9) #keeps only the points between 0.5 and 0.9 m. That skips the start, where the flow is still developing, and the very end, near the outlet
slope = -np.polyfit(x[inside], p[inside], 1)[0] #fits a straight line through those points. The 1 means a straight line (a 1st order polynomial). [0] takes its slope. The minus sign makes it positive, because pressure falls along the channel

if friction: #uses the Brinkman formula
    K = H**2 / 12 #the premeability from the 3mm depth
    d = np.sqrt(K) #the thickness of the slow layer at the side walls
    theory = NU * U / (K * (1 - (2 * d / W) * np.tanh(W / (2 * d))))
else:
    theory = 12 * NU * U / W**2 #uses the textbook formula when friction is off: 12 ν U / W²

error = (slope - theory) / theory * 100 #the diference as a % of the theory value
print(f'Simulation: {slope:.4e}')
print(f'Theory:     {theory:.4e}')
print(f'Difference: {error:+.2f} %')