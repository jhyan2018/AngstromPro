# Image-processing workflows

These procedures extend the basic tutorials to lattice correction and
registration of your own STM images. First practise
[opening a measurement](file-formats.md#tutorial-open-and-verify-a-measurement),
[inspecting the image and FFT](image-stack-viewer.md#tutorial-inspect-images-and-their-fourier-transforms),
and [running a process](processes.md#tutorial-configure-a-process-menu).

Each operation produces a new workspace item. Keep the original measurement
and save intermediate results so that the scientific effect of each step can
be assessed independently. The procedures follow the current process schemas;
a more ordered-looking image is not by itself evidence that a correction is
appropriate.

## Controls used in these workflows

Perform these steps in Image Stack Viewer. Open **View → Workspace** and
**View → Inspector**; if they share a dock, click their tabs to switch.
Single-click a Workspace row to select it for inspection or reference
assignment; double-click a row to activate it as Primary.
Right-click on an image to pick a point. To clear picked points, select entries
in that panel's **Picked Points** list and click its **Remove Point** button.

Every named process below must first be added through **Process → Configure
Process Menu…**. Launch it from **Process → your configured submenu →
process name**. Labels such as **Interpolation**, **Padding**, **Pixel ratio**,
**σ / a₀**, **Phase unwrap**, **Unwrap method**, and **Layer index** are fields
inside that process's dialog. Input selectors such as **3D Stack**, **Stack B**,
and **Displacement field** are in its **Inputs** section. Click **Run** at the
bottom of that dialog after checking the inputs, annotations, and parameters.

## Tutorial: correct a resolved atomic lattice

**Goal:** subtract a background, correct global lattice geometry, then estimate
and apply a local displacement field.

**Input:** real-valued, atomically resolved topography with two identifiable,
non-collinear Bragg peaks and known lattice symmetry. For the LF steps below,
use a square spatial grid: the current implementation constructs a square
coordinate mesh.

### 1. Prepare the topography

1. Load the topographic channel into Image Stack Viewer and verify its spatial
   axes and units. Use a one-layer topography for displacement-field estimation;
   **LF Displacement Field 2D** uses layer 0 even if another layer is displayed.
2. Run **Background Subtract 2D** using the
   [background tutorial](processes.md#tutorial-run-background-subtraction).
3. Double-click the resulting `_bg` item. Wait for its FFT to appear in
   **Reference Image**. Check both item names.
4. Use the FFT's **Type = Abs** and appropriate colour limits to identify
   lattice peaks. Do not choose the central zero-frequency peak.

### 2. Correct the global lattice geometry

1. Remove previous markers from Reference's **Picked Points** list with
   **Remove Point**.
2. Right-click exactly two independent Bragg peaks in Reference. Use peaks
   defining the known reciprocal-lattice basis: roughly a right angle for the
   square correction, or adjacent peaks roughly 60 degrees apart for the
   hexagonal correction. Opposite peaks are collinear and cannot define a basis.
3. Choose **Points → Set Bragg Peaks from Reference**. Expand the corresponding
   real-space workspace item and confirm that `bragg_peaks` is attached to it.
4. Add and run **Perfect Lattice Square 2D** or **Perfect Lattice Hexagonal 2D**
   from the configured Process menu, according to the known sample symmetry.
   Verify that the first input is the real-space topography, not its FFT.
5. Review **Interpolation** and **Padding**, then click **Run**.
6. Inspect the `_pl` result and its FFT. Check the lattice geometry, field of
   view, and interpolation-affected boundaries, and save the result.

**Checkpoint:** the selected reciprocal-lattice geometry should approach the
chosen symmetry. These operations impose that geometry; they should not be
used to claim that an unknown sample necessarily has square or hexagonal
symmetry.

### 3. Estimate the local displacement field

1. Check the spatial shape of the affine-corrected image. If it is not square,
   [crop a suitable square region](processes.md#tutorial-crop-a-region-for-further-analysis)
   and use that result as the next input.
2. Activate the chosen topography, wait for its FFT, and pick the two Bragg
   peaks again on this new FFT. Store them with **Points → Set Bragg Peaks from
   Reference**. Previous peak coordinates belong to the earlier grid.
3. Add and run **LF Displacement Field 2D**. Verify the real-space input and
   required `bragg_peaks` annotation.
4. Review **σ / a₀**, **Phase unwrap**, and **Unwrap method**. The built-in
   initial value of **σ / a₀** is 0.5; it is a starting value, not a universal
   setting for all measurements. Keep **Unwrap method = auto** for automatic
   backend selection, or select an available method deliberately.
5. Click **Run**, then inspect the resulting `_df` item. It has two layers:
   layer 0 is the X displacement and layer 1 is the Y displacement, not
   two energy slices.

**Checkpoint:** inspect the displacement field for discontinuities and
implausible spatial variation. Reassess the peaks, phase unwrapping, and window
scale if the estimate is unstable. Save the field together with its generating
topography.

### 4. Apply and assess the correction

1. Double-click the real-space image to correct in Workspace. Run **LF Correction 2D**.
2. Verify **Real-space 3D stack** as the first input and explicitly select the
   `_df` item in **Displacement field**. Do not leave the automatically staged
   FFT as that second input.
3. Set **Interpolation** and **Padding**, then click **Run**.
4. Inspect the new `_lf` image and its FFT. Compare against the input using
   [matched display settings](image-stack-viewer.md#tutorial-compare-raw-and-processed-images).
   Look for changes in peak shape and consistency of real-space features,
   as well as interpolation or boundary artifacts.
5. Save the input, displacement field, corrected result, and processing history.

**Expected result:** a corrected data item, with the input and displacement
field retained for inspection. Peak sharpening is a useful check but is not
guaranteed for every measurement.

A displacement field may be applied to another simultaneously acquired
channel only when it refers to the same spatial sampling, orientation, crop,
and preceding transformations. The program does not establish this scientific
correspondence for you. Do not apply a field obtained after cropping or affine
correction to an unrelated raw grid.

## Tutorial: register two measurements

**Goal:** align a source topography to a reference using three corresponding
landmarks, then assess the result.

**Input:** two real-valued topographies of the same region with three recognisable,
non-collinear corresponding features. For this first workflow, use matching
square pixel grids and matching spatial sampling, with **Pixel ratio = 1**.

### 1. Set source and reference

1. Load both measurements into one Image Stack Viewer workspace. Give them
   distinct aliases such as `source_topography` and `reference_topography`.
2. Double-click the source to put it in **Primary** and wait for automatic FFT
   generation.
3. Single-click the target reference item and click **Select Variable** in
   **Reference Image**. Confirm that the right panel shows the second real-space
   measurement, not an FFT.
4. Select corresponding layers. Open **File → Preferences… → Sync** and turn
   **Sync pick points** off before picking independent landmarks. **Sync FOV
   zoom** may help navigate matching fields of view.

### 2. Save three landmark pairs

1. Empty both **Picked Points** lists using **Remove Point**.
2. Right-click three landmarks on Primary, in a deliberate order: 0, 1, 2.
   Choose features spread across the image, not three points along one line.
3. Pick the corresponding landmarks on Reference in exactly the same order.
4. Choose **Points → Register → Set Src Points from Primary**, then
   **Points → Register → Set Ref Points from Reference**.
5. Expand the source workspace item and confirm that it has both
   `register_points` and `register_reference_points`.

Both annotations are stored on the source item. If a marker is moved, repeat
the corresponding **Set** command. The current process uses the first three
points, so additional markers do not provide a least-squares fit.

### 3. Run registration

1. Add **Register 2D** to the module's Process menu and run it.
2. Verify the source under **3D Stack** and check that both annotations are
   present.
3. Use **Pixel ratio = 1** for the matching-grid workflow. The parameter means
   reference pixels divided by source pixels; a different ratio must be based
   on the actual image sampling, not chosen to improve the appearance.
4. Review **Interpolation** and **Padding**, then click **Run**.
5. Double-click the `_rg` result. Wait for its automatic FFT, then reload the
   original target image into Reference with **Select Variable**.
6. Compare the landmarks and additional features not used for fitting.
   Registration applies to every source layer and returns the source's spatial
   shape; it does not automatically crop away padded regions.

### 4. Check agreement with cross-correlation

1. Add **Cross Correlation 2D** to the Process menu.
2. Activate the unregistered source as Primary, run the process, and choose
   the actual reference topography in **Stack B**. Set **Layer index** explicitly;
   this parameter does not automatically follow the displayed layer.
3. Record the correlation map, which normally has a `_xcorr` suffix.
4. Repeat with the registered source as Primary and the same reference,
   layer, and comparison region.
5. Compare the peak position and value. For matching shapes, zero lag lies
   at the centre of the correlation array. The current output retains the
   first input's spatial axes rather than constructing displacement axes,
   so its displayed coordinate labels must not be read directly as lag units.
   Inspect the array in the Inspector when numerical values are needed.
6. Exclude padding-affected regions from a quantitative comparison, using
   matching valid regions and documenting any cropping. Keep preprocessing
   consistent when comparing correlation values.
7. Save the registered result and the correlation results with their histories.

**Expected result:** corresponding landmarks and independent features agree
more closely, with a correlation peak nearer zero lag when alignment improves.
There is no universal target correlation value. Repeated lattice patterns can
produce several peaks, and flat or invalid data cannot provide a meaningful
alignment score.

**If the result is incorrect:** first check landmark order, collinearity,
source/reference assignment, and pixel sampling. Adjusting display contrast
does not change the fitted transformation or the correlation calculation.
