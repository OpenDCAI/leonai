from middleware.monitor.state_monitor import AgentState, StateMonitor


def test_mark_error_while_active_returns_to_idle_and_preserves_error_flag() -> None:
    monitor = StateMonitor()
    assert monitor.transition(AgentState.READY)
    assert monitor.transition(AgentState.ACTIVE)
    assert monitor.state == AgentState.ACTIVE

    err = RuntimeError("boom")
    assert monitor.mark_error(err)

    # Regression: previously transitioned ACTIVE -> ERROR and stayed wedged, blocking new runs.
    assert monitor.state == AgentState.IDLE
    assert monitor.flags.hasError is True
    assert monitor.last_error_type == "RuntimeError"
    assert monitor.last_error_message == "boom"
    assert monitor.last_error_at is not None


def test_mark_error_outside_active_transitions_to_error_state() -> None:
    monitor = StateMonitor()
    err = ValueError("init fail")
    assert monitor.mark_error(err)
    assert monitor.state == AgentState.ERROR
    assert monitor.flags.hasError is True
