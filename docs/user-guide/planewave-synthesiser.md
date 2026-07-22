# Planewave Synthesiser

The Planewave Synthesiser produces a two-dimensional real-space image from a
sum of plane waves. It is the recommended first analysis module when you want
to explore AngstromPro but do not have measurement data available:

$$
f(x,y) = \sum_j A_j \cos\!\left(
2\pi\frac{q_{x_j}X + q_{y_j}Y}{\mathrm{size}} - \varphi_j
\right)
$$

## Create an image

1. In the Main Workbench, choose **+ New Module → Planewave Synthesiser**.
2. Set the square output size.
3. Add or remove wave components.
4. For each `Q` component, set `qx`, `qy`, amplitude `A`, and phase `φ`.
   The **A range** and **φ range** controls set the slider limits.
5. Adjust component values while observing the live image.
6. Choose **Save to workspace**.

## Continue through AngstromPro

1. Select the generated item in the Planewave Synthesiser's Workspace dock.
2. Single-click the new workspace item so it is highlighted, then choose
   **Send…** and select an open **Image Stack Viewer**.
3. Explore the image display, layer controls, colormaps, and point picking.
4. Run a compatible operation from the viewer's **Process** menu.
5. Inspect the returned workspace item or send it to another compatible module.

This synthetic-data route teaches the same workspace and processing workflow
used for experimental files, without requiring AngstromPro to distribute
private or instrument-specific example datasets.
