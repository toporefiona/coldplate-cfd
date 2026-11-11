"""A simple, differentiable 2D flow solver for the cold plate, written in JAX."""
import jax
import jax.numpy as jnp
import matplotlib.pyplot as plt
from jax.scipy.sparse.linalg import cg #jax's conjugate gradient solver
from config import load_settings, channel_width

jax.config.update('jax_enable_x64', True)
MU = 997.0 * 8.9e-7 #the water's dynamic viscosity in Pa, its density times the kinematic viscosity


def overlap(lo, hi, a, b): #it answers what fraction of the stretch from one square's edges lies inside teh stretch from a channel's edges
    return jnp.clip(jnp.minimum(hi, b) - jnp.maximum(lo, a), 0.0, None) / (hi - lo) #the stretch where the 2 overlap, if they dont overlap it comes out negative. Example: a square from 5 to 6 mm, and a channel starting at 5.4 mm, gives an overlap of 0.6, so the square is 60% water
 

def plate_grid(widths, settings, cell=1.0):
    plate = settings['plate']
    L, W, wall, margin = plate['length'], plate['width'], plate['wall'], plate['edge_margin']
    h_in, h_out = plate['inlet_header'], plate['outlet_header']
    port_w, port_l = plate['port_width'], plate['port_length']

    x = jnp.arange(-port_l, L + port_l, cell) + cell / 2 #the cetre of every square along the plate
    y = jnp.arange(0.0, W, cell) + cell / 2 #the same across the plate from 0 to 200, y axis of the plate
    X, Y = jnp.meshgrid(x, y, indexing='ij') #makes 2 full grids wit the x and y position of every square
    x0, x1, y0, y1 = X - cell / 2, X + cell / 2, Y - cell / 2, Y + cell / 2 #the left, right, bottom and top edge of every square

    headers = (overlap(x0, x1, 0.0, h_in) + overlap(x0, x1, L - h_out, L)) * overlap(y0, y1, margin, W - margin)
    ports = (overlap(x0, x1, -port_l, 0.0) + overlap(x0, x1, L, L + port_l)) * overlap(y0, y1, (W - port_w) / 2, (W + port_w) / 2)
    starts = margin + jnp.concatenate([jnp.zeros(1), jnp.cumsum(widths + wall)[:-1]])
    across = sum(overlap(y0, y1, starts[k], starts[k] + widths[k]) for k in range(len(widths)))
    channels = overlap(x0, x1, h_in, L - h_out) * across
    return x, y, headers + ports + channels

def harmonic(a, b):
    return 2 * a * b / (a + b) #the harmoic mean between 2 numbers, If either is nearly 0, the answer is nearly 0. Between two water squares (both k), it gives k. Between water and metal, it gives almost 0, so the face is blocked.


def solve_flow(water, u_in, settings, eps=1e-6): #eps is the tiny k for metal square, one millionth of water
    depth = settings['physics']['depth'] * 1e-3
    port_w = settings['plate']['port_width'] * 1e-3
    k = (eps + (1 - eps) * water) * depth ** 2 / (12 * MU) #how easily each square lets water through
    kx = harmonic(k[:-1, :], k[1:, :]) #k for every face beyween left and right neighbours
    ky = harmonic(k[:, :-1], k[:, 1:]) #k for every face between up and down neighbours
    outlet = 2 * k[-1, :] * water[-1, :] #how easily the water leaves through the outlet

    def net_outflow(p):
        fx = kx * (p[:-1, :] - p[1:, :]) #flow through every left-right face
        fy = ky * (p[:, :-1] - p[:, 1:]) #flow throgh every up-down face
        out = jnp.zeros_like(p).at[:-1, :].add(fx).at[1:, :].add(-fx).at[:, :-1].add(fy).at[:, 1:].add(-fy) #adds up, for every square, the flow leaving it
        return out.at[-1, :].add(outlet * p[-1, :]) #adds the flow leaving through the outlet

    diag = jnp.zeros_like(k).at[:-1, :].add(kx).at[1:, :].add(kx).at[:, :-1].add(ky).at[:, 1:].add(ky).at[-1, :].add(outlet) #each square’s total “ease of flow” to all its neighbours.
    inflow = u_in * port_w * water[0, :] / water[0, :].sum()
    source = jnp.zeros_like(k).at[0, :].set(inflow) #a grid that i 0 everywhere, except the first clumn which holds the inflow
    p, _ = cg(net_outflow, source, M=lambda r: r / diag, tol=1e-10, maxiter=20000) #the solve itself
    dp = (p[0, :] * water[0, :]).sum() / water[0, :].sum() #the pressure drop
    return p, kx, dp


def channel_shares(p, kx, x, y, widths, settings):
    plate = settings['plate']
    i = int(jnp.argmin(jnp.abs(x - plate['length'] / 2))) #finds the column of plates halfway along the plates
    flow = kx[i, :] * (p[i, :] - p[i + 1, :]) #the flow through every face in that column
    starts = plate['edge_margin'] + jnp.concatenate([jnp.zeros(1), jnp.cumsum(widths + plate['wall'])[:-1]])
    per_channel = jnp.array([(flow * overlap(y - 0.5, y + 0.5, starts[k], starts[k] + widths[k])).sum() for k in range(len(widths))]) #for each channel adds up the flow through the squares inside it, overlap handles the part‑water squares at its edges
    return 100 * per_channel / per_channel.sum()


if __name__ == '__main__':
    settings = load_settings()
    n, u_in = 6, 0.25 #Builds the 6 channel grid, prints the water area check, solves at 0.25 m/s, then prints Δp and the flow split
    widths = jnp.full(n, channel_width(n, settings['plate']))
    x, y, water = plate_grid(widths, settings)
    print(f"Grid: {water.shape[0]} x {water.shape[1]} cells, water area {water.sum():.1f} mm\u00b2")
    p, kx, dp = solve_flow(water, u_in, settings)
    shares = channel_shares(p, kx, x, y, widths, settings)
    print(f"Pressure drop: {dp:.2f} Pa")
    print("Share of flow in each channel (%):", jnp.round(shares, 1))
    plt.figure(figsize=(10, 5))
    plt.pcolormesh(x, y, jnp.where(water > 0.5, p, jnp.nan).T, cmap='viridis', shading='nearest')
    plt.gca().set_aspect('equal')
    plt.colorbar(label='Pressure (Pa)', shrink=0.8)
    plt.xlabel('x (mm)')
    plt.ylabel('y (mm)')
    plt.title(f'Pressure, no inertia: {n} channels at {u_in} m/s')
    plt.tight_layout()
    plt.savefig('results/jax_pressure.png', dpi=150)
    print("Saved results/jax_pressure.png")