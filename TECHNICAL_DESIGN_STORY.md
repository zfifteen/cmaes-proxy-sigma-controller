# TECHNICAL DESIGN STORY

## Why This Controller Exists

Most optimization systems fail in two opposite ways. They either move too boldly and waste computation exploring bad territory, or they become too cautious and stop searching before they have actually found a strong answer. In CMA-ES, that tension is concentrated in sigma, the value that controls how far each generation can step from the current estimate. When sigma is healthy, the optimizer can balance discovery and refinement. When sigma drifts into an unhealthy regime, the entire run can become either chaotic or stagnant.

The cmaes-proxy-sigma-controller exists to address that specific problem without rewriting CMA-ES itself. The design assumes that many teams already trust their core optimizer implementation and do not want a deep fork that is expensive to maintain. The controller therefore lives outside the optimizer internals and acts as a small, observable decision layer. It reads a narrow stream of runtime signals and returns a single control decision about sigma movement. The core optimizer remains intact.

This choice is practical and philosophical at the same time. Practically, it allows quick experimentation and safer deployment across different codebases. Philosophically, it treats control as a separate concern from search mechanics. The optimizer still performs evolution, covariance shaping, and selection. The controller only manages the operating envelope for step-size behavior so the optimizer spends more of its budget in productive search states.

## The Shift in Perspective

Classic tuning often frames sigma adaptation as a smooth parameter problem. This project takes a different view. It treats adaptation as state management over time. The same controller setting can produce good or bad outcomes depending on when the run enters constrained behavior and how long it remains there while budget is still meaningful.

That time-aware framing changes what we pay attention to. Endpoint summaries are still useful, but they are incomplete on their own. Two runs can end with similar endpoint diagnostics while having very different internal histories. One run might preserve broad exploration when it matters most, then tighten late. Another might collapse early, appear stable, and still finish worse because the opportunity to discover better basins was lost before the midpoint.

The controller is therefore designed around observed behavior trajectories, not just terminal conditions. It asks a simple operational question at each generation. Is the run still in an active search state, or has it drifted into a constrained state where adaptation mostly reacts rather than guides? The answer to that question shapes how the controller updates sigma.

## What Makes This a Proxy Controller

The cmaes-proxy-sigma-controller is intentionally external. It does not alter the mathematics of covariance updates, recombination weights, evolution paths, or sampling inside CMA-ES. It observes values that can be surfaced through normal runtime telemetry and returns a scalar adjustment policy for sigma. This keeps the controller portable across implementations and allows the same logic to be tested in many environments with minimal integration risk.

External control also creates discipline. Because the controller cannot reach privileged internals, it must base decisions on signals that are consistently measurable and easy to audit. That constraint is helpful. It reduces hidden coupling and makes post-run diagnosis easier because every decision can be traced to explicit observed inputs.

The design target is not maximal theoretical elegance at all costs. The target is a robust engineering layer that can be deployed incrementally, compared fairly against vanilla baselines, and improved through evidence rather than intuition.

## Architecture in Human Terms

The architecture has four conceptual parts that operate as a loop. A sensing surface gathers proxy-visible runtime indicators each generation. An interpretation layer transforms these indicators into a current behavior reading. A control layer selects the next sigma adjustment under explicit safety boundaries. A telemetry layer records enough context to explain what happened later.

The sensing surface focuses on progress and variability signals that reflect local optimization conditions. It does not try to reconstruct the full hidden state of CMA-ES. The interpretation layer smooths noisy fluctuations so decisions are not dominated by one anomalous generation. The control layer applies bounded multiplicative updates and respects hard limits to prevent runaway behavior. The telemetry layer tracks both endpoint summaries and run-level occupancy patterns so mechanisms can be tested, not guessed.

The boundaries are strict. The controller consumes observations and emits a sigma decision. It never mutates optimizer structures directly. This boundary allows reliable A and B testing against vanilla CMA-ES because the only intentional difference is the sigma policy pathway.

## The Operational Story of a Run

At the start of a run, the controller inherits an initial sigma from the host optimizer configuration. Early generations are treated as information gathering with guarded action. Signals are noisy at this stage, so the controller emphasizes stability over aggression while still allowing responsive movement when evidence is consistent.

As generations proceed, the controller continually interprets whether progress is meaningful relative to local noise. If signals support expansion, sigma can widen within safe bounds to preserve exploration. If signals suggest deterioration or random drift, sigma can contract. If evidence is ambiguous, the controller prefers continuity rather than oscillation.

A critical part of the story is what happens near lower constraints. If sigma repeatedly presses toward the lower floor too early in the budget, the run risks entering a constrained mode where future corrections become less effective. The controller is designed to detect that trend and distinguish temporary contact from persistent occupancy. This distinction matters because occasional floor contact can be healthy late in a run, while prolonged early occupancy can suppress useful discovery.

Recovery behavior is therefore first-class, not an afterthought. When telemetry indicates that the run is becoming trapped in constrained dynamics, the controller can shift from routine adaptation into guarded recovery behavior. Recovery does not mean forcing large jumps blindly. It means widening or relaxing control in a measured way so the run can re-enter an active search regime without destabilizing the optimizer.

Near the end of the budget, priorities change. Exploration value naturally declines as remaining evaluations shrink. The controller allows progressively tighter behavior when justified, while still preventing collapse into misleading endpoint calm. The intent is to finish with credible convergence, not merely with small steps.

## Implementation Shape Without Formal Spec Syntax

The implementation should be organized so each concern is separable, testable, and replaceable. A policy core should own stateful interpretation and action decisions. A telemetry adapter should normalize host runtime values into the controller’s observation format. A safety envelope should enforce hard bounds and guardrails on updates. A trace writer should capture compact per-run summaries and sampled per-generation traces for mechanism analysis.

The policy core should remain deterministic given observations and configuration. Determinism is important because it allows exact replay for debugging and scientific comparisons. Stochastic behavior belongs to the optimizer and benchmark seeds, not to the control layer.

The telemetry adapter should be permissive in what it accepts and strict in what it emits. Different hosts may expose slightly different naming conventions or timing for values. The adapter should handle those differences while producing one canonical internal observation structure.

The safety envelope should be explicit and centralized. Boundaries should not be scattered across multiple modules where behavior becomes hard to reason about. Every clamp, cap, and fallback path should be attributable to one readable control boundary.

The trace writer should support both light and high-rigor modes. Light mode should write minimal run-level diagnostics suitable for routine benchmarking. High-rigor mode should add sampled per-generation traces that enable mechanism testing without creating unsustainable storage pressure.

## Telemetry Expectations and Why They Matter

The controller depends on observability that is rich enough to explain behavior but lean enough to stay practical. Endpoint-only summaries are useful for broad scoreboard comparisons, but they are not sufficient to validate mechanism claims. The design therefore expects a baseline set of run-level indicators for every proxy run and optional deeper traces for selected runs.

Run-level telemetry should capture when constrained behavior first appears, how much of the run occurs in that state, how often the run enters and exits that state, and the effective range sigma actually used. These values let us characterize regime occupancy and compare variants fairly.

Sampled per-generation traces should capture the local decision context across time. They make it possible to separate genuine controller behavior from accidental outcomes caused by seed idiosyncrasies. They also support quality assurance by revealing whether decision logic matches intended design in real runs.

Telemetry is not just for reporting. It is part of the controller’s engineering contract. If the controller cannot explain its behavior post hoc, it is not ready for serious use.

## Expected Behavior Across Problem Families

Not all objective landscapes reward the same sigma behavior. Some families benefit strongly from sustained broad movement early, while others reward earlier contraction once directional information becomes reliable. The controller is designed with this heterogeneity in mind.

On landscapes where narrow early search can miss useful structure, preserving active exploration for longer should improve outcomes even if late-stage convergence appears slower. On landscapes with clear curvature and lower ambiguity, earlier tightening can still perform well. Mixed benchmark outcomes are therefore expected and do not imply design failure by default.

The important question is whether observed wins and losses align with interpretable behavior signatures. If target losses correlate with early persistent constrained occupancy and recover when that pattern is reduced, the controller is behaving in a mechanistically coherent way. If outcomes fluctuate without relationship to occupancy patterns, the control logic is likely under-specified or misaligned with the observed signals.

## Failure Modes and Built-In Mitigations

One failure mode is premature floor dominance, where the run spends too much meaningful budget in constrained motion. The mitigation is early detection of persistent occupancy and controlled recovery behavior that reopens search capacity without overcorrecting.

Another failure mode is oscillatory overreaction, where sigma alternates too aggressively because noisy short-term signals are interpreted as stable evidence. The mitigation is smoothing, hysteresis in decision transitions, and conservative neutral behavior under ambiguity.

A third failure mode is false calm at the endpoint. A run may look stable simply because adaptation authority collapsed earlier. The mitigation is to treat endpoint calm as one signal among many and evaluate it alongside occupancy history.

A fourth failure mode is overfitting to one benchmark family. The mitigation is structured cross-family evaluation and explicit claim boundaries. The controller should be framed as a mechanism-aware engineering layer with bounded scope, not as a universal optimizer replacement.

## How Evaluation Should Be Framed

Evaluation should answer three questions in sequence. First, does the controller change outcomes relative to vanilla CMA-ES in a statistically credible way. Second, do those changes track the mechanism signals the controller claims to manage. Third, do the same relationships hold across independent seed sets and controlled variant arms.

Success is not defined as winning every cell. Success is defined as producing a coherent, testable relationship between controller behavior and outcome direction, then using that relationship to improve decision quality. A mechanism-aware controller should make experimentation more intelligible, not just more optimistic.

Evidence should be labeled by strength. Direct measurements support observational claims. Computed summaries support derived claims. Causal interpretations remain hypotheses until controlled tests disconfirm alternatives. This distinction protects the project from accidental overclaiming.

## Use Cases and Non-Goals

The primary use case is teams that already run CMA-ES and want stronger sigma governance without forking optimizer internals. They need a controller that can be deployed incrementally, benchmarked rigorously, and audited clearly.

A second use case is research programs studying adaptation dynamics. The controller’s telemetry-first design supports mechanistic experiments and makes it easier to test competing explanations.

A third use case is comparative evaluation environments where multiple adaptation ideas are tested under a common harness. Because this controller is external and bounded, it can serve as a reliable baseline for future mechanism-aware variants.

A clear non-goal is replacing internal CMA-ES theory with a black-box heuristic stack. Another non-goal is claiming universal superiority across all landscapes and budgets. The project is about controlled improvement and explanatory power in defined operating regimes.

## Deployment Posture

A practical rollout begins with shadow benchmarking against vanilla CMA-ES under fixed seeds and matrix settings. Once telemetry confirms stable behavior and coherent mechanism signatures, the controller can move into active use for selected workloads where evidence is strongest.

Operational deployment should keep guardrails visible. Configuration changes should be versioned. Telemetry schemas should remain stable enough to support trend analysis over time. Any shift in decision logic should be auditable against prior behavior.

This posture keeps the system scientific and operational at once. It enables learning without sacrificing reliability.

## Closing the Story and Opening the Specification

This story defines the intent and shape of cmaes-proxy-sigma-controller in human terms. It explains why the controller exists, how it should behave, how it should be instrumented, and where its claims end. It is written to be understandable before formalism.

The next document will convert this narrative into a conventional technical specification with explicit interfaces, data schemas, state transitions, configuration contracts, and acceptance tests. That specification will not change the core philosophy established here. It will make it implementation-ready for engineering teams who need exact contracts and reproducible execution details.
