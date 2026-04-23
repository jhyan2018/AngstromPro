# -*- coding: utf-8 -*-
"""
Created on Sat Jan 24 20:34:04 2026

@author: jiahaoYan & Huiyu Zhao
"""
import numpy as np

from ..RawDataProcess.UdsDataProcess import UdsDataStru

def interp2d_bilinear(img: np.ndarray, x: float, y: float) -> float:
    """
    Bilinear interpolation of a 2D image at floating-point coordinate (x, y).

    Parameters
    ----------
    img : np.ndarray (H, W)
        Input image
    x, y : float
        Coordinates in image space (x = column, y = row)

    Returns
    -------
    float
        Interpolated intensity value
    """
    img = np.asarray(img)
    H, W = img.shape

    # Clamp coordinates to valid range
    x = np.clip(x, 0, W - 1)
    y = np.clip(y, 0, H - 1)

    x0 = int(np.floor(x))
    y0 = int(np.floor(y))
    x1 = min(x0 + 1, W - 1)
    y1 = min(y0 + 1, H - 1)

    dx = x - x0
    dy = y - y0

    I00 = img[y0, x0]
    I10 = img[y0, x1]
    I01 = img[y1, x0]
    I11 = img[y1, x1]

    val = (
        (1 - dx) * (1 - dy) * I00 +
        dx * (1 - dy) * I10 +
        (1 - dx) * dy * I01 +
        dx * dy * I11
    )

    return float(val)

def interp2d_average(img: np.ndarray, coords) -> float:
    """
    Compute the average interpolated intensity at multiple (x, y) coordinates.

    Parameters
    ----------
    img : np.ndarray (H, W)
        Input image
    coords : iterable of (x, y)
        List (or array) of floating-point coordinates

    Returns
    -------
    float
        Average interpolated intensity value
    """
    if len(coords) == 0:
        raise ValueError("coords must contain at least one (x, y) pair")

    vals = []
    for x, y in coords:
        val = interp2d_bilinear(img, x, y)
        vals.append(val)

    return float(np.mean(vals))

def lattice_coefficients(
    a1: tuple[float, float],
    a2: tuple[float, float],
    P: tuple[int, int],
    roi_x0: int,
    roi_y0: int,
) -> tuple[float, float]:
    """
    Solve P = m*a1 + n*a2 for (m, n).

    Coordinate conventions:
      - x = column, y = row
      - positive x: left -> right
      - positive y: up -> down
      - a1, a2 are in lattice/ROI space (float)
      - P is in Full FOV (int)
      - ROI and lattice space share the same origin

    Parameters
    ----------
    a1, a2 : (x, y)
        Lattice vectors (floats)
    P : (x, y)
        Point in Full FOV (integers)
    roi_x0, roi_y0 : int
        ROI origin in Full FOV

    Returns
    -------
    (m, n) : floats
        Lattice coordinates such that P = m*a1 + n*a2
    """
    a1x, a1y = a1
    a2x, a2y = a2
    Px, Py = P

    # Convert Full FOV -> ROI / lattice coordinates
    Px_roi = Px - roi_x0
    Py_roi = Py - roi_y0

    # Solve linear system:
    # [a1x a2x] [m] = [Px_roi]
    # [a1y a2y] [n]   [Py_roi]
    A = np.array([[a1x, a2x],
                  [a1y, a2y]], dtype=np.float64)
    b = np.array([Px_roi, Py_roi], dtype=np.float64)

    if abs(np.linalg.det(A)) < 1e-12:
        raise ValueError("Lattice vectors a1 and a2 are linearly dependent")

    m, n = np.linalg.solve(A, b)
    return float(m), float(n)

def lattice_equiv_points_in_roi(
    a1: tuple[float, float],
    a2: tuple[float, float],
    m: float,
    n: float,
    roi_shape: tuple[int, int],
) -> np.ndarray:
    """
    Given lattice vectors a1, a2 and the lattice coefficients (m, n) of a point P,
    compute the fractional part (m_frac, n_frac) -> P0 inside the first unit cell,
    then generate all equivalent points:
        P_equi = (M + m_frac)*a1 + (N + n_frac)*a2
    for integer M, N such that P_equi lies inside the ROI.

    Coordinate convention: x=col, y=row; ROI coordinates satisfy:
        0 <= x < W, 0 <= y < H

    Parameters
    ----------
    a1, a2 : (x, y) floats
        Lattice vectors in ROI coordinate system.
    m, n : float
        Lattice coefficients of some point P, i.e. P = m*a1 + n*a2.
    roi_shape : (H, W)
        ROI size in pixels.

    Returns
    -------
    pts : np.ndarray of shape (K, 2), dtype float64
        All equivalent points (x, y) within ROI, including P0.
    """
    H, W = map(int, roi_shape)
    if H <= 0 or W <= 0:
        raise ValueError("roi_shape must be positive (H, W)")

    a1x, a1y = a1
    a2x, a2y = a2

    A = np.array([[a1x, a2x],
                  [a1y, a2y]], dtype=np.float64)

    det = float(np.linalg.det(A))
    if abs(det) < 1e-12:
        raise ValueError("a1 and a2 are linearly dependent (cannot define unit cell)")

    Ainv = np.linalg.inv(A)

    # fractional parts in [0, 1)
    m_frac = float(m - np.floor(m))
    n_frac = float(n - np.floor(n))


    # --- Find candidate integer ranges for M,N by mapping ROI corners into (u,v) coefficient space ---
    # ROI corners in (x,y). Use inclusive-ish corners to be safe.
    corners = np.array([
        [0.0, 0.0],
        [W - 1.0, 0.0],
        [0.0, H - 1.0],
        [W - 1.0, H - 1.0],
    ], dtype=np.float64)

    # Solve [u,v]^T = A^{-1} [x,y]^T for each corner
    # corners_uv shape (4,2)
    corners_uv = (Ainv @ corners.T).T
    umin, vmin = corners_uv.min(axis=0)
    umax, vmax = corners_uv.max(axis=0)

    # u = M + m_frac, v = N + n_frac
    # so M = u - m_frac, N = v - n_frac
    Mmin = int(np.floor(umin - m_frac)) - 1
    Mmax = int(np.ceil(umax - m_frac)) + 1
    Nmin = int(np.floor(vmin - n_frac)) - 1
    Nmax = int(np.ceil(vmax - n_frac)) + 1

    pts_list = []
    for M in range(Mmin, Mmax + 1):
        for N in range(Nmin, Nmax + 1):
            u = M + m_frac
            v = N + n_frac
            x = u * a1x + v * a2x
            y = u * a1y + v * a2y
            if (0.0 <= x < W) and (0.0 <= y < H):
                pts_list.append([x, y])
                
    if not pts_list:
        # Shouldn't happen often, but return empty array if ROI has no equivalent points
        return np.zeros((0, 2), dtype=np.float64)
    #print(pts_list)
    pts = np.array(pts_list, dtype=np.float64)

    # Optional: de-duplicate numerically (can happen near boundaries)
    # Round to a tight grid then unique.
    key = np.round(pts, decimals=4)
    _, idx = np.unique(key, axis=0, return_index=True)
    pts = pts[np.sort(idx)]
    

    return pts

def vector_from_length_angle(length: float, degree: float) -> tuple[float, float]:
    """
    Convert (length, angle) to (x, y) vector components.

    Coordinate convention:
      - x: column direction (left -> right, positive)
      - y: row direction (top -> bottom, positive)
      - degree in [0, 360)
      - 0 deg: +x direction
      - angle increases clockwise

    Parameters
    ----------
    length : float
        Vector length
    degree : float
        Angle in degrees

    Returns
    -------
    (x, y) : floats
        Vector components
    """
    theta = np.deg2rad(degree)
    x = length * np.cos(theta)
    y = length * np.sin(theta)
    return float(x), float(y)

def extendRegion2D(img: np.ndarray, a1, a2, roi) -> np.ndarray:
    """
    Construct a NEW image with the SAME shape as `img`.

    For every integer pixel P(x,y) in the full image:
      1) compute (m,n) such that (P - ROI_origin) = m*a1 + n*a2
      2) take fractional parts (m_frac, n_frac) -> get all lattice-equivalent points
         inside the ROI: (M+m_frac)*a1 + (N+n_frac)*a2 that fall within ROI
      3) sample ROI image at those float points (bilinear interpolation) and average
      4) assign the averaged value to output[y,x]

    Inputs
    ------
    img : 2D numpy array (H, W)   (Full FOV)
    a1, a2 : (length, degree)
        Lattice vectors given as (float length, float degree),
        converted internally by vector_from_length_angle().
    roi : (roi_x0, roi_y0, size) or (roi_x0, roi_y0, roi_H, roi_W)
        ROI top-left origin in Full FOV and ROI size.
        If 3 items: square ROI (size x size). If 4 items: roi_H x roi_W.

    Returns
    -------
    out : 2D numpy array (H, W), float64
    """
    img = np.asarray(img)
    if img.ndim != 2:
        raise ValueError(f"img must be 2D, got shape {img.shape}")

    H, W = img.shape

    # Parse ROI
    if len(roi) == 3:
        roi_x0, roi_y0, roi_size = roi
        roi_H = int(roi_size)
        roi_W = int(roi_size)
    elif len(roi) == 4:
        roi_x0, roi_y0, roi_H, roi_W = roi
        roi_H = int(roi_H)
        roi_W = int(roi_W)
    else:
        raise ValueError("roi must be (roi_x0, roi_y0, size) or (roi_x0, roi_y0, roi_H, roi_W)")

    roi_x0 = int(roi_x0)
    roi_y0 = int(roi_y0)
    if roi_H <= 0 or roi_W <= 0:
        raise ValueError("ROI size must be positive")

    # ROI bounds in full image (clipped)
    y1 = max(0, roi_y0)
    x1 = max(0, roi_x0)
    y2 = min(H, roi_y0 + roi_H)
    x2 = min(W, roi_x0 + roi_W)
    if y2 <= y1 or x2 <= x1:
        raise ValueError("ROI is outside the image bounds or empty after clipping")

    roi_img = img[y1:y2, x1:x2]
    H_roi, W_roi = roi_img.shape  # actual clipped ROI shape

    # Convert (length, degree) -> (x, y) vectors (ROI coordinate system)
    a1_vec = vector_from_length_angle(float(a1[0]), float(a1[1]))
    a2_vec = vector_from_length_angle(float(a2[0]), float(a2[1]))

    out = np.empty((H, W), dtype=np.float64)

    # Iterate ALL pixels in full image
    for y_full in range(H):
        print(y_full/H)
        for x_full in range(W):
            # Compute (m,n) for this pixel relative to ROI origin (x1,y1)
            m, n = lattice_coefficients(
                a1=a1_vec,
                a2=a2_vec,
                P=(x_full, y_full),
                roi_x0=x1,
                roi_y0=y1,
            )

            # All equivalent points inside ROI (ROI coordinate system)
            pts = lattice_equiv_points_in_roi(
                a1=a1_vec,
                a2=a2_vec,
                m=m,
                n=n,
                roi_shape=(H_roi, W_roi),
            )

            # Average intensity sampled from ROI image at those points
            out[y_full, x_full] = interp2d_average(roi_img, pts)

    return out


