# File I/O

## Built-in formats

| Format | Read | Write | Purpose |
| --- | :---: | :---: | --- |
| `.uds` | Yes | Yes | Native HDF5 scientific data |
| `.scplot` | Yes | Yes | Curve Stack Viewer scene |
| `.npy` | Yes | Yes | NumPy array |
| `.sxm` | Yes | No | Nanonis map |
| `.3ds` | Yes | No | Nanonis grid spectroscopy |
| `.dat` | Yes | No | Nanonis point spectroscopy |
| `.1fl` | Yes | No | LF dI/dV map |
| `.tfr` | Yes | No | LF topography map |
| `.mat` | Yes | No | MATLAB data |
| `.txt` | Yes | No | Whitespace-delimited numeric data |

Open **Help → Supported Formats…** for the runtime registry. This view also
includes formats supplied by installed plugins.

## Native data

Current `.uds` files use HDF5 and retain AngstromPro data, axes, metadata,
annotations, and processing history. Legacy binary `.uds` files are imported
read-only; save the imported result as `.uds` to upgrade it to the current
format.

`.scplot` is also HDF5-based and stores plot-scene data. Style-only `.scet`
templates are managed by the Curve Stack Viewer and are not general workspace
data files.

## Channel mappings for multichannel formats

Some instrument formats contain multiple named channels. For those formats,
channel mappings associate varying instrument labels with stable AngstromPro
channel roles and control which channels load by default. Single-channel file
formats do not require channel mapping.

Configure mappings in Preferences. The same mapping is used by normal file
opening and Data Browser thumbnail rendering. If a browser card reports that a
channel was not found, add the actual instrument channel name as an alias or
select a different default channel.

## Saving and exporting

Saving writes structured data through a registered format handler. Exporting
creates a presentation artifact such as an image, video, or figure. Use saving
when the result must be reloaded and processed later; use exporting for
publication or presentation.
