"""Plot solver residuals from an OpenFOAM log file."""
import re #tool for finding patterns in a text
import sys #lets the script read what you type after its name in the terminal
import matplotlib.pyplot as plt

log_file = sys.argv[1]  # path to the log file, typed after the script name
residuals = {} #an empty dictionary to store the results
iteration = 0 #counts the iterations

with open(log_file) as f: #opens the log file to read it and with makes sure its closed afterward
    for line in f: #goes through the file one at a time
        if line.startswith('Time ='):
            iteration += 1
        match = re.search(r'Solving for (\w+), Initial residual = ([0-9.eE+-]+)', line) #looks for lines like the ones mentioned, (\w+) captures the filed name such as Ux,Uy,p,k,epsilon, \w+ means one or more letters or numbers
        if match:
            field = match.group(1) #take the field name
            value = float(match.group(2)) #and residual turned from text into a number
            residuals.setdefault(field, {}) #if this field is not in the dictionary yet add it with an empty list of values
            residuals[field].setdefault(iteration, value) #store the residual for this iteration
 
for field, values in residuals.items(): #loops through each field and its values
    plt.semilogy(list(values.keys()), list(values.values()), label=field) #plots iteration against residual with a logarithmic y-axis (where each step up multiplies by 10)

plt.xlabel('Iteration')
plt.ylabel('Initial residual')
plt.title('Convergence history')
plt.legend()
plt.grid(True, which='both', alpha=0.3)
out_file = sys.argv[2] if len(sys.argv) > 2 else 'residuals.png'  # where to save the plot
plt.savefig(out_file, dpi=150)
print(f'Saved {out_file}')