# Design notes

Things we have learned about the cold plate design and the model, and what needs to change later. This is not a list of code slips (a missing bracket, a typo). It is the list of decisions, assumptions and findings that affect the design, the study, or the surrogate model.

Status: **Open** = still to do. **Done** = changed already. **Watch** = fine for now, check again later.

Last updated: 29 October 2026 (end of Phase 3)

---

## 1. The 2D model was missing the friction of the top and bottom walls

**Status:** Done

**What we found:** The first `simpleFoam` run on N6 did not converge. Residuals stuck at about 0.02 to 0.08 for 2000 iterations, and continuity errors were high (sum local about 0.05). The jet from the inlet port was flapping in the header. Residual plot: `results/residuals_N6_no_friction.png`.

**Why:** A real channel is about 3 mm deep. Most of its friction comes from the top and bottom walls, only 3 mm apart. A plain 2D top view has no top and bottom walls, so the jet was far less damped than in the real plate. The Reynolds number check (Re about 1400 in the port) used the real 3D port, which did not match the model being solved.

**What changed:** Added the depth friction back as a Darcy porosity term in `constant/fvOptions`, with d = 12 / h² = 1.333e6 m⁻² for h = 3 mm. This is the same physics as Δp/L = 12μU/h². The model is now **2.5D**, not plain 2D. Residuals dropped by 2000 to 6000 times, continuity errors to about 1e-5, and Δp became realistic. Residual plot: `results/residuals_N6.png`.

**Side effect (good):** The velocity profile across each channel is now flat with thin wall layers, which is correct for a shallow channel. The parabolic profile in a real plate is across the depth, not the width.

**Lesson:** Always check that a hand calculation (Re, Δp) describes the model actually being solved, not the real object.

---

## 2. Settings are typed by hand in several files

**Status:** Open

**What we found:** Several study values are typed directly into different files, so changing one means editing several places, and they can disagree:

| Value | Where it is typed now |
|---|---|
| Channel depth h = 3 mm | `constant/fvOptions` (as d = 1.333e6), and in the heat source |
| Inlet velocity 0.25 m/s | `0/U`, and `src/channel_flow.py` |
| Battery heat 200 W | `system/controlDict` (as S = 0.304 K/s) |

**What to change:** Add `depth`, `inlet_velocity` and `heat` to `study.yaml`. In Phase 5, the automation script works out d = 12 / depth² and S = q / (ρ c_p h) and writes them into each case, and `channel_flow.py` reads the velocity from `study.yaml`.

**Also consider:** making depth a study parameter later (for example 2 to 5 mm), since it changes both cooling and Δp strongly.

---

## 3. Flow rate and inlet velocity

**Status:** Watch

**Current choice:** Inlet velocity 0.25 m/s. With a 15 × 3 mm port (D_h = 5 mm) this is about 0.7 L/min, Re about 1400 in the port (laminar), about 150 in the channels.

**What to change later:** Flow rate could become a study parameter (for example 0.3 to 1.5 L/min), keeping Re below about 2000.

---

## 4. Strong flow maldistribution: most water goes through the middle two channels

**Status:** Open (main design finding so far)

**What we found:** In the N6 baseline, the inlet jet crosses the 30 mm inlet header, hits the end of the middle strip, and splits into channels 3 and 4. Water swirls in the header corners and feeds channels 1 and 6 a little more than channels 2 and 5.

Measured at x = 200 mm (halfway along the channels):

| Channel | 1 | 2 | 3 | 4 | 5 | 6 |
|---|---|---|---|---|---|---|
| Share of flow | 8.8% | 6.1% | 35.1% | 35.3% | 5.8% | 8.9% |

Channels 3 and 4 carry 70% of the flow. Lowest / highest flow = 0.17 (an even split would be 1.0, a good design would aim for 0.8 or more).

**Why it matters:** Every channel receives the same heat (the battery above it), but with very different amounts of water. So uneven flow becomes uneven temperature (see section 11). Cells above the starved channels run hottest.

**Why it happens:** The inlet header is too short for the jet to slow down and spread sideways. The port is centred, so the jet points straight at the middle channels.

**What to change:**
- Add **header length** as a study parameter (for example 30 to 80 mm).
- Possible design fixes to test later: longer or tapered headers, an offset or wider inlet port, a small baffle or diffuser in front of the port, or a serpentine layout.
- Changing the number of channels alone will **not** fix this, because the problem is in the header.

**For the surrogate:** Include header length as an input. Record a flow uniformity output (the share of flow through each channel, and the lowest / highest ratio), not just Δp and temperatures.

---

## 5. Most of the pressure drop is at the ports, not in the channels

**Status:** Watch

**What we found:** N6 baseline Δp = 0.0868763 m²/s² (kinematic) = **86.6 Pa**, steady to 6 significant figures between iterations 1600 and 2000. A hand estimate gave about 75 Pa (within about 15%). Over half of it comes from the jet entering the inlet header and squeezing into the outlet port. Channel friction is only about 10 Pa.

**Why it matters:** Δp may change less with the number of channels than expected. Port size may matter more than channel count for pressure.

**What to change:** Consider port width as a study parameter later. When reporting results, separate port losses from channel losses if possible.

---

## 6. Mesh too coarse for narrow channels, and for measuring flow

**Status:** Open (Phase 4)

**What we found:**
- With a fixed 2 mm cell size, the N6 channels (25.8 mm) get about 13 cells across, but the N16 channels (6.6 mm) get only about 3.
- Plot Over Line underestimates the total channel flow by about 6% on the 2 mm mesh (3.532e-3 against 3.750e-3 m²/s at the inlet), because ParaView interpolates to zero at the walls across one coarse cell. The channel shares are still good to about 1 percentage point.

**What to change:**
- Set the cell size from the channel width (for example, at least 10 cells across each channel), instead of one fixed value.
- Run a mesh independence study (Δp, T_max and flow split against cell count) on the narrowest and widest plates.
- For the automated study, measure each channel's flow from OpenFOAM's own face fluxes (phi) on a face zone across each channel, which is exact.

---

## 7. Irregular cells in the headers

**Status:** Watch

**What we found:** Where the channels meet the headers, gmsh fills the gap with uneven quads. `checkMesh` passed (max non-orthogonality 35°, max skewness 0.83), so it is acceptable.

**What to change if needed:** These cells sit exactly where the flow splits between channels, which is the most important region. If the mesh study shows the headers are sensitive, try gmsh smoothing settings or a structured (transfinite) header mesh.

---

## 8. Convergence and how to measure results

**Status:** Open (for Phase 5 automation)

**What we found:**
- With depth friction, residuals fall smoothly until about 1150 iterations, then flatten with slow waves (p about 2e-4, Uy about 3e-5). A small swirl in a header is still moving slightly. But Δp at 1600, 1800 and 2000 iterations agreed to 6 significant figures, so the result is converged for our purposes.
- The Ux residual sits flat at exactly 1e-5 because that is the solver tolerance for U, not because of the flow.
- The temperature residual settles at about 7e-5. The "T is converged" message from `scalarTransport` is meaningless, because its default tolerance is 1.
- **Outlet temperature must be flow weighted.** The plain area average gave 30.03 °C, because slow, hot water near the port walls counts as much as fast water in the middle. The flow weighted average (weighted by phi) gave 29.28 °C, which matches the energy balance.

**What to change:**
- In the automated study, judge convergence by whether Δp and T_max have stopped changing (for example, less than 0.1% change over the last 400 iterations), not only by residual targets. Record the final residuals for each run anyway.
- Always use `operation=weightedAverage, weightField=phi` for outlet temperatures.

**Solver settings that worked:** standard SIMPLE (`consistent no`), relaxation p 0.3, U 0.7 (T uses 0.7 too). T saved only at write times (`writeControl writeTime` in the temperature function).

---

## 9. Coolant properties

**Status:** Watch

**Current choice:** Water at 25 °C, ν = 8.9e-7 m²/s, thermal diffusivity α = 1.44e-7 m²/s, constant properties.

**What to change later:** Water and glycol mixture (as used in EVs) as an upgrade. Properties that change with temperature are ignored for now, which is reasonable while the temperature rise is small.

---

## 10. Heat goes straight into the water, with no metal in the model

**Status:** Watch

**Current choice:** The battery heat (200 W) is added as a uniform heat source in the water in the channel section only (S = 0.304 K/s in a `channels` cell zone, x = 30 to 370 mm, 13,397 cells). The headers and ports are not heated. The strip walls (`heated_walls`) are adiabatic, because in the 2.5D model the heat enters through the top wall, which is not drawn.

**What a real plate does differently:** The top wall and strips are aluminium. Heat above each strip goes down into the strip and out through its sides (fin effect), and the metal spreads heat sideways from hot channels to cooler ones.

**Effect on results:** The overall water temperature rise is correct (it depends only on total heat and flow). The temperature differences between channels are overstated, because there is no sideways spreading through the metal. The model is pessimistic about uniformity.

**What to change later:**
- In Phase 7, run a few conjugate heat transfer cases (`chtMultiRegionFoam`, with the metal included) and measure how much this simplification overstates ΔT.
- Possible version 2: add a second 2D layer for the top wall (heat conduction in the metal, linked to the water with a heat transfer coefficient). This captures sideways spreading while staying fast.

---

## 11. Temperature results: the N6 baseline fails on uniformity

**Status:** Open (main result of Phase 3)

**What we found:**
- Outlet water temperature (flow weighted): **29.28 °C**, against 29.27 °C from the energy balance (within 0.15% of the temperature rise).
- Water temperature across the plate ranges from 25 °C to about 40 °C. The middle channels stay cool. The outer four channels heat up strongly. The hottest water is along the outer walls of channels 1 and 6 near the outlet end, where flow is slowest. Plot: `results/N6_temperature.png`.
- Each channel gets the same heat (about 33 W for N6), so its average temperature rise depends on its share of the flow:

| Channels | Share of flow | Average water rise |
|---|---|---|
| 3 and 4 | 35% each | about 2 °C |
| 1 and 6 | 8.8% each | about 8 °C |
| 2 and 5 | 6% each | about 12 °C |

- T_max (water): about 40 °C. Exact value from the ParaView Information tab: _to add_.

**Why it matters:** The spread of about 15 °C is far above the roughly 5 °C that battery makers aim for between cells. The cells sit a few degrees above the water temperature, so the real cell temperatures are higher still. This design fails on uniformity, mainly because of the flow split in section 4.

**What to change:**
- The battery surface temperature is not calculated yet. Add it in post-processing: T_battery ≈ T_water + q / h, with q = 3,795 W/m² and h from Nu k / D_h (or from the 3D checks).
- For the surrogate, the temperature outputs should be T_max, the spread (T_max minus T_min, or the spread of channel outlet temperatures), and the outlet temperature as a check.

---

## 12. Case setup was not saved in git

**Status:** Done

**What we found:** The working case files (`0/`, `constant/fvOptions`, `system/`) only existed in `runs/N6`, which git ignores. Losing the folder would have lost the setup.

**What changed:** Copied the case setup into `case_template/` in the repo. Phase 5 will build every case from this template.

---

## Checks that passed (keep for confidence)

- Fluid volume from `checkMesh` matched the hand calculation exactly: 64,400 mm² × 2 mm.
- Inlet patch area 3e-5 m² = 15 mm × 2 mm.
- Peak outlet velocity 0.37 m/s ≈ 1.5 × 0.25 m/s, the peak of a fully developed laminar profile.
- Δp from CFD within about 15% of a hand estimate.
- Flow split symmetric to within 0.3 percentage points (centred inlet and outlet).
- `channels` zone: 13,397 cells, matching about 13,200 from the hand calculation.
- Outlet temperature (flow weighted) within 0.006 °C of the energy balance.

---

## Inputs and outputs for the surrogate (current thinking)

**Inputs:** number of channels (6 to 16). Likely additions: header length, flow rate, channel depth, port width.

**Outputs:** Δp, T_max, temperature spread, and flow uniformity (lowest / highest channel flow). Battery surface temperature once section 11 is added.
