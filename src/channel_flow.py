"""Work out how the flow splits between the channels, from a ParaView line across the plate."""
import sys
import numpy as np
import pandas as pd
from config import load_settings, channel_width

MM = 0.001  # study.yaml is in mm, the CSV is in metres

csv_file = sys.argv[1] #the file path
n_channels = int(sys.argv[2]) #the number of channels turned into a number

plate = load_settings()['plate']
w = channel_width(n_channels, plate) #gives the channel width in mm (25.8 for N6)

data = pd.read_csv(csv_file) #loads the csv file into a table
ux_col = 'U:0' if 'U:0' in data.columns else 'U_X' #ParaView names the x velocity column U:0 when it saves a CSV, but some versions use U_X. This picks whichever exists
y = data['Points:1'].to_numpy() #the y coordinate
ux = data[ux_col].to_numpy() #the x velocity at each point

flows = [] #empty list for the flow in each channel
for i in range(n_channels):
    y_bottom = (plate['edge_margin'] + i * (w + plate['wall'])) * MM #where the channel starts
    y_top = y_bottom + w * MM #where the channel ends
    inside = (y >= y_bottom) & (y <= y_top) #mark which sample points lie inside this channel
    flows.append(np.trapezoid(ux[inside], y[inside])) #the area under the bump for this channel. The flow per metre of depth

total = sum(flows) #the total over al channels
inlet_flow = 0.25 * plate['port_width'] * MM #the flow coming in, 0.25 isthe velocity

print(f'Total flow through the line: {total:.3e} m2/s (inlet: {inlet_flow:.3e} m2/s)')
for i, q in enumerate(flows, start=1): #goes through the flow numbering them from 1 instead of 0
    print(f'Channel {i}: {q / total * 100:5.1f} %') #the channels share in %
print(f'Lowest / highest: {min(flows) / max(flows):.2f}') #the lowest ÷ highest channel flow. 1.00 would be perfectly even, and anything much lower shows uneven flow. This is the uniformity number for the surrogate.