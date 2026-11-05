# Planewave Synthesiser

The Planewave Synthesiser produces a two-dimensional real-space image from a
sum of plane waves. Use it to explore how wavevectors, amplitudes, and phases
affect spatial patterns or to create synthetic references for analysis.

```text
f(X, Y) = Σ_j A_j cos(2π (qx_j X + qy_j Y) / size - φ_j)
```

The sum runs over the wave components `j`. Each component has amplitude `A_j`,
wavevector components `qx_j` and `qy_j`, and phase `φ_j`. The square output
size sets the spatial grid.

## Create an image

1. In the Main Workbench, click the **+ New Module** button and choose
   **Simulation → Planewave Synthesiser**.
2. In the synthesiser's control panel, edit **Size (px)** for the square output.
3. Click **＋ Add wave** or **－ Remove wave** in that panel to change the components.
4. For each `Q` component, set `qx`, `qy`, amplitude `A`, and phase `φ`.
   The **A range** and **φ range** controls set the slider limits.
5. Adjust component values while observing the live image.
6. Click the **Save to workspace** button in the synthesiser's control panel.
   Open **View → Workspace** to see the new item.

## Continue through AngstromPro

1. In the Planewave Synthesiser's Workspace dock, single-click the generated
   item so it is highlighted, then click
   the **Send…** button below the Workspace list and select an open
   **Image Stack Viewer**. Open one first using Main Workbench's
   **+ New Module → Basic → Image Stack Viewer** if needed.
2. In the receiving viewer, open **View → Workspace** and double-click the
   received item to display it. Use the panel's **Layer** and **Palette**
   controls; right-click the image to pick points.
3. Add a compatible operation through **Process → Configure Process Menu…**,
   then run it from **Process → your configured submenu → operation**.
4. Inspect the returned workspace item or send it to another compatible module.

## Preferences

Open **File → Preferences…** from this module to configure:

- **Color map:** choose and order the image palette.
- **Scale:** set histogram sigma scaling, scale-button zoom, and canvas wheel
  sensitivity.
- **Canvas:** limit canvas size and configure the optional bias-value overlay.

Use **Apply** for the current synthesiser and **Save as default** for future
Planewave Synthesiser instances.
