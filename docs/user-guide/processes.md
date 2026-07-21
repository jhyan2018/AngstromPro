# Processes

Processes are registered analysis operations. A process declares the data it
accepts, any annotations it needs, its parameters, and the result it produces.
AngstromPro uses this information to present the correct dialog and to avoid
offering incompatible operations where possible.

## Run a process

1. Load or select the required workspace data.
2. Choose an operation from the module's **Process** menu.
3. Supply any additional inputs and parameters requested by the dialog.
4. Start the process.

Long-running operations execute through the task system so the interface can
remain responsive. Successful results are added to the module workspace and
record their processing history. Parameter values are remembered for later
runs.

Some operations need annotations such as picked points, a region, or reference
points. In the Image Stack Viewer, create these from the **Points** menu before
running the process.

## Process Browser

Open **Process → Process Browser…** or press `Ctrl+B` to inspect every
registered process. The browser can filter by name, label, or category and
shows:

- Process ID and description
- Required input ports and dimensionality
- Output types
- Parameters, defaults, ranges, and units

The naming convention uses `_1D` for operations on curve stacks (`ndim=2`) and
`_2D` for operations on image stacks (`ndim=3`). Verify axis orientation in the
item inspector before processing unfamiliar data.

## Built-in process categories

The Process menu groups built-in operations by purpose:

- **Arithmetic & Normalization** — element-wise mathematics and scaling.
- **Contours & Surfaces** — iso-points, iso-lines, and iso-surfaces.
- **Correlation & Statistics** — spatial correlation and intensity statistics.
- **Data & Axes** — layer extraction and axis reordering.
- **Filtering & Background** — smoothing, masking, and background removal.
- **Fourier & Wavevector** — FFT, reciprocal-space filtering, lock-in, and
  symmetry operations.
- **Geometry & Resampling** — cropping, interpolation, rotation, and tiling.
- **Lattice & Registration** — affine registration and lattice-distortion
  correction.
- **Simple Simulations** — lightweight synthetic image generators.
- **Spectroscopy & Profiles** — spectral maps, integration, and line or circle
  profiles.

Plugins may add further categories when their processes do not fit these
built-in groups.

## Configure a module menu

Use **Process → Configure Process Menu…** to expose additional registered
processes in a particular module:

1. Select the target module type.
2. Add compatible entries from the registry.
3. Reorder or remove user-added entries.
4. Save the configuration.

Developer-provided defaults are shown for context but cannot be removed in this
dialog. User selections are stored separately, so an application update does
not overwrite them.

## Simulations

Registered simulations appear in the **Simulate** menu. Unlike normal
processes, a simulation may generate data without an input dataset.
