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
**Test: 60 mm headers** (channels kept at 340 mm, plate 460 mm long, mesh M2, `--header 60` option in `geometry.py`):

| | 30 mm headers | 60 mm headers |
|---|---|---|
| Flow split | 9.0 / 6.1 / 35.3 / 35.0 / 6.0 / 8.7% | 11.4 / 6.4 / 32.1 / 32.3 / 6.2 / 11.6% |
| Lowest / highest | 0.171 | 0.193 |
| T max | 40.89 °C | 39.65 °C |
| Δp | 88.40 Pa | 89.28 Pa |

(The 60 mm run had not fully settled: Δp changed 1.3% over the last 500 iterations, so these values are good to about 1 to 2%.)

Doubling the header helps only a little. Channels 2 and 5 are still starved. Reason: the depth friction slows a jet over a damping length of about U h² / (12 ν) = 0.25 × 0.003² / (12 × 8.9e-7) ≈ 0.21 m, so the jet carries on for about 200 mm. Header length alone would need about 200 mm to fix the flow, which wastes plate area.

**Better fixes to test:** features that break up or spread the jet at the inlet: a wider inlet port, a baffle in front of the port, a tapered header, or several inlet ports.

**For the surrogate:** Include header length as an input. Record a flow uniformity output (the share of flow through each channel, and the lowest / highest ratio), not just Δp and temperatures.

---

## 5. Most of the pressure drop is at the ports, not in the channels

**Status:** Watch

**What we found:** N6 baseline Δp = 0.0868763 m²/s² (kinematic) = **86.6 Pa**, steady to 6 significant figures between iterations 1600 and 2000. A hand estimate gave about 75 Pa (within about 15%). Over half of it comes from the jet entering the inlet header and squeezing into the outlet port. Channel friction is only about 10 Pa.

**Why it matters:** Δp may change less with the number of channels than expected. Port size may matter more than channel count for pressure.

**What to change:** Consider port width as a study parameter later. When reporting results, separate port losses from channel losses if possible.

---

## 6. Mesh too coarse for narrow channels, and for measuring flow

**Status:** Done (mesh study complete, see section 14; M3 chosen)

**What we found:**
- With a fixed 2 mm cell size, the N6 channels (25.8 mm) get about 13 cells across, but the N16 channels (6.6 mm) get only about 3.
- Plot Over Line underestimates the total channel flow by about 6% on the 2 mm mesh (3.532e-3 against 3.750e-3 m²/s at the inlet), because ParaView interpolates to zero at the walls across one coarse cell. The channel shares are still good to about 1 percentage point.
- The straight channel validation (section 13) confirms it: with 2 mm cells, the side wall friction is under-resolved (−2.4%). About 1 mm cells near the walls bring the error under 1%.

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
- The steady solver can converge on a coarse mesh and fail on a finer one, even when the flow is steady (see section 14). Convergence must be checked on every mesh.
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

- T_max (water): about 40 °C. 41.41 °C on mesh M1 (from `case_results.py`).

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

**Inputs:** number of channels (6 to 16). Likely additions: header length, flow rate, channel depth, port width, and inlet features that spread the jet (baffle, tapered header, several ports).

**Outputs:** Δp, T_max, temperature spread, and flow uniformity (lowest / highest channel flow). Battery surface temperature once section 11 is added.

The flow is steady (section 14), so single steady values are fine as outputs, as long as every run is checked for convergence.

## 13. Validation: straight channel against exact solutions

**Status:** Done (Phase 4, Part A)

**What we did:** Simulated one straight channel, 25.8 mm wide (an N6 channel) and 1 m long, with the same solver settings as the plate. Measured the pressure gradient between x = 0.5 and 0.9 m (fully developed flow) and compared it with exact formulas. Script: `src/validate_channel.py`.

**A1, no depth friction** (textbook flow between two walls, Δp/L = 12νU/W², U = 0.002 m/s, 13 cells across): **−1.16%** from theory.

**A2, with depth friction** (our 2.5D model, exact Brinkman solution, U = 0.024 m/s):

| Cells across | Cell size | Difference from theory | Iterations |
|---|---|---|---|
| 13 | 1.98 mm | −2.43% | 1041 |
| 26 | 0.99 mm | −0.97% | 559 |
| 52 | 0.50 mm | −0.30% | 141 |

**What it shows:**
- The solver, boundary conditions and the depth friction term are correct. The 2.5D model matches the exact solution.
- The remaining error comes from the side walls. With depth friction, the water slows down only in a thin layer next to each side wall, h/√12 = 0.87 mm thick. With 2 mm cells, that layer sits inside the first cell and is under-resolved. The side walls add about 7% to the pressure drop, so missing part of it gives the −2.4%.
- Halving the cell size cuts the error by about 2.5 to 3 times, so the results converge steadily towards the exact answer.

**What to change:** Cells next to the walls should be about 1 mm or smaller (within 1% of theory). Rather than making every cell smaller (about 4 times slower per run), refine only near the walls and keep larger cells in the middle of the channels, where the flow is flat. Test this in the plate mesh study (Part B).

## 14. Mesh study: results and chosen mesh

**Status:** Done (Phase 4, Part B)

**What we did:** Ran the N6 plate (30 mm headers) on 4 meshes, with wall cells half the size of the main cells from M2 onwards. Each mesh has roughly twice the cells of the last.

**Problem found on the way:** `simpleFoam` converged on M1 and M2 but not on finer meshes. Residuals went flat at about 0.1 to 0.2 and Δp kept changing. Smaller relaxation factors (p 0.2, U 0.5) did not fix it. A careful transient run of M3 (`pimpleFoam`, Courant 0.8) showed the flow is laminar and steady: Δp settled flat at 94.3 Pa after about 2 s. The steady solver's corrections were overshooting and looping, which is a numerical problem, not physical unsteadiness. My first guess (unsteady jets) was wrong, and the transient run is what showed it.

**Method used for M3 and M4:** pseudo-transient flow (`pimpleFoam`, max Courant 5, 3 outer correctors, 4 s of simulated time, 6 cores in parallel), then temperature on the frozen flow (section 15). On M3 this matched the careful transient run (Δp 93.99 vs 94.33 Pa, same flow split) about 25 times faster.

**Final results** (all temperatures from the frozen flow method with the upwind scheme, all outlet temperatures 29.27 °C, matching the energy balance):

| Mesh | Main / wall cells | Cells | Δp (Pa) | Change | T max (°C) | Lowest / highest flow |
|---|---|---|---|---|---|---|
| M1 | 2 / 2 mm | 17,358 | 86.62 | | 40.28 | 0.166 |
| M2 | 2 / 1 mm | 27,816 | 88.40 | +2.1% | 38.80 | 0.171 |
| M3 | 1.4 / 0.7 mm | 54,740 | 93.99 | +6.3% | 40.06 | 0.162 |
| M4 | 1 / 0.5 mm | 103,218 | 95.51 | +1.6% | 41.37 | 0.152 |

**What it shows:**
- Δp levels off: +6.3% from M2 to M3, then +1.6% from M3 to M4. Richardson extrapolation from M2 to M4 gives a mesh-independent Δp of about 96 to 97 Pa, so M3 is about 3% low and M4 about 1 to 2% low.
- T max rises slowly with refinement on M2 to M4, because the upwind scheme smooths the hottest spots less on finer meshes. M3 is probably about 1.5 to 2 °C below the true value.
- The flow split is stable on every mesh (about 9 / 6 / 35 / 35 / 6 / 9%). The uneven flow is a real result, not a mesh effect.

**Chosen mesh: M3** (1.4 mm main cells, 0.7 mm at the walls), now the default in `study.yaml`. Every design uses the same settings, so the small, consistent error largely cancels when comparing designs, which is what the surrogate learns. About 6 minutes per design on 6 cores, against about 18 for M4.

**To do at the end of the study:** rerun a few designs (for example the best and worst) on M4 to confirm the error stays at about 3% for Δp and 1.5 to 2 °C for T max.

**Lessons:**
- A steady solver can converge on a coarse mesh and fail on a fine one. Convergence must be checked on every mesh.
- Check a hunch before believing it: the transient run overturned the "unsteady flow" explanation.
- A pseudo-transient run is a robust way to reach a steady answer when the steady solver will not converge.

## 15. How the temperature is solved

**Status:** Done

**Method:** The flow is solved first, then the temperature is solved on the frozen flow with `scalarTransportFoam` (steady, 2000 iterations), using `src/frozen_T.sh`. This works because temperature does not affect the flow when properties are constant (one-way coupling). It takes about 1 to 3 minutes per case.

**What we found on the way:**
- 200 iterations was not enough: the outlet temperature depended on the starting point (29.30 vs 29.60 °C on M3). 2000 iterations fixed it.
- Steady temperature solves with accurate schemes can run away: T max of 268 °C on M4 with `limitedLinear`, and about 10¹³ °C on M3 with `linearUpwind`. These schemes are not guaranteed to be stable or bounded in a steady solve.
- Fix: `bounded Gauss upwind` for `div(phi,T)`, with T relaxation 0.7 and the PBiCGStab solver. Upwind is guaranteed bounded (it cannot create temperatures beyond what the heat input allows), at the cost of slightly smoothing the hottest spots. The smoothing shrinks as the mesh gets finer.
- All four meshes were rerun with the same scheme, so the mesh study compares like with like.

**Lesson:** Always sanity check against physics. The outlet temperature must match the energy balance, and T max cannot be far above what the heat input allows. Both checks caught the problem immediately.

**Possible improvement later:** solve the temperature as a pseudo-transient (with a time term for stability) using `limitedLinear`, for sharper temperature peaks.

## 16. The study: 40 designs, cooling against pumping pressure

**Status:** Done (Phase 5)

**What we did:** Varied the number of channels (6 to 16) and the inlet velocity (0.1 to 0.3 m/s) over 40 designs chosen with a Latin hypercube (`src/doe.py`, fixed seed 42): 30 for training the surrogate, 10 kept aside for testing. Each design runs automatically (`src/run_case.py`, `src/run_all.py`): geometry and mesh (M3 settings), pseudo-transient flow on 6 cores starting from rest (end time 1.5 / U so every design takes a similar number of steps), then frozen flow temperature. Results in `results.csv`.

**Battery heat fixed at 200 W for every design.** The heat source used to be a fixed rate per volume of water (0.304 K/s). With more channels there is more metal and less water in the channel section (155 mm of water across the plate for 6 channels, 105 mm for 16), so that would have put in about 200 W for 6 channels but only about 136 W for 16, flattering the designs with more channels. `run_case.py` now works out the rate for each design: S = heat / (ρ c_p × depth × water area).

**Checks:** All 40 runs converged. Worst energy balance error 0.002 °C, worst flow check error 0.0%, worst Δp change over the last fifth of a run 0.06%. Total computing time 4.2 hours (about 6 minutes per design).

**Method note:** On the same mesh, the pseudo-transient and steady methods give Δp about 1.5% apart (85.0 against 86.6 Pa on M1), and the pseudo-transient result shifts by about 0.5% with the time step size. This comes from how OpenFOAM couples pressure and velocity in each method. Every design uses the same method, so comparisons between designs are not affected.

**What we found:**
- **A clear trade-off:** along the Pareto front, T max falls from 40.1 to 30.9 °C as Δp rises from 23 to 132 Pa.
- **Diminishing returns:** from 23 to 54 Pa, T max drops 6.4 °C. From 54 to 132 Pa, only 2.9 °C more. The sweet spot is about 35 to 55 Pa (T max about 34 to 36 °C).
- **More channels win:** nearly every Pareto design has 11 to 16 channels. No 6 or 7 channel design is on the front.
- **Slower flow spreads more evenly:** the lowest / highest channel flow is about 0.42 to 0.50 at 0.10 to 0.13 m/s, but only 0.25 to 0.28 at 0.26 to 0.30 m/s. This matches the jet damping length U h² / (12 ν), which is proportional to velocity (about 85 mm at 0.10 m/s, about 240 mm at 0.29 m/s).
- **Pumping harder can make parts of the plate worse:** in run_009 (8 channels, 0.29 m/s) the jet sends almost all the water down the two middle channels, and one channel gets only 1.4% of the flow of the busiest one. Its water reaches 118 °C in the model, against about 40 °C for every other design. The effect is real (fast jet, few channels), but the temperature is exaggerated because the model has no metal to spread heat sideways (section 10).

**For the surrogate:** run_009 is an extreme point that a smooth surrogate will struggle with. Options for Phase 6: train on the other designs and report run_009 separately, predict a transformed T max, or add a flow uniformity output so the surrogate can flag designs at risk of starving a channel.

**Plot:** `results/tradeoff.png` (run_009 shown as a labelled marker at the top edge).

## 17. The surrogate: Gaussian process for Δp and T max

**Status:** Done (Phase 6)

**What we did:** Trained a Gaussian process (scikit-learn) to predict Δp and T max from the number of channels N and the inlet velocity U, both scaled to 0 to 1. Kernel: constant × RBF with a separate length scale for N and U, plus a white noise term. Trained on the 29 training designs (run_009 left out, see section 16), tested on the 10 test designs it never saw (`src/surrogate.py`).

**Choosing the models (results/surrogate_comparison.png):**
- Δp trained directly: mean test error 0.86 Pa, consistently predicting low (bias −0.49 Pa).
- **Δp trained on log(Δp): mean error 0.55 Pa (about 1%), bias −0.31 Pa, 0 of 10 outside ±2 standard deviations. Chosen.** Log turns the curved rise of Δp with U into something close to a straight line, which is easier to learn.
- T max trained directly: mean error 0.52 °C, but 5 of 10 test designs outside ±2 sd. The model chose zero noise and a very short length scale in N (about 1.4 channels), so it believed every reading exactly and was overconfident.
- T max on the log of the rise above 25 °C: mean error 0.47 °C, 2 of 10 outside.
- Forcing a smooth surface (log of rise with a noise floor): the model chose a long length scale and lots of noise, and predicted worst of all (worst error 2.74 °C). **So the sharp change of T max with N is mostly physical, not mesh noise.** The likely cause is how the inlet jet lines up with the channels and ribs.
- **T max trained directly with a noise floor of 0.01: mean error 0.62 °C, all 10 test designs within ±2 sd. Chosen**, giving up 0.15 °C of accuracy for uncertainty that can be trusted.
- Every T max version predicts slightly low (−0.4 to −0.8 °C), with the misses at the hottest designs (37 to 40 °C). A smooth model cuts off sharp peaks between training points.

**run_009:** every version predicts its Δp well (120.5 against 120.2 Pa) but its T max at about 40 °C against the true 118 °C. Δp depends on the whole plate's resistance and changes smoothly. T max is set by the single worst channel and can jump when a channel is starved. N and U alone don't tell the surrogate when that happens.

**Using the surrogate (`src/surrogate_maps.py`, results/surrogate_maps.png):** final models trained on all 39 designs. Predicts 891 designs (11 channel counts × 81 speeds) in about a second, against about 89 hours of CFD. Best design for each pressure budget, two of them checked with new CFD runs:
- 30 Pa: N16, 0.113 m/s. Predicted Δp 29.8 Pa, T max 35.8 ± 1.7 °C. **CFD: Δp 29.8 Pa, T max 36.9 °C.** Inside the range, and about 0.9 °C cooler than any study design within that budget. Uniformity 0.555, the most even flow sharing of any design.
- 50 Pa (N16, 0.160 m/s) and 80 Pa (N16, 0.212 m/s): agree with the simulated Pareto front.
- 120 Pa: N11, 0.285 m/s. Predicted Δp 119.5 Pa, T max 30.6 ± 1.4 °C. **CFD: Δp 121.0 Pa, T max 33.5 °C.** Outside the range, and worse than the 16 channel designs already found. The centre channel, in line with the inlet jet, takes 26% of the flow.
- The first N11 check run did not converge (Δp still changing 2.5%) and needed 3 times the run length. `run_case` now takes a `travel` option (default 1.5 m). T max barely changed (33.4 to 33.5 °C), only Δp crept up.

**Sampling experiment (`src/sampling.py`, results/sampling.png):** trained on 5, 10, 15, 20, 25 and 29 designs (10 random picks at each size), tested on the same 10 designs.
- Δp error: 12.7%, 2.2%, 1.7%, 1.6%, 1.1%, 1.0%. Below the 3% M3 mesh error from 10 simulations onwards.
- T max error: 1.77, 1.38, 1.32, 1.16, 0.69, 0.62 °C. Still falling at 29.
- Whole-plate quantities like Δp are cheap to learn. Local extremes like T max need far more data, so the number of simulations should be set by the hardest output, or extra simulations aimed where T max is bumpy.

**Lessons for the surrogate:**
- Trust it for Δp everywhere. Trust it for T max where flow shares evenly, and check with CFD where the inlet jet dominates.
- Add flow uniformity as an output, so the surrogate can flag designs at risk of starving a channel.
- Phase 7 options: adaptive sampling (add CFD runs where the surrogate is unsure or where T max is bumpy), a multi-fidelity surrogate (cheap M1 runs plus M3), and the two check runs fed back into training.

## 18. Upgrade 1: flagging designs where the jet may starve a channel

**Status:** Done (Phase 7)

**What we did:** Trained a Gaussian process on the log of flow uniformity (lowest / highest channel flow), with run_009 kept in, because recognising designs like it is the point. Flag a design if the low end of its 95% range is below 0.2 (`src/uniformity.py`, results/uniformity_map.png). The limit of 0.2 sits between normal high speed designs (0.25 to 0.28) and the jet dominated ones (run_009 0.014, the N11 check 0.168).

**Tested on the 10 test designs plus the 2 Phase 6 check runs:**
- Predictions mostly within 0.01 to 0.05 of the true value.
- All three designs truly below 0.2 were flagged (run_032 0.100, run_035 0.159, N11 check 0.168), with no false alarms.
- The N11 check was flagged only because of its wide range (best guess 0.217, range 0.084 to 0.562). The cautious rule (flag on the low end, not the best guess) is what caught it.
- Length scale in N of 0.08: uniformity changes sharply from one channel count to the next, consistent with the jet lining up differently with odd and even channel counts.
- The model chose zero noise again, so some ranges are slightly too tight (2 of 12 true values just above their range). Both misses are in the safe direction.

**The key test:** trained on the 40 study designs only (what the Phase 6 surrogate knew), the flag passes all three N16 picks and flags the N11 pick (best guess 0.183, could be as low as 0.127). It would have warned us before running the failed design.

**Limits:** a low uniformity doesn't always mean T max is predicted badly (run_032 and run_035 were predicted within about 0.4 °C in Phase 6). The flag means "check with CFD", not "wrong".

## 19. Upgrade 2: adaptive sampling

**Status:** Done (Phase 7)

**What we did:** Started from 10 random training designs (seed 0), then 8 times over: the T max surrogate predicted all 891 grid designs, the one with the largest uncertainty was run in CFD (`run_case`), added to the training data, and both surrogates retrained. Error measured on the same 10 test designs after every step (`src/adaptive.py`, adaptive_results.csv, adaptive_history.csv, results/adaptive_vs_random.png). Designs with uniformity below 0.05 are kept out of the T max training, as with run_009. All 8 runs converged first time, about 30 minutes in total.

**Designs chosen, in order:** 6 ch 0.10, 16 ch 0.10, 16 ch 0.30, 6 ch 0.30, 11 ch 0.10, 11 ch 0.30, 6 ch 0.17, 6 ch 0.10 (repeat). The four corners first, then the middles of the edges. A Gaussian process is least sure at the edges, and the Latin hypercube never places designs right on them.

**Results:**
- T max error: 1.71 °C at 10 simulations, 0.85 °C at 11, 0.69 °C at 17. Random sampling (step D average) needed 25 simulations for 0.69 °C. About 30% fewer simulations.
- The first pick alone (6 ch, 0.10 m/s, the hottest corner) halved the T max error. With 11 simulations, adaptive beat random with 20.
- Δp error: 2.6% at 10, 0.8% by 13, then flat (limited by the mesh, not the data).
- Then a plateau from 12 to 16: the edge designs reduced uncertainty where the test designs aren't. Picking purely by uncertainty spends many runs on the boundaries.
- Some individual random picks did better than adaptive (one 20 simulation pick at about 0.5 °C). Adaptive beats the typical random pick, without relying on luck.
- Caveats: one starting set only, and a 10 design test set, so "about 30% fewer" is an indication.

**The repeat:** design 8 repeated design 1, because the T max noise floor keeps the reported uncertainty above zero even where a result already exists. The script now skips designs already run. Bonus: a repeatability check. Δp 21.504 against 21.499 Pa, T max 41.040 against 41.042 °C. The CFD repeats to within 0.02%.

**New designs on the Pareto front:**
- 16 ch, 0.30 m/s: T max 30.4 °C at 141.7 Pa, the coolest design so far.
- 6 ch, 0.10 m/s: Δp 21.5 Pa, the lowest pressure drop so far.
- 11 ch, 0.30 m/s: uniformity 0.149, confirming the 11 channel jet effect.

**Better ways to choose (future work):** combine uncertainty with how promising a design is (for example expected improvement), or aim at where the test or target designs actually are, rather than uncertainty alone.

## 20. Upgrade 3: multi-fidelity surrogate (cheap M1 runs plus a few M3 runs)

**Status:** Done (Phase 7)

**What we did:** Ran all 40 study designs again on the coarse M1 mesh (2.0 mm cells, no wall refinement), using a new `mesh` option in `run_case` (`src/run_all_m1.py`, results_M1.csv). All 40 completed in about 40 minutes. Then compared two surrogates using the same random picks of M3 training designs (3, 5, 10, 15, 20 and 29, 10 picks each), tested on the same 10 M3 test designs (`src/multifidelity.py`, results/multifidelity.png):
- **M3 only:** a surrogate trained on the picked M3 runs, as before.
- **Multi-fidelity:** a surrogate trained on the 29 M1 training runs gives the overall shape, and a second surrogate learns the gap between M1 and M3 from the picked M3 runs. Prediction = M1 surrogate + gap. M1 results at the test designs were not used.

**Cost:** M1 runs take 0.5 min each, M3 runs 7.2 min each (about 14 times more).

**Results (test error, Δp % / T max °C):**
- M1 surrogate alone: 5.1% / 0.54 °C. M1's Δp is consistently low (as in Phase 4), but its T max is already as good as the M3 only surrogate.
- 3 M3 runs: M3 only 19.4% / 2.78 °C, multi-fidelity 2.2% / 0.58 °C.
- 5 M3 runs: M3 only 5.2% / 1.96 °C, multi-fidelity 1.8% / 0.56 °C.
- 29 M3 runs: M3 only 1.0% / 0.62 °C, multi-fidelity 0.8% / 0.22 °C.
- **29 M1 + 5 M3 runs (51 min of computing) matches 29 M3 runs (209 min) on T max, with Δp within the mesh error. About a quarter of the computing time.**
- With all 29 M3 runs as well, T max error 0.22 °C, the best surrogate in the project.

**Open question:** the M1 surface predicts M3 T max better than an M3 surrogate trained on the same designs. This suggests part of the bumpiness in M3 T max is numerical scatter (the single hottest cell moving on the finer mesh), not only the physical jet effects found in sections 17 and 18. Probably both. A check: compare T max with a flow weighted or area averaged hot spot measure, which should be less sensitive to single cells.