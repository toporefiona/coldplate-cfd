# Design notes

Things we have learned about the cold plate design and the model, and what needs to change later. This is not a list of code slips (a missing bracket, a typo). It is the list of decisions, assumptions and findings that affect the design, the study, or the surrogate model.

Status: **Open** = still to do. **Done** = changed already. **Watch** = fine for now, check again later.

Last updated: 28 October 2026

---

## 1. The 2D model was missing the friction of the top and bottom walls

**Status:** Done

**What we found:** The first `simpleFoam` run on N6 did not converge. Residuals stuck at about 0.02 to 0.08 for 2000 iterations, and continuity errors were high. The jet from the inlet port was flapping in the header.

**Why:** A real channel is about 3 mm deep. Most of its friction comes from the top and bottom walls, only 3 mm apart. A plain 2D top view has no top and bottom walls, so the jet was far less damped than in the real plate. The Reynolds number check (Re about 1400 in the port) used the real 3D port, which did not match the model being solved.

**What changed:** Added the depth friction back as a Darcy porosity term in `constant/fvOptions`, with d = 12 / h² = 1.333e6 m⁻² for h = 3 mm. This is the same physics as Δp/L = 12μU/h². The model is now **2.5D**, not plain 2D. It converged and Δp became realistic.

**Lesson:** Always check that a hand calculation (Re, Δp) describes the model actually being solved, not the real object.

---

## 2. Channel depth is assumed, and not yet in the settings

**Status:** Open

**What we found:** The 3 mm channel depth sets both the inlet velocity choice and the friction coefficient d, but it is only typed by hand in `fvOptions`.

**What to change:**
- Add `depth: 3` to `study.yaml`.
- Have the automation script work out d = 12 / depth² and write it into `fvOptions` for each run.
- Consider making depth a study parameter later (for example 2 to 5 mm), since it changes both cooling and Δp strongly.

---

## 3. Flow rate and inlet velocity

**Status:** Watch

**Current choice:** Inlet velocity 0.25 m/s. With a 15 × 3 mm port this is about 0.7 L/min, Re about 1400 in the port (laminar), about 150 in the channels.

**What to change later:** Flow rate could become a study parameter (for example 0.3 to 1.5 L/min), keeping Re below about 2000. If it does, the inlet velocity must be written per run by the automation script.

---

## 4. Strong flow maldistribution: most water goes through the middle two channels

**Status:** Open (main design finding so far)

**What we found:** In the N6 baseline, the inlet jet crosses the 30 mm inlet header, hits the end of the middle strip, and splits into channels 3 and 4. Channels 1, 2, 5 and 6 get almost no flow. Water swirls in the header corners instead.

**Why it matters:** Battery cells above the outer channels would be poorly cooled and run hot. This is the main source of temperature non-uniformity (ΔT) between cells.

**Why it happens:** The inlet header is too short for the jet to slow down and spread sideways. The port is centred, so the jet points straight at the middle channels.

**What to change:**
- Add **header length** as a study parameter (for example 30 to 80 mm).
- Possible design fixes to test later: longer or tapered headers, an offset or wider inlet port, a small baffle or diffuser in front of the port, or a serpentine layout.
- Changing the number of channels alone will **not** fix this, because the problem is in the header.

**For the surrogate:** Include header length as an input. Record a flow uniformity output (the share of total flow through each channel, or the ratio of the lowest to the highest channel flow), not just Δp and temperatures.

---

## 5. Most of the pressure drop is at the ports, not in the channels

**Status:** Watch

**What we found:** N6 baseline Δp = 0.0868763 m²/s² (kinematic) = **86.6 Pa**. A hand estimate gave about 75 Pa (within about 15%). Over half of it comes from the jet entering the inlet header and squeezing into the outlet port. Channel friction is only about 10 Pa.

**Why it matters:** Δp may change less with the number of channels than expected. Port size may matter more than channel count for pressure.

**What to change:** Consider port width as a study parameter later. When reporting results, separate port losses from channel losses if possible.

---

## 6. Mesh too coarse for narrow channels

**Status:** Open

**What we found:** With a fixed 2 mm cell size, the N6 channels (25.8 mm) get about 13 cells across, but the N16 channels (6.6 mm) get only about 3. That is too few to capture the velocity profile from wall to centre.

**What to change:**
- Set the cell size from the channel width (for example, at least 10 cells across each channel), instead of one fixed value.
- Run a mesh independence study (Δp and T_max against cell count) on the narrowest and widest plates.

---

## 7. Irregular cells in the headers

**Status:** Watch

**What we found:** Where the channels meet the headers, gmsh fills the gap with uneven quads. `checkMesh` passed (max non-orthogonality 35°, max skewness 0.83), so it is acceptable.

**What to change if needed:** These cells sit exactly where the flow splits between channels, which is the most important region. If the mesh study shows the headers are sensitive, try gmsh smoothing settings or a structured (transfinite) header mesh.

---

## 8. Convergence: residual targets are stricter than needed

**Status:** Open

**What we found:** With depth friction, residuals fall smoothly until about 1150 iterations, then flatten with slow waves (p about 2e-4, Uy about 3e-5). A small swirl in a header is still moving slightly. But Δp at 1600, 1800 and 2000 iterations agreed to 6 significant figures, so the result is converged for our purposes.

**What to change:** In the automated study, judge convergence by **whether Δp (and later T_max) has stopped changing**, for example less than 0.1% change over the last 400 iterations, not only by residual targets. Record the final residuals for each run anyway.

**Solver settings that worked:** standard SIMPLE (`consistent no`), relaxation p 0.3, U 0.7.

---

## 9. Coolant properties

**Status:** Watch

**Current choice:** Water at 25 °C, ν = 8.9e-7 m²/s, constant properties.

**What to change later:** Water and glycol mixture (as used in EVs) as an upgrade. Properties that change with temperature are ignored for now, which is reasonable while the temperature rise is small.

---

## Checks that passed (keep for confidence)

- Fluid volume from `checkMesh` matched the hand calculation exactly: 64,400 mm² × 2 mm.
- Inlet patch area 3e-5 m² = 15 mm × 2 mm.
- Peak outlet velocity 0.37 m/s ≈ 1.5 × 0.25 m/s, the peak of a fully developed laminar profile.
- Δp from CFD within about 15% of a hand estimate.

---

## Inputs and outputs for the surrogate (current thinking)

**Inputs:** number of channels (6 to 16). Likely additions: header length, flow rate, channel depth, port width.

**Outputs:** Δp, T_max, ΔT across the plate, and a flow uniformity measure.
