from __future__ import annotations

from cmaes_proxy_sigma_controller.trace import should_trace_proxy_run
from cmaes_proxy_sigma_controller.types import TraceMode


def test_hybrid_traces_target_cells() -> None:
    assert should_trace_proxy_run("sphere", 10, 7, TraceMode.HYBRID)
    assert should_trace_proxy_run("rosenbrock", 20, 3, TraceMode.HYBRID)


def test_hybrid_uses_seed_rule_for_nontarget() -> None:
    assert should_trace_proxy_run("ellipsoid", 40, 20, TraceMode.HYBRID)
    assert not should_trace_proxy_run("ellipsoid", 40, 21, TraceMode.HYBRID)


def test_trace_mode_off_and_full() -> None:
    assert not should_trace_proxy_run("sphere", 10, 0, TraceMode.OFF)
    assert should_trace_proxy_run("anything", 999, 13, TraceMode.FULL)
