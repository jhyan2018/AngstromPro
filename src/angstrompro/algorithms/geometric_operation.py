# -*- coding: utf-8 -*-
"""
Geometric transformation utilities.

Classes
-------
AffineTransform
    Builds and applies a 3×3 affine matrix to a 2-D image via inverse mapping
    and pixel interpolation.  Supports translate, scale, shear, rotate, and
    fitting from three point-pair correspondences.

Functions
---------
rotate2d(data3d, theta_deg)
    Rotate every layer of a 3-D stack by ``theta_deg`` degrees (counter-clockwise).
"""

from __future__ import annotations

import numpy as np

from .pixel_interpolation import PixelInterpolation


class AffineTransform:
    """3×3 affine transformation with inverse-mapping interpolation.

    The matrix ``A`` maps source coordinates to target coordinates:
        [tgt_x, tgt_y, 1]^T = A @ [src_x, src_y, 1]^T

    Transformations are composed left-to-right (each new operation
    pre-multiplies the current matrix).
    """

    def __init__(self) -> None:
        self.A = np.eye(3, dtype=np.float64)
        self.src_X_float = 0
        self.src_Y_float = 0
        self.tgt_x_min = 0.0
        self.tgt_x_max = 0.0
        self.tgt_y_min = 0.0
        self.tgt_y_max = 0.0

    # ------------------------------------------------------------------
    # Matrix builders
    # ------------------------------------------------------------------

    def setTranslateOfAffineMatrix(self, dx: float, dy: float) -> None:
        """Apply a translation (dx=col, dy=row)."""
        T = np.array([[1., 0., dx],
                      [0., 1., dy],
                      [0., 0., 1.]])
        self.A = T @ self.A

    def setScaleOfAffineMatrix(self, sx: float, sy: float) -> None:
        """Apply a scale (sx=col, sy=row)."""
        S = np.array([[sx,  0., 0.],
                      [0.,  sy, 0.],
                      [0.,  0., 1.]])
        self.A = S @ self.A

    def setShearOfAffineMatrix(self, bx: float, by: float) -> None:
        """Apply a shear (bx=col-axis shear, by=row-axis shear)."""
        H = np.array([[1.,  bx, 0.],
                      [by,  1., 0.],
                      [0.,  0., 1.]])
        self.A = H @ self.A

    def setRotateOfAffineMatrix(self, angle: float) -> None:
        """Apply a rotation by ``angle`` radians (counter-clockwise)."""
        c = np.cos(angle)
        s = np.sin(angle)
        R = np.array([[ c, -s, 0.],
                      [ s,  c, 0.],
                      [0.,  0., 1.]])
        self.A = R @ self.A

    def setAffineMatrixFrom3PairsRpoints(self, rPoints) -> None:
        """Fit affine matrix from 6 (src, tgt) point pairs.

        ``rPoints`` : sequence of 6 (x, y) pairs —
            [src0, src1, src2, tgt0, tgt1, tgt2]
        """
        (sx0, sy0), (sx1, sy1), (sx2, sy2) = rPoints[0], rPoints[1], rPoints[2]
        (tx0, ty0), (tx1, ty1), (tx2, ty2) = rPoints[3], rPoints[4], rPoints[5]

        d = 1.0 / (sx0 * (sy2 - sy1) + sx1 * (sy0 - sy2) + sx2 * (sy1 - sy0))

        self.A[0, 0] = d * (sy0 * (tx1 - tx2) + sy1 * (tx2 - tx0) + sy2 * (tx0 - tx1))
        self.A[0, 1] = d * (sx0 * (tx2 - tx1) + sx1 * (tx0 - tx2) + sx2 * (tx1 - tx0))
        self.A[0, 2] = d * (sx0 * (sy2 * tx1 - sy1 * tx2) +
                            sx1 * (sy0 * tx2 - sy2 * tx0) +
                            sx2 * (sy1 * tx0 - sy0 * tx1))
        self.A[1, 0] = d * (sy0 * (ty1 - ty2) + sy1 * (ty2 - ty0) + sy2 * (ty0 - ty1))
        self.A[1, 1] = d * (sx0 * (ty2 - ty1) + sx1 * (ty0 - ty2) + sx2 * (ty1 - ty0))
        self.A[1, 2] = d * (sx0 * (sy2 * ty1 - sy1 * ty2) +
                            sx1 * (sy0 * ty2 - sy2 * ty0) +
                            sx2 * (sy1 * ty0 - sy0 * ty1))

    # ------------------------------------------------------------------
    # Coordinate mapping
    # ------------------------------------------------------------------

    def srcMappedPoints(self, data2D_row: int, data2D_col: int) -> None:
        """Pre-compute inverse-mapped source coordinates for a target grid.

        Must be called before :meth:`affineMapping` or
        :meth:`affineMappingForRegister`.

        Parameters
        ----------
        data2D_row, data2D_col : int
            Shape of the source image (rows, cols).
        """
        src_X, src_Y = np.meshgrid(np.arange(data2D_col), np.arange(data2D_row))

        tgt_X_f = self.A[0, 0] * src_X + self.A[0, 1] * src_Y + self.A[0, 2]
        tgt_Y_f = self.A[1, 0] * src_X + self.A[1, 1] * src_Y + self.A[1, 2]

        self.tgt_x_min = np.floor(tgt_X_f.min())
        self.tgt_x_max = np.ceil(tgt_X_f.max())
        self.tgt_y_min = np.floor(tgt_Y_f.min())
        self.tgt_y_max = np.ceil(tgt_Y_f.max())

        tgt_X, tgt_Y = np.meshgrid(
            np.arange(self.tgt_x_min, self.tgt_x_max + 1),
            np.arange(self.tgt_y_min, self.tgt_y_max + 1),
        )

        A_inv = np.linalg.inv(self.A)
        self.src_X_float = A_inv[0, 0] * tgt_X + A_inv[0, 1] * tgt_Y + A_inv[0, 2]
        self.src_Y_float = A_inv[1, 0] * tgt_X + A_inv[1, 1] * tgt_Y + A_inv[1, 2]

    # ------------------------------------------------------------------
    # Mapping
    # ------------------------------------------------------------------

    def affineMapping(self, data2D: np.ndarray,
                      interpolate_method: str = 'bilinear',
                      pad_method: str = 'constant') -> np.ndarray:
        """Apply the affine transform; output may be larger than input."""
        px_itp = PixelInterpolation(
            data2D, self.src_X_float, self.src_Y_float,
            interpolate_method, pad_method,
        )
        return px_itp.dataMapping()

    def affineMappingForRegister(self, data2D: np.ndarray,
                                  interpolate_method: str = 'bilinear',
                                  pad_method: str = 'constant') -> np.ndarray:
        """Apply the affine transform and crop result back to the original shape."""
        mapped = self.affineMapping(data2D, interpolate_method, pad_method)

        H, W = data2D.shape[-2], data2D.shape[-1]

        if self.tgt_y_min <= 0:
            y_start  = int(0 - self.tgt_y_min)
            y_start_p = 0
            y_end    = int(min(H, self.tgt_y_max) - self.tgt_y_min)
            y_end_p  = int(min(H, self.tgt_y_max))
        else:
            y_start  = 0
            y_start_p = int(self.tgt_y_min)
            y_end    = int(min(H, self.tgt_y_max) - self.tgt_y_min)
            y_end_p  = int(min(H, self.tgt_y_max))

        if self.tgt_x_min <= 0:
            x_start  = int(0 - self.tgt_x_min)
            x_start_p = 0
            x_end    = int(min(W, self.tgt_x_max) - self.tgt_x_min)
            x_end_p  = int(min(W, self.tgt_x_max))
        else:
            x_start  = 0
            x_start_p = int(self.tgt_x_min)
            x_end    = int(min(W, self.tgt_x_max) - self.tgt_x_min)
            x_end_p  = int(min(W, self.tgt_x_max))

        data = np.zeros_like(data2D)
        data[y_start_p:y_end_p, x_start_p:x_end_p] = mapped[y_start:y_end, x_start:x_end]
        return data


# ---------------------------------------------------------------------------
# Convenience function
# ---------------------------------------------------------------------------

def rotate2d(data3d: np.ndarray, theta_deg: float,
             interpolate_method: str = 'bilinear',
             pad_method: str = 'constant') -> np.ndarray:
    """Rotate every layer of a 3-D stack counter-clockwise by ``theta_deg`` degrees.

    Parameters
    ----------
    data3d : ndarray (L, H, W)
    theta_deg : float
        Rotation angle in degrees.
    interpolate_method : str
        Pixel interpolation method ('bilinear').
    pad_method : str
        Edge padding mode ('constant', 'reflect', 'edge', …).

    Returns
    -------
    ndarray
        Rotated stack; may have different spatial dimensions than input.
    """
    affine = AffineTransform()
    affine.setRotateOfAffineMatrix(-np.deg2rad(theta_deg))
    affine.srcMappedPoints(data3d.shape[-2], data3d.shape[-1])

    n_layers = data3d.shape[0]
    out_h    = affine.src_X_float.shape[-2]
    out_w    = affine.src_X_float.shape[-1]
    out      = np.zeros((n_layers, out_h, out_w), dtype=data3d.dtype)

    for i in range(n_layers):
        out[i] = affine.affineMapping(data3d[i], interpolate_method, pad_method)

    return out
