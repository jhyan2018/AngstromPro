"""Synthetic simulation and analysis process for the example plugin."""

from __future__ import annotations

from copy import deepcopy

import numpy as np

from angstrompro.core.data.uds_data import Axis, AxisType, UdsDataStru
from angstrompro.core.processes import (
    InputSpec,
    OutputSpec,
    ParameterSpec,
    ProcessSchema,
    register_process,
    register_simulation,
)


_IMAGE_OUTPUT = [
    OutputSpec(
        type_id="uds",
        ndim=3,
        label="Image Stack",
        description="A single-layer synthetic image stack.",
    )
]


@register_simulation(
    name="angstrompro_example.gaussian_stack",
    label="Gaussian Demo Stack",
    category="Examples",
    description="Generate a single-layer Gaussian image for plugin testing.",
    schema=ProcessSchema(
        outputs=_IMAGE_OUTPUT,
        params=[
            ParameterSpec(
                "size", int, 96, min=16, max=512,
                description="Image width and height in pixels.",
            ),
            ParameterSpec(
                "sigma", float, 14.0, min=0.1,
                description="Gaussian standard deviation in pixels.",
            ),
        ],
    ),
)
def gaussian_stack(inputs: dict, params: dict, *, annotations=None) -> UdsDataStru:
    """Return a one-layer Gaussian image stack."""
    size = int(params["size"])
    sigma = float(params["sigma"])
    coords = np.arange(size, dtype=np.float64) - (size - 1) / 2
    yy, xx = np.meshgrid(coords, coords, indexing="ij")
    image = np.exp(-(xx * xx + yy * yy) / (2 * sigma * sigma))

    return UdsDataStru(
        name="example_gaussian",
        data=image[np.newaxis, :, :],
        axes=[
            Axis(np.array([0.0]), "Layer", "", AxisType.INDEX),
            Axis(np.arange(size, dtype=np.float64), "Y", "px", AxisType.SPATIAL_Y),
            Axis(np.arange(size, dtype=np.float64), "X", "px", AxisType.SPATIAL_X),
        ],
        info={"_source_format": "angstrompro_example.simulation"},
    )


@register_process(
    name="angstrompro_example.scale_2D",
    label="Scale Image Stack",
    category="Examples",
    description="Multiply every image-stack value by a scalar factor.",
    schema=ProcessSchema(
        inputs=[InputSpec("data", "uds", ndim=3, label="Image Stack")],
        outputs=_IMAGE_OUTPUT,
        params=[
            ParameterSpec(
                "factor", float, 2.0,
                description="Scalar multiplier applied to every value.",
            )
        ],
    ),
)
def scale_image_stack(
    inputs: dict,
    params: dict,
    *,
    annotations=None,
) -> UdsDataStru:
    """Return a scaled copy while preserving axes and metadata."""
    source = inputs["data"]
    result = deepcopy(source)
    result.name = f"{source.name}_scaled"
    result.data = np.asarray(source.data) * float(params["factor"])
    result.info = dict(source.info)
    result.info["example_scale_factor"] = float(params["factor"])
    return result
