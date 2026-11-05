# -*- coding: utf-8 -*-
"""
Created on Fri Oct 02 2026

@author: jiahaoYan
Regression tests for optional process cancellation and progress callbacks.
"""

from angstrompro.core.processes import ProcessEntry, ProcessRegistry, ProcessSchema


def _registry_with(name, function):
    registry = ProcessRegistry()
    registry._entries[name] = ProcessEntry(
        name=name,
        label="Callback test",
        category="Test",
        func=function,
        schema=ProcessSchema(),
    )
    return registry


def test_run_passes_callbacks_only_when_the_process_declares_them():
    seen = {}

    def callback_process(
        inputs, params, *, annotations=None, cancel_token=None,
        progress_callback=None,
    ):
        seen.update(
            token=cancel_token,
            callback=progress_callback,
            annotations=annotations,
        )

    token = object()
    callback = lambda current, total: None
    registry = _registry_with("test.callbacks", callback_process)
    registry.run(
        "test.callbacks", {}, {}, cancel_token=token,
        progress_callback=callback,
    )

    assert seen == {
        "token": token,
        "callback": callback,
        "annotations": {},
    }

    legacy_called = []

    def legacy_process(inputs, params, *, annotations=None):
        legacy_called.append(True)

    registry._entries["test.legacy"] = ProcessEntry(
        name="test.legacy",
        label="Legacy test",
        category="Test",
        func=legacy_process,
        schema=ProcessSchema(),
    )
    registry.run(
        "test.legacy", {}, {}, cancel_token=token,
        progress_callback=callback,
    )
    assert legacy_called == [True]


def test_submit_marks_callback_aware_process_as_cancellable_with_progress():
    seen = {}

    def process(
        inputs, params, *, annotations=None, cancel_token=None,
        progress_callback=None,
    ):
        seen["token"] = cancel_token
        seen["callback"] = progress_callback

    class Manager:
        request = None

        def submit(self, request):
            self.request = request
            return request

    manager = Manager()
    registry = _registry_with("test.submit_callbacks", process)
    request = registry.submit(
        "test.submit_callbacks", {}, {}, task_manager=manager,
    )

    assert request.cancellable is True
    assert request.has_progress is True
    token = object()
    callback = lambda current, total: None
    request.task_func(cancel_token=token, progress_callback=callback)
    assert seen == {"token": token, "callback": callback}
