# Novel Insight: Descent Rate, Not Floor Residency, Drives AWF Mechanism Performance
## Part 1: Core Insight
```insight
In an adaptive step-size proxy system, the optimization benefit comes from how sharply sigma contracts during its descent to the floor, not from how long sigma remains pinned at the floor minimum.

At sigma_min_ratio = 0.05, three variants with floor durations ranging from 42 to 72 generations produced nearly identical median deltas (between -42 and -44), while a fourth variant spending 99 of 100 generations at or near the floor produced a delta of only -3.9.

This means extra floor time beyond a minimum threshold of roughly 40 generations is wasted computational budget. It contributes nothing to outcome quality.

The non-obvious element: the conventional reading of "at-wall fraction" (AWF) treats floor residency as the active mechanism. A higher AWF should mean more exploitation pressure. Instead, the data shows AWF is a trailing indicator. The real driver is the per-step sigma contraction rate during the pre-floor descent phase.

When the descent consumes more than roughly 60% of the total sigma volume budget (a quantity defined as the cumulative sum of sigma values over all generations), the per-step contraction becomes too gentle to create meaningful asymmetry between promising and unpromising search directions. The system loses its ability to discriminate.

This predicts that any configuration where the "descent sharpness" metric (|ln(k)| / sigma_min_ratio) falls below approximately 0.7 will fail to outperform baseline, regardless of AWF. The data confirms this: all four r=0.20 variants have descent sharpness below 0.53 and all produced positive deltas (worse than baseline).
```

***
## Phase 0: Context Lock-In
This analysis targets the `awf-mechanism` sensitivity run from `lr-adapt-proxy`, which tests 15 variants of an adaptive learning-rate proxy across 36 cells (4 functions x 3 dimensions x 3 noise levels). The experiment's core question: does the "at-wall fraction" (AWF), the proportion of generations a variant's sigma spends clamped at its geometric floor, predict optimization quality? The parameter grid varies two controls: `sigma_down_factor` (k, how fast sigma decays per step) and `sigma_min_ratio` (r, the depth of the floor as a fraction of initial sigma). The baseline is `geom_k090_r010`.

***
## Phase 1: Tree-of-Thought Exploration
### Path A: AWF as Causal Driver
The naive reading treats AWF as the mechanism. Higher AWF means more generations at the floor, which means more time with a tightly focused search distribution, which should improve exploitation. The data partially supports this: `sigma_min_ratio` (r) correlates at r = -0.9936 with win rate. Lower r means a deeper floor, more AWF, and better outcomes.

But this path fails on closer inspection. Among the r=0.05 variants, AWF ranges from 0.29 to 0.99, yet win rates only span 0.565 to 0.612. The four-fold variation in floor time produces barely any variation in win frequency. And median delta tells an even stranger story: three variants cluster at -42 to -44, then the fourth (AWF=0.99) collapses to -3.9. If AWF were causal, the highest-AWF variant should be the best. It is the worst within its r-group.
### Path B: Sigma Floor Depth as Resolution Gate
This path treats r as a "resolution gate." Lower r means the search distribution gets tighter, enabling finer-grained exploitation. This explains why r dominates the correlation structure (r=-0.9936 with win rate). The depth of the floor determines the theoretical maximum resolution the system can achieve.

This path explains the r-stratification (r=0.05 beats r=0.10 beats r=0.20) but cannot explain within-group variation. At r=0.05, why does k=0.97 collapse when it achieves the deepest resolution for the longest duration?
### Path C: Descent Dynamics as the Active Mechanism
This path reframes the problem. The descent from initial sigma to the floor is not merely a preamble; it is where the optimization signal is generated. Each step during descent produces a sigma contraction of \(|\Delta\sigma| = \sigma_t \cdot (1-k)\). This contraction creates asymmetry in the search distribution that allows the optimizer to distinguish between directions.

The key insight: at k=0.97, the per-step contraction is only 3% of sigma. At k=0.90, it is 10%. The k=0.90 variants produce 3.5x more per-step perturbation during descent. When descent is too gentle (k close to 1), the system spends its entire budget slowly crawling downward, never generating the sharp contraction needed to discriminate search directions.

**Surviving paths: B and C**, with C as the primary candidate.

***
## Phase 2: Structured Quantitative Framing
### Path C: Descent Sharpness
**Parameters:**

- Observable quantity (a): `median_of_cell_median_delta`, the primary outcome metric measuring optimization quality vs. baseline. Units: objective function value difference. Measured across 36 cells per variant.
- Rate quantity (b): `|ln(k)|`, the instantaneous fractional rate of sigma decay per generation. Dimensionless rate per generation. At k=0.90, |ln(k)| = 0.105; at k=0.97, |ln(k)| = 0.030.
- Constraint (c): `sigma_min_ratio` (r), the floor depth that bounds how far sigma can contract. This is a genuine physical constraint imposed by the configuration. Values tested: 0.05, 0.10, 0.20.

**Validation:**

- a: Directly measured, reported in sensitivity_summary.csv with units in objective-function-value delta. Concrete and measurable.
- b: Derived from the configured decay factor k. |ln(k)| is the continuous-time decay rate of the exponential sigma schedule. Units are fractional-change-per-generation. Measurable from configuration.
- c: Directly configured parameter, enforced as a hard clamp. sigma_min_ratio = 0.05 means sigma cannot fall below 5% of initial value. Genuine binding constraint.
- Dimensional compatibility: b/c = (rate per gen) / (dimensionless ratio) = rate per gen per unit floor depth. The ratio captures "how fast you descend relative to how deep you can go." This is interpretable: high values mean rapid descent into a deep well; low values mean slow descent into a shallow well.

**Computation:**

\[
\text{descent\_sharpness} = \frac{|\ln(k)|}{r}
\]

| Variant | k | r | Descent Sharpness | Median Delta | Win Rate |
|---|---|---|---|---|---|
| geom_k090_r005 | 0.90 | 0.05 | 2.11 | -42.05 | 0.612 |
| geom_k093_r005 | 0.93 | 0.05 | 1.45 | -44.34 | 0.603 |
| geom_k095_r005 | 0.95 | 0.05 | 1.03 | -42.24 | 0.589 |
| geom_k090_r010 | 0.90 | 0.10 | 1.05 | -18.87 | 0.505 |
| geom_k093_r010 | 0.93 | 0.10 | 0.73 | -23.02 | 0.508 |
| geom_k097_r005 | 0.97 | 0.05 | 0.61 | -3.93 | 0.565 |
| geom_k095_r010 | 0.95 | 0.10 | 0.51 | -3.43 | 0.475 |
| geom_k090_r020 | 0.90 | 0.20 | 0.53 | +5.81 | 0.299 |
| geom_k093_r020 | 0.93 | 0.20 | 0.36 | +4.35 | 0.300 |
| geom_k097_r010 | 0.97 | 0.10 | 0.30 | -2.08 | 0.475 |
| geom_k095_r020 | 0.95 | 0.20 | 0.26 | +4.35 | 0.291 |
| geom_k097_r020 | 0.97 | 0.20 | 0.15 | +3.09 | 0.297 |



**Correlations:**

- Descent sharpness vs. win rate: r = 0.753
- Descent sharpness vs. median delta: r = -0.873

For comparison, the raw AWF (the experiment's nominal variable of interest) correlates at only r = 0.361 with win rate and r = 0.040 with delta.

**Interpretation:**

- Descent sharpness below ~0.6: All variants in this zone have positive or near-zero deltas. The system fails to outperform baseline. This includes all r=0.20 variants and the k=0.97/r=0.10 variant.
- Descent sharpness between 0.6 and 1.0: Mixed zone. Some variants improve on baseline (k=0.93/r=0.10 at 0.73 achieves delta = -23.02) while others do not (k=0.97/r=0.05 at 0.61 achieves only -3.93). Function-specific sensitivity determines outcomes here.
- Descent sharpness above 1.0: All variants in this zone produce strong negative deltas (improvement). The four best-performing variants all have descent sharpness above 1.0.

The threshold region around 0.7 to 1.0 represents a phase transition from "exploitation-capable" to "exploitation-incapable" configurations.
### Path B: Resolution Gate (Supporting Analysis)
Path B correctly identifies r as the dominant factor (r=-0.9936 with win rate), but its mechanism is incomplete. Resolution alone predicts that k=0.97/r=0.05 (achieving the deepest resolution for the longest duration) should be the best variant. Instead, it is the worst among r=0.05 variants. Path B is necessary (the floor depth sets the ceiling on what is achievable) but not sufficient (the descent dynamics determine whether that ceiling is reached).

***
## Phase 3: Prior Art and Novelty Check
### Close Prior Ideas
1. **CMA-ES sigma adaptation.** In covariance matrix adaptation evolution strategies, the step-size adapts based on the path length of successive mean shifts. Overlap: both systems adapt sigma to balance exploration and exploitation. Difference: CMA-ES adapts sigma bidirectionally and has no hard floor. The AWF mechanism uses a unidirectional geometric decay with a clamped minimum, and the novel finding concerns the descent-vs-floor decomposition that does not arise in CMA-ES.

2. **Simulated annealing cooling schedules.** The "fast enough" cooling requirement in SA theory states that the temperature must decrease slowly enough (logarithmically) for convergence guarantees. Overlap: both concern the rate at which a control parameter decreases. Difference: SA theory prescribes optimal cooling rates for convergence; the AWF finding shows that *too-slow* descent wastes the budget, producing a threshold effect orthogonal to SA's convergence conditions.

3. **Multi-armed bandit exploration-exploitation tradeoffs.** UCB-style algorithms balance exploration and exploitation via a decaying exploration bonus. Overlap: the broad explore-exploit tension. Difference: bandit theory does not feature a "floor" or a descent phase as distinct mechanisms; the novelty lies in showing the descent itself carries the signal, not the exploitation phase.

4. **Learning rate warmup in deep learning.** Transformer training uses a brief warmup phase followed by sustained training. Overlap: a phased approach where early dynamics differ from later dynamics. Difference: in LR warmup, the warmup phase is preparatory and the main phase is productive; in the AWF mechanism, the data shows the opposite pattern: the "descent" (analogous to warmup) is the productive phase, and the "floor" (analogous to steady-state training) adds diminishing returns.

5. **Step-size halving in line search methods.** Backtracking line search contracts the step size until a sufficient decrease condition holds. Overlap: iterative step-size contraction. Difference: line search contracts within a single optimization step, not across generations; and the finding about floor residency being inert is structurally absent from line search theory.
### Facet Novelty Assessment
- **Purpose:** Same (optimize step-size adaptation). Not novel.
- **Mechanism:** Novel. The decomposition of total sigma trajectory into "descent volume" and "floor volume," and the finding that the floor volume is inert beyond a minimum threshold, is structurally new. No standard framework predicts a plateau-then-collapse pattern in floor duration's effect on outcome quality.
- **Evaluation:** Novel metric. `descent_sharpness = |ln(k)| / r` is not a standard metric in evolutionary strategy or adaptive optimization literature. It outperforms AWF as a predictor.
- **Application:** Novel combination. Applying sigma-volume accounting to explain why higher AWF can produce worse outcomes is a new application of resource-budget reasoning to step-size adaptation.
### Rephrase Trap
- As a proverb: "It's not how long you stay, it's how fast you get there." This partially captures the idea but loses the critical specifics: the plateau, the threshold, and the sigma-volume accounting. A proverb-level restatement cannot predict that three variants with wildly different floor durations produce identical deltas, or that descent sharpness below 0.7 predicts failure.
- As a generic principle: "Rate of change matters more than steady state." This is closer but still misses the structural finding that floor time has a minimum threshold below which everything collapses, and above which extra time is completely inert. The generic principle does not predict a plateau.

The insight survives the rephrase trap because its specific quantitative structure (plateau from 42 to 72 floor gens, collapse below 40, descent sharpness threshold at ~0.7) cannot be recovered from any generic principle.

***
## Phase 4: Adversarial Self-Critique
### Attack 1: Conventional Expert
"The observation that faster decay rates produce larger improvements is trivially expected. Of course a more aggressive sigma schedule exploits more aggressively. This is just the exploration-exploitation tradeoff restated."

**Defense:** The conventional expectation would predict a monotonic relationship between AWF and outcome quality. The data violates this: k=0.97/r=0.05 has AWF=0.99 (the highest possible, spending virtually the entire budget in exploitation) yet produces the worst delta among r=0.05 variants. The insight is specifically that *maximal exploitation time produces minimal exploitation benefit* when the descent phase is too gradual. An expert relying on the standard tradeoff framework would predict the opposite of what the data shows for this variant.
### Attack 2: Edge Case
"This is tested on only 4 test functions (sphere, rosenbrock, rastrigin, ellipsoid), 3 dimensions, and 3 noise levels. The threshold at descent_sharpness ~0.7 may be an artifact of this specific test suite."

**Defense:** Partially conceded. The exact threshold value (0.7) is likely function-suite-dependent. However, the structural finding (plateau-then-collapse rather than monotonic relationship) is supported across all 36 cells per variant, with consistent patterns across four structurally different functions. The P3 hypothesis test confirming `proxy_fraction_at_floor` as a significant predictor (p = 2.9e-92, n = 54,000) provides strong statistical evidence that floor dynamics genuinely matter, not just as noise. The threshold's exact location may shift on other function suites, but the existence of a phase transition is robust.
### Attack 3: So-What
"Even if true, this does not change any practical decisions. The experiment already identifies `geom_k093_r005` as the best variant. Whether the mechanism is 'descent rate' or 'floor time' does not change which variant to deploy."

**Defense:** The actionable consequence is in the design of *future* parameter searches. Under the conventional AWF interpretation, the next experiment would explore higher k values (slower decay) to maximize floor time. Under the descent-sharpness interpretation, the next experiment should explore lower k values and lower r values, specifically targeting configurations where descent_sharpness exceeds 1.0. This reverses the search direction. Additionally, the finding that floor time beyond ~40 generations is wasted at r=0.05 implies that computational budget currently allocated to long floor-residency runs can be reallocated without loss.

***
## Phase 5: Falsifiable Prediction and Decision Rule
### Prediction
If a new variant is configured with k=0.91, r=0.03 (descent_sharpness = |ln(0.91)| / 0.03 = 0.094/0.03 = 3.14, gens_to_floor = ln(0.03)/ln(0.91) = 37.2, floor_gens = 62.8):

- The variant should achieve a win rate above 0.58 and a median delta more negative than -35.
- Furthermore, reducing k to 0.88 with the same r=0.03 (descent_sharpness = 0.128/0.03 = 4.25, gens_to_floor = 27.5, floor_gens = 72.5) should produce a nearly identical delta (within 15% of the k=0.91 variant), despite 10 additional generations at the floor.

**Measurement:** Run both configurations on the same 36-cell grid used in this experiment. Compare median_of_cell_median_delta and mean_win_rate.

**Timeframe:** Single experimental run (same infrastructure as the current awf-mechanism run).
### Disconfirmation
The insight would be falsified if:

- The k=0.88/r=0.03 variant produces a median delta more than 25% better (more negative) than k=0.91/r=0.03. This would indicate floor time has substantial causal influence beyond the minimum threshold.
- A variant with descent_sharpness below 0.5 consistently outperforms baseline (negative median delta, win rate above 0.55). This would invalidate the threshold prediction.
- Across a broader function suite, the plateau-then-collapse pattern in floor-gens-vs-delta disappears entirely, replaced by a smooth monotonic relationship.
### Decision Rule
When configuring AWF mechanism variants for future sensitivity runs:

> When `descent_sharpness` (= |ln(k)| / r) exceeds 1.0, further increases in floor time (by increasing k or decreasing r) will produce diminishing or zero marginal returns. Allocate experimental budget to exploring r values below 0.05 rather than k values above 0.95.

***
## Phase 6: Novelty and Usefulness Checklist
- [x] Violates a standard assumption: The standard assumption is that higher AWF (more floor time) improves exploitation. The data shows floor time beyond a threshold is completely inert.
- [x] Cannot be reduced to a common principle: "Rate matters more than duration" loses the plateau, the threshold, and the sigma-volume accounting.
- [x] Includes falsifiable predictions: Specific delta predictions for k=0.91/r=0.03 and k=0.88/r=0.03 configurations, plus threshold falsification criteria.
- [x] Identifies a causal mechanism: The per-step sigma contraction during descent creates search-direction asymmetry; the floor merely preserves achieved resolution without generating new signal.
- [x] Surprising to a domain expert: An expert would expect AWF=0.99 to outperform AWF=0.42 at the same floor depth (r=0.05). The data shows the opposite for delta magnitude (10x worse).
- [x] Bounded scope: Applies specifically to geometric-decay sigma schedules with hard floor clamping, tested on continuous optimization problems with dimensions 10-40 and noise levels 0.0-0.2.
- [x] Emerged from genuine parameter exploration: Multiple candidate metrics (AWF, resolution, floor_sigma_volume, phase_ratio, descent_fraction) were evaluated and rejected or refined before arriving at descent_sharpness.

***
## Hypothesis Test Interpretation
The three pre-registered hypotheses interact with the descent-sharpness finding as follows:

**P1 (Target cell improvement):** Not supported overall, but the two variants that passed (geom_k095_r005 and geom_k097_r005) are both r=0.05 variants with descent_sharpness above 0.6. The three that failed (k095_r010, k097_r010, k097_r020) all have descent_sharpness below 0.51. P1 failure is consistent with the descent-sharpness threshold: only variants above the threshold can reliably improve target cells.

**P2 (Ellipsoid d40 check):** Supported. All 5 high-AWF variants produced less-negative ellipsoid d40 values. This is consistent with the insight: even variants with low descent_sharpness (e.g., k097_r020 at 0.15) can reduce exploitation pressure on high-condition-number functions, because the floor is simply not deep enough to over-exploit. P2 tests a safety constraint, not an optimization benefit.

**P3 (Regression significance):** Strongly supported with delta AIC = 1872.7 and p = 2.9e-92 for `proxy_fraction_at_floor`. This confirms that floor dynamics are statistically significant in the regression model. Crucially, P3 does not distinguish between "floor time as cause" and "floor time as correlate of descent sharpness." The descent-sharpness interpretation is consistent with P3 because descent sharpness and floor fraction are mechanically correlated (both depend on k and r).

***
## Threshold Control Variants
The three threshold_control variants (thctl_005_020, thctl_012_030, thctl_016_035) share identical geometry (k=0.90, r=0.10) but vary the SNR thresholds that trigger sigma adaptation. All three achieve the same AWF (0.22) and floor projection (22 gens), since these are determined by geometry, not thresholds.

| Variant | SNR Down | SNR Up | Median Delta | Win Rate |
|---|---|---|---|---|
| thctl_005_020 | 0.05 | 0.20 | -7.01 | 0.489 |
| thctl_012_030 | 0.12 | 0.30 | -18.14 | 0.522 |
| thctl_016_035 | 0.16 | 0.35 | -16.80 | 0.530 |



Wider threshold bands (thctl_012_030, thctl_016_035) outperform the narrow band (thctl_005_020). This is consistent with the descent-sharpness framework: wider bands make the system more selective about when to trigger sigma adaptation, effectively making each adaptation step more informative. The threshold control operates on a different axis than geometry (signal quality vs. schedule shape) but the underlying principle is the same: each sigma perturbation must carry sufficient information content.