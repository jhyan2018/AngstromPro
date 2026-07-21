# -*- coding: utf-8 -*-
"""
Element-wise math processes for AngstromPro.

Registered processes
--------------------
    math.two_stacks
        Element-wise arithmetic between two 3-D stacks (+, -, *, /).
        Name suffix: _mat

    math.multiply_const
        data × constant.  Name suffix: _mat

    math.divide_by_const
        data / constant.  Name suffix: _mat

    math.const_divide
        constant / data.  Name suffix: _mat

    math.complex_abs
        |data| (modulus of each element).  Name suffix: _abs
"""

from __future__ import annotations

import copy

import numpy as np

from angstrompro.core.data.uds_data import UdsDataStru
from angstrompro.core.processes import (
    InputSpec,
    OutputSpec,
    ParameterSpec,
    ProcessSchema,
    register_process,
)

_OUT_3D = [OutputSpec(type_id="uds", ndim=3, label="Image Stack", description="ndim=3 UDS (layers × rows × cols).")]

# ---------------------------------------------------------------------------
# math.two_stacks
# ---------------------------------------------------------------------------

@register_process(
    name        = "math.two_stacks_2d",
    label       = "Two Stacks Math 2D",
    category    = "Arithmetic & Normalization",
    schema      = ProcessSchema(
        outputs=_OUT_3D,
        inputs=[
            InputSpec(
                name        = "data_a",
                type_id     = "uds",
                label       = "Stack A",
                description = "Primary 3-D stack (left-hand operand).",
                ndim        = 3,
            ),
            InputSpec(
                name        = "data_b",
                type_id     = "uds",
                label       = "Stack B",
                description = "Secondary 3-D stack (right-hand operand). Must match shape of A.",
                ndim        = 3,
            ),
        ],
        params=[
            ParameterSpec(
                name        = "operator",
                type        = str,
                default     = "+",
                label       = "Operator",
                description = "Element-wise arithmetic operator applied as A op B.",
                choices     = ["+", "-", "*", "/"],
            ),
        ],
    ),
    description = "Element-wise arithmetic between two 3-D stacks: result = A op B.",
)
def two_stacks(inputs: dict, params: dict, *, annotations=None) -> UdsDataStru:
    a   = inputs["data_a"]
    b   = inputs["data_b"]
    op  = params["operator"]

    if op == "+":
        out = a.data + b.data
    elif op == "-":
        out = a.data - b.data
    elif op == "*":
        out = a.data * b.data
    elif op == "/":
        out = a.data / b.data
    else:
        raise ValueError(f"math.two_stacks_2d: unrecognised operator {op!r}.")

    return UdsDataStru(
        name         = a.name + "_mat",
        data         = out,
        axes         = [copy.deepcopy(ax) for ax in a.axes],
        info         = dict(a.info),
        proc_history = [copy.deepcopy(r) for r in a.proc_history],
    )


# ---------------------------------------------------------------------------
# math.multiply_const
# ---------------------------------------------------------------------------

@register_process(
    name        = "math.multiply_const_2d",
    label       = "Multiply by Constant 2D",
    category    = "Arithmetic & Normalization",
    schema      = ProcessSchema(
        outputs=_OUT_3D,
        inputs=[
            InputSpec(
                name    = "data",
                type_id = "uds",
                label   = "3D Stack",
                ndim    = 3,
            ),
        ],
        params=[
            ParameterSpec(
                name        = "const",
                type        = float,
                default     = 1.0,
                label       = "Constant",
                description = "Scalar multiplied into every element: result = data × constant.",
            ),
        ],
    ),
    description = "Multiply every element of a 3-D stack by a scalar constant.",
)
def multiply_const(inputs: dict, params: dict, *, annotations=None) -> UdsDataStru:
    src = inputs["data"]
    out = src.data * params["const"]
    return UdsDataStru(
        name         = src.name + "_mat",
        data         = out,
        axes         = [copy.deepcopy(ax) for ax in src.axes],
        info         = dict(src.info),
        proc_history = [copy.deepcopy(r) for r in src.proc_history],
    )


# ---------------------------------------------------------------------------
# math.divide_by_const  (data / const)
# ---------------------------------------------------------------------------

@register_process(
    name        = "math.divide_by_const_2d",
    label       = "Divide by Constant 2D",
    category    = "Arithmetic & Normalization",
    schema      = ProcessSchema(
        outputs=_OUT_3D,
        inputs=[
            InputSpec(
                name    = "data",
                type_id = "uds",
                label   = "3D Stack",
                ndim    = 3,
            ),
        ],
        params=[
            ParameterSpec(
                name        = "const",
                type        = float,
                default     = 1.0,
                label       = "Constant",
                description = "Scalar divisor: result = data / constant.",
            ),
        ],
    ),
    description = "Divide every element of a 3-D stack by a scalar constant.",
)
def divide_by_const(inputs: dict, params: dict, *, annotations=None) -> UdsDataStru:
    src = inputs["data"]
    out = src.data / params["const"]
    return UdsDataStru(
        name         = src.name + "_mat",
        data         = out,
        axes         = [copy.deepcopy(ax) for ax in src.axes],
        info         = dict(src.info),
        proc_history = [copy.deepcopy(r) for r in src.proc_history],
    )


# ---------------------------------------------------------------------------
# math.const_divide  (const / data)
# ---------------------------------------------------------------------------

@register_process(
    name        = "math.const_divide_2d",
    label       = "Constant Divide by Stack 2D",
    category    = "Arithmetic & Normalization",
    schema      = ProcessSchema(
        outputs=_OUT_3D,
        inputs=[
            InputSpec(
                name    = "data",
                type_id = "uds",
                label   = "3D Stack",
                ndim    = 3,
            ),
        ],
        params=[
            ParameterSpec(
                name        = "const",
                type        = float,
                default     = 1.0,
                label       = "Constant",
                description = "Scalar numerator: result = constant / data.",
            ),
        ],
    ),
    description = "Compute constant / data element-wise for every layer of a 3-D stack.",
)
def const_divide(inputs: dict, params: dict, *, annotations=None) -> UdsDataStru:
    src = inputs["data"]
    out = params["const"] / src.data
    return UdsDataStru(
        name         = src.name + "_mat",
        data         = out,
        axes         = [copy.deepcopy(ax) for ax in src.axes],
        info         = dict(src.info),
        proc_history = [copy.deepcopy(r) for r in src.proc_history],
    )


# ---------------------------------------------------------------------------
# math.complex_abs
# ---------------------------------------------------------------------------

@register_process(
    name        = "math.complex_abs_2d",
    label       = "Complex Abs 2D",
    category    = "Arithmetic & Normalization",
    schema      = ProcessSchema(
        outputs=_OUT_3D,
        inputs=[
            InputSpec(
                name        = "data",
                type_id     = "uds",
                label       = "3D Stack",
                description = "3-D stack; may contain complex values.",
                ndim        = 3,
            ),
        ],
        params=[],
    ),
    description = "Compute the element-wise modulus |data| of a 3-D stack.",
)
def complex_abs(inputs: dict, params: dict, *, annotations=None) -> UdsDataStru:
    src = inputs["data"]
    out = np.abs(src.data)
    return UdsDataStru(
        name         = src.name + "_abs",
        data         = out,
        axes         = [copy.deepcopy(ax) for ax in src.axes],
        info         = dict(src.info),
        proc_history = [copy.deepcopy(r) for r in src.proc_history],
    )
