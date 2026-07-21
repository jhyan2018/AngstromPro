# Planewave Synthesiser

The Planewave Synthesiser produces a two-dimensional real-space image from a
sum of plane waves:

$$
f(x,y) = \sum_j A_j \cos\!\left(
2\pi\frac{q_{x_j}X + q_{y_j}Y}{\mathrm{size}} - \varphi_j
\right)
$$

## Create an image

1. Open the module from the Modules menu.
2. Set the output width and height.
3. Add or remove wave components.
4. For each component, set `qx`, `qy`, amplitude, and phase.
5. Adjust component values while observing the live image.
6. Save the result to the module workspace.

The generated workspace item can be sent to the Image Stack Viewer or used as
input to compatible processes. This makes the module useful for testing
analysis workflows as well as visualising plane-wave interference.
