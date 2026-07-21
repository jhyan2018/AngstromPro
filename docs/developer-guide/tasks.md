# Tasks and background execution

AngstromPro's task subsystem keeps expensive or long-running work away from
the Qt GUI thread. `AppContext.tasks` exposes the shared `TaskManager`, which
accepts a `TaskRequest` and returns a `TaskHandle` for observing or cancelling
the work.

Registered scientific processes normally go through `ProcessRunner`, which
builds their task requests and routes results back to a module. Submit a task
directly when implementing infrastructure work that is not a registered
process, such as file loading, thumbnail rendering, or a background scanner.

## Execution backends

| Backend | Intended work | Execution model |
| --- | --- | --- |
| `compute` or `auto` | Finite CPU-oriented work | Shared compute thread pool |
| `io` | Finite file or device I/O | Shared I/O thread pool |
| `async` | Compatibility alias for `io` | Shared I/O thread pool; not an `asyncio` event loop |
| `persistent` | A long-lived cooperative loop | One dedicated low-priority `QThread` per task |

The compute pool size comes from `tasks.max_concurrent_tasks`; the I/O pool
has its own larger limit. Pool tasks accept `high`, `normal`, and `low`
priorities. Priority changes queue order, not the operating-system priority of
already running work. Persistent workers always run at low thread priority.

## Submitting a task

```python
from angstrompro.core.tasks import TaskRequest


def build_preview(path, *, cancel_token=None, progress_callback=None):
    for current in range(10):
        if cancel_token is not None and cancel_token.is_cancelled():
            return None
        # Perform one bounded unit of work here.
        if progress_callback is not None:
            progress_callback(current + 1, 10)
    return {"path": path}


request = TaskRequest(
    task_func=build_preview,
    source_id=self.instance_id,
    task_type="example.build_preview",
    kwargs={"path": path},
    backend="io",
    cancellable=True,
    has_progress=True,
    priority="normal",
)
handle = self._context.tasks.submit(request)
handle.result.connect(self._on_preview_ready)
handle.error.connect(self._on_preview_error)
handle.cancelled.connect(self._on_preview_cancelled)
```

The task manager injects `cancel_token` only when `cancellable=True` and
`progress_callback` only when `has_progress=True`. The callable must accept
those keyword arguments. Results and errors are delivered to the manager on
the Qt thread through queued signals.

## Request and handle contracts

Important `TaskRequest` fields include:

- `source_id`: stable ID of the submitting module or service.
- `task_type`: descriptive ID used by logs and the Task Dashboard.
- `kwargs`: arguments passed to the callable; avoid GUI objects here.
- `backend`, `priority`: execution placement and pool queue priority.
- `cancellable`, `has_progress`: enable injected cooperative callbacks.
- `retries`: retry count after exceptions.
- `timeout_s`: emit a timeout error after the task starts.
- `group_id`: collect related tasks for `cancel_group()`.
- `metadata`: optional descriptive data for observers.
- `silent`: hide internal work from the Task Dashboard.

`TaskHandle` emits `started(task_id)`, `progress(task_id, current, total)`,
`result(task_id, value)`, `error(task_id, traceback_text)`, and
`cancelled(task_id)`. Keep the handle when the caller may need to cancel or
track the operation.

## Cancellation, timeouts, and shutdown

Cancellation is cooperative. `handle.cancel()` sets the injected token; the
callable must check it at sensible boundaries and return promptly. Python
threads cannot be safely killed from another thread.

Likewise, `timeout_s` reports a timeout and removes the task from manager
tracking, but it does not forcibly stop the underlying callable. A task that
must stop promptly should also be cancellable and perform bounded operations.

A persistent task should loop until `cancel_token.is_cancelled()` and put
resource cleanup in a `finally` block. Application shutdown cancels active
tasks, asks persistent loops to finish, and waits briefly for executor threads.
Modules must still close resources they own, such as database connections and
file handles, in their shutdown hooks.

## Thread-safety rules

- Never create or modify Qt widgets from a task callable.
- Pass plain data into workers and update the GUI from handle signals.
- Do not share thread-bound resources such as SQLite connections; create one
  connection per worker thread when required.
- Check cancellation inside loops and between potentially slow operations.
- Use a registered process for reusable scientific transformations; use a
  direct task for application infrastructure.

The Data Browser provides both patterns: thumbnail renders are finite `io`
tasks, while its background scanner is a cancellable `persistent` task.
