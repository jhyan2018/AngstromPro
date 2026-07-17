# -*- coding: utf-8 -*-
"""
Created on Sun Jun 28 2026

@author: jiahaoYan
"""

from typing import Any, Callable


def make_process_task(process_func: Callable, *input_data: Any) -> Callable:
    """
    Pre-bind input data into a closure so that TaskRequest.kwargs
    only carries serializable parameters.

    The returned callable has the signature:
        _run(**params) -> Any

    which internally calls:
        process_func(*input_data, **params)

    Convention for process functions using this bridge:
        - Positional args  = data inputs  (WorkspaceData payloads)
        - Keyword args     = parameters   (scalars, strings, etc.)

    Note
    ----
    ProcessRegistry uses the func(inputs: dict, params: dict) convention
    and does not need this bridge — it builds its own closure internally.
    This helper is available for one-off tasks or custom callables that
    use positional data args rather than the registry convention.

    Example
    -------
        bound = make_process_task(my_func, uds_item.payload)
        request = TaskRequest(
            task_func = bound,
            kwargs    = {"x_min": 0.5, "x_max": 1.0},
            ...
        )
    """
    def _run(**params: Any) -> Any:
        return process_func(*input_data, **params)

    return _run
