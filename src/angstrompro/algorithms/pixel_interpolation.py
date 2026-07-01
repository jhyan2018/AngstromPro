# -*- coding: utf-8 -*-
"""
Pixel interpolation utilities.

Classes
-------
PixelInterpolation
    Inverse-mapping interpolation for affine-transformed images.
    Pads the source image to handle out-of-bounds mapped coordinates,
    then samples each target pixel via vectorised bilinear interpolation
    (fully NumPy — releases the GIL during heavy array work).

RasterPixelInterpolation
    Bilinear interpolation along a 1-D raster of float coordinates
    (used for line profiles and similar point-set sampling).
"""

from __future__ import annotations

import numpy as np


class PixelInterpolation:
    """Inverse-map interpolation of a 2-D image at pre-computed float coordinates.

    Parameters
    ----------
    src_data2D : ndarray (H, W)
        Source image.
    src_X_f : ndarray
        Float column coordinates in source space for each target pixel.
    src_Y_f : ndarray
        Float row coordinates in source space for each target pixel.
    interpolate_method : str
        ``'bilinear'`` (only supported method currently).
    pad_method : str
        NumPy ``np.pad`` mode used to extend the source image
        (e.g. ``'constant'``, ``'reflect'``).
    """

    def __init__(self, src_data2D: np.ndarray, src_X_f: np.ndarray,
                 src_Y_f: np.ndarray,
                 interpolate_method: str = 'bilinear',
                 pad_method: str = 'constant') -> None:
        self.src_data           = src_data2D
        self.src_X_f            = src_X_f
        self.src_Y_f            = src_Y_f
        self.interpolate_method = interpolate_method
        self.pad_method         = pad_method
        self.src_data_padded    = None
        self.offset_x           = 0
        self.offset_y           = 0
        self._pad()

    def _pad(self) -> None:
        data_size_max = max(self.src_data.shape[-1], self.src_data.shape[-2])
        padding_size  = int((data_size_max - data_size_max % 2) / 2)

        src_X_f_max = np.ceil(np.amax(self.src_X_f))
        src_X_f_min = np.floor(np.amin(self.src_X_f))
        src_Y_f_max = np.ceil(np.amax(self.src_Y_f))
        src_Y_f_min = np.floor(np.amin(self.src_Y_f))

        border = int(max(
            0 - src_X_f_min,
            0 - src_Y_f_min,
            src_X_f_max - self.src_data.shape[-1] + 1,
            src_Y_f_max - self.src_data.shape[-2] + 1,
            0,
        ))
        padding_size += border

        self.offset_x        = padding_size
        self.offset_y        = padding_size
        self.src_data_padded = np.pad(
            self.src_data, padding_size, self.pad_method, constant_values=0
        )

    def dataMapping(self) -> np.ndarray:
        if self.interpolate_method == 'bilinear':
            return self._bilinear_vectorised()
        raise NotImplementedError(
            f"Interpolation method '{self.interpolate_method}' is not implemented.")

    def _bilinear_vectorised(self) -> np.ndarray:
        # Shift coordinates into padded-image space (all NumPy — releases GIL)
        x_f = self.src_X_f + self.offset_x   # shape (H_tgt, W_tgt)
        y_f = self.src_Y_f + self.offset_y

        ux = np.floor(x_f).astype(np.intp)
        vy = np.floor(y_f).astype(np.intp)
        ax = x_f - ux   # fractional column offset in [0, 1)
        by = y_f - vy   # fractional row    offset in [0, 1)

        # Clamp so ux+1 / vy+1 never exceed padded image bounds
        pH, pW = self.src_data_padded.shape[-2], self.src_data_padded.shape[-1]
        ux = np.clip(ux, 0, pW - 2)
        vy = np.clip(vy, 0, pH - 2)

        p = self.src_data_padded
        return (
            (ax - 1) * (by - 1) * p[vy,     ux    ] +
            ax       * (1 - by) * p[vy,     ux + 1] +
            (1 - ax) * by       * p[vy + 1, ux    ] +
            ax       * by       * p[vy + 1, ux + 1]
        )


class RasterPixelInterpolation:
    """Bilinear interpolation of a 2-D image along a 1-D raster of float coords.

    Parameters
    ----------
    src_data2D : ndarray (H, W)
        Source image.
    src_X_f : array-like of float
        Column coordinates to sample.
    src_Y_f : array-like of float
        Row coordinates to sample.
    interpolate_method : str
        ``'bilinear'`` (only supported method currently).
    """

    def __init__(self, src_data2D: np.ndarray, src_X_f, src_Y_f,
                 interpolate_method: str = 'bilinear') -> None:
        self.src_data           = src_data2D
        self.src_X_f            = np.asarray(src_X_f, dtype=np.float64)
        self.src_Y_f            = np.asarray(src_Y_f, dtype=np.float64)
        self.interpolate_method = interpolate_method

    def interpolate(self, modulus: bool = False) -> np.ndarray:
        if self.interpolate_method == 'bilinear':
            return self._bilinear_vectorised(modulus)
        raise NotImplementedError(
            f"Interpolation method '{self.interpolate_method}' is not implemented.")

    def _bilinear_vectorised(self, modulus: bool) -> np.ndarray:
        src = np.abs(self.src_data) if modulus else self.src_data

        ux = np.floor(self.src_X_f).astype(np.intp)
        vy = np.floor(self.src_Y_f).astype(np.intp)
        ax = self.src_X_f - ux
        by = self.src_Y_f - vy

        H, W = src.shape[-2], src.shape[-1]
        ux = np.clip(ux, 0, W - 2)
        vy = np.clip(vy, 0, H - 2)

        result = (
            (ax - 1) * (by - 1) * src[vy,     ux    ] +
            ax       * (1 - by) * src[vy,     ux + 1] +
            (1 - ax) * by       * src[vy + 1, ux    ] +
            ax       * by       * src[vy + 1, ux + 1]
        )
        return result.reshape(1, -1)
