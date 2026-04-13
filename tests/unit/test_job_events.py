"""Tests for job events and the event log."""

from __future__ import annotations

from src.app.jobs.events import EventLog, JobStep


class TestEventLog:
    def test_step_context_manager(self) -> None:
        log = EventLog()
        with log.step(JobStep.NORMALIZE):
            pass  # simulate work
        assert len(log.events) == 1
        assert log.events[0].step == JobStep.NORMALIZE
        assert log.events[0].status == "completed"
        assert log.events[0].duration_ms is not None
        assert log.events[0].duration_ms >= 0

    def test_step_failure(self) -> None:
        log = EventLog()
        try:
            with log.step(JobStep.EXECUTE_RUNTIME):
                raise RuntimeError("boom")
        except RuntimeError:
            pass
        assert log.events[0].status == "failed"
        assert log.events[0].error == "boom"

    def test_skip(self) -> None:
        log = EventLog()
        log.skip(JobStep.EXPORT_ALTO, "Not eligible")
        assert log.events[0].status == "skipped"
        assert log.events[0].message == "Not eligible"

    def test_has_failures(self) -> None:
        log = EventLog()
        with log.step(JobStep.NORMALIZE):
            pass
        assert not log.has_failures

        try:
            with log.step(JobStep.VALIDATE):
                raise ValueError("bad")
        except ValueError:
            pass
        assert log.has_failures

    def test_total_duration(self) -> None:
        log = EventLog()
        with log.step(JobStep.NORMALIZE):
            pass
        with log.step(JobStep.VALIDATE):
            pass
        assert log.total_duration_ms >= 0

    def test_to_dicts(self) -> None:
        log = EventLog()
        with log.step(JobStep.NORMALIZE):
            pass
        log.skip(JobStep.EXPORT_ALTO, "skip")
        dicts = log.to_dicts()
        assert len(dicts) == 2
        assert dicts[0]["step"] == "normalize"
        assert dicts[1]["step"] == "export_alto"

    def test_multiple_steps_in_order(self) -> None:
        log = EventLog()
        for step in [JobStep.RECEIVE_FILE, JobStep.NORMALIZE, JobStep.VALIDATE]:
            with log.step(step):
                pass
        steps = [e.step for e in log.events]
        assert steps == [JobStep.RECEIVE_FILE, JobStep.NORMALIZE, JobStep.VALIDATE]
