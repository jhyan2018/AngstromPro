# -*- coding: utf-8 -*-
"""
Created on Tue Apr  9 16:04:58 2024

@author: Jiahao Yan
"""
import math
import numpy as np

from angstrompro.utils.qt_compat import QtCore, QtWidgets, Signal, Horizontal

from .customizedWidgets.RangeSlider import RangeSlider
from .customizedWidgets.SimplifiedNumberLineEditor import SimplifiedNumberLineEditor
from .general.NumberExpression import NumberExpression


class ScaleWidget(QtWidgets.QWidget):
    scaleChanged = Signal()

    def __init__(self, orientation=Horizontal, parent=None):
        super().__init__(parent)
        self.initNonUiMembers(orientation)
        self.initUiMembers()
        self.initUiLayout()

    def initNonUiMembers(self, orientation):
        self.orientation = orientation
        self.slider_max = 1000
        self.slider_min = 0
        self.slider_upper_value = self.slider_max
        self.slider_lower_value = self.slider_min

        self.data_max = 0.0
        self.data_min = 0.0
        self.data_upper_limit = 0.0
        self.data_lower_limit = 0.0
        self.data_upper_value = 0.0
        self.data_lower_value = 0.0
        self.zoom_out_factor = 0.6
        self.zoom_in_factor  = 0.6
        self.data_scale_fixed = False

        self.data_sigma_factor         = 4.5
        self.data_sigma_factor_default = 4.5
        self.data = 0

        self.indicator_upper_value = 0.0
        self.indicator_lower_value = 0.0

        self.auto_scale_strategy   = ''
        self.auto_scale_fft_factor = 1.0
        self.data_suffix = ''

    def initUiMembers(self):
        self.ui_rangeSlider = RangeSlider(self.orientation)
        self.ui_rangeSlider.setRange(self.slider_min, self.slider_max)
        self.ui_rangeSlider.valueChanged.connect(self.sliderMoved)

        self.ui_le_data_upper_value = SimplifiedNumberLineEditor()
        self.ui_le_data_upper_value.validTextChanged.connect(self.dataUpperValueChange)

        self.ui_le_data_lower_value = SimplifiedNumberLineEditor()
        self.ui_le_data_lower_value.validTextChanged.connect(self.dataLowerValueChanged)

        self.ui_le_data_sigma_factor = SimplifiedNumberLineEditor()
        self.ui_le_data_sigma_factor.setSNText(str(self.data_sigma_factor))
        self.ui_le_data_sigma_factor.validTextChanged.connect(self.sigmaFactorChanged)

        self.ui_pb_sigma = QtWidgets.QPushButton('σ')
        self.ui_pb_sigma.setCheckable(True)
        self.ui_pb_sigma.setChecked(True)
        self.setAutoScaleHistgram()
        self.ui_pb_sigma.clicked.connect(self.setAutoScaleHistgram)

        self.ui_pb_scale_full__sigma = QtWidgets.QPushButton('F')
        self.ui_pb_scale_full__sigma.clicked.connect(self.fullScale)
        self.ui_pb_scale_full__sigma.setMaximumSize(40, 40)

        self.ui_pb_scale_zoom_in = QtWidgets.QPushButton('i')
        self.ui_pb_scale_zoom_in.clicked.connect(self.zoomInScale)
        self.ui_pb_scale_zoom_in.setMaximumSize(40, 40)

        self.ui_pb_scale_zoom_out = QtWidgets.QPushButton('o')
        self.ui_pb_scale_zoom_out.clicked.connect(self.zoomOutScale)
        self.ui_pb_scale_zoom_out.setMaximumSize(40, 40)

    def initUiLayout(self):
        if self.orientation == Horizontal:
            h1 = QtWidgets.QHBoxLayout()
            h1.addWidget(self.ui_pb_scale_full__sigma)
            h1.addWidget(self.ui_pb_scale_zoom_out)
            h1.addWidget(self.ui_pb_scale_zoom_in)

            v1 = QtWidgets.QVBoxLayout()
            v1.addWidget(self.ui_le_data_sigma_factor)
            v1.addWidget(self.ui_pb_sigma)

            h2 = QtWidgets.QHBoxLayout()
            h2.addWidget(self.ui_le_data_lower_value)
            h2.addLayout(v1)
            h2.addWidget(self.ui_le_data_upper_value)

            v2 = QtWidgets.QVBoxLayout()
            v2.addLayout(h1)
            v2.addWidget(self.ui_rangeSlider)
            v2.addLayout(h2)

            grid = QtWidgets.QGridLayout()
            grid.addLayout(v2, 0, 0, 1, 1)
        else:
            h1 = QtWidgets.QHBoxLayout()
            h1.addWidget(self.ui_pb_sigma)
            h1.addWidget(self.ui_le_data_sigma_factor)

            v1 = QtWidgets.QVBoxLayout()
            v1.addWidget(self.ui_le_data_upper_value)
            v1.addLayout(h1)
            v1.addWidget(self.ui_le_data_lower_value)

            v2 = QtWidgets.QVBoxLayout()
            v2.addWidget(self.ui_pb_scale_full__sigma)
            v2.addWidget(self.ui_pb_scale_zoom_out)
            v2.addWidget(self.ui_pb_scale_zoom_in)

            h2 = QtWidgets.QHBoxLayout()
            h2.addLayout(v2)
            h2.addWidget(self.ui_rangeSlider)
            h2.addLayout(v1)

            grid = QtWidgets.QGridLayout()
            grid.addLayout(h2, 0, 0, 1, 1)

        self.setLayout(grid)

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def sliderMoved(self, s_lowerV, s_upperV):
        s_min, s_max = self.slider_min, self.slider_max
        d_l_l, d_u_l = self.data_lower_limit, self.data_upper_limit

        self.data_lower_value = s_lowerV / (s_max - s_min) * (d_u_l - d_l_l) + d_l_l
        self.data_upper_value = s_upperV / (s_max - s_min) * (d_u_l - d_l_l) + d_l_l

        self.scaleChanged.emit()
        self.setIndicators(self.data_lower_value, self.data_upper_value)

    def sigmaFactorChanged(self):
        sigma = NumberExpression.simplified_number_to_float(self.ui_le_data_sigma_factor.text())
        self.setSigma(sigma)
        self.scaleChanged.emit()

    def dataLowerValueChanged(self):
        idc_l_v = NumberExpression.simplified_number_to_float(self.ui_le_data_lower_value.snText())
        if idc_l_v >= self.data_upper_value:
            self.ui_le_data_lower_value.setSNText(
                NumberExpression.float_to_simplified_number(self.data_lower_value))
        elif idc_l_v < self.data_lower_limit:
            self.data_lower_limit = idc_l_v
            self.data_lower_value = idc_l_v
            self.dataValueChanged()
        else:
            self.data_lower_value = idc_l_v
            self.dataValueChanged()

    def dataUpperValueChange(self):
        idc_u_v = NumberExpression.simplified_number_to_float(self.ui_le_data_upper_value.snText())
        if idc_u_v <= self.data_lower_value:
            self.ui_le_data_upper_value.setSNText(
                NumberExpression.float_to_simplified_number(self.data_upper_value))
        elif idc_u_v > self.data_upper_limit:
            self.data_upper_limit = idc_u_v
            self.data_upper_value = idc_u_v
            self.dataValueChanged()
        else:
            self.data_upper_value = idc_u_v
            self.dataValueChanged()

    def fullScale(self):
        self.data_sigma_factor = self.data_sigma_factor_default
        self.AutoScale()
        self.ui_le_data_sigma_factor.setSNText(str(self.data_sigma_factor))
        self.scaleChanged.emit()

    def zoomOutScale(self):
        data_limit_range = self.data_upper_limit - self.data_lower_limit
        data_l_diff = data_limit_range / (self.data_lower_value - self.data_lower_limit + 1)
        data_u_diff = data_limit_range / (self.data_upper_limit - self.data_upper_value + 1)
        self.data_lower_limit -= data_l_diff * self.zoom_out_factor
        self.data_upper_limit += data_u_diff * self.zoom_out_factor
        self.setSlierPosition()
        self.setIndicators(self.data_lower_value, self.data_upper_value)

    def zoomInScale(self):
        data_l_diff = self.data_lower_value - self.data_lower_limit
        data_u_diff = self.data_upper_limit - self.data_upper_value
        self.data_lower_limit += data_l_diff * self.zoom_in_factor
        self.data_upper_limit -= data_u_diff * self.zoom_in_factor
        self.setSlierPosition()
        self.setIndicators(self.data_lower_value, self.data_upper_value)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def lowerValue(self):
        return self.data_lower_value

    def upperValue(self):
        return self.data_upper_value

    def setData(self, data1D, suffix='SUFFIX_NON_FFT'):
        self.data = data1D
        self.data_max = np.max(self.data)
        self.data_min = np.min(self.data)

        if not self.data_scale_fixed:
            self.data_suffix = suffix
            if self.data_suffix == 'SUFFIX_FFT':
                self.ui_pb_sigma.setChecked(False)
            else:
                self.ui_pb_sigma.setChecked(True)
            self.setAutoScaleHistgram()

        self.ui_le_data_sigma_factor.setSNText(str(self.data_sigma_factor))

    def setZoomFactor(self, zoom_factor):
        if 0 < zoom_factor < 1:
            self.zoom_in_factor  = zoom_factor
            self.zoom_out_factor = zoom_factor

    def setSigmaDefault(self, sigma_default):
        self.data_sigma_factor_default = sigma_default
        self.data_sigma_factor         = sigma_default
        self.ui_le_data_sigma_factor.setSNText(str(sigma_default))
        if self.ui_pb_sigma.isChecked() and hasattr(self.data, '__len__') and len(self.data) > 0:
            self.AutoScale()
            self.scaleChanged.emit()

    def setSigma(self, sigma):
        self.data_sigma_factor = sigma
        self.AutoScale()

    def setAutoScaleHistgram(self):
        if self.ui_pb_sigma.isChecked():
            self.ui_le_data_sigma_factor.setEnabled(True)
            self.auto_scale_strategy = 'ASS_MAX_MIN'
        else:
            self.ui_le_data_sigma_factor.setEnabled(False)
            self.auto_scale_strategy = 'ASS_HISTGRAM'
        self.AutoScale()
        self.scaleChanged.emit()

    def setFFTAutoScaleFactor(self, fft_auto_scale_factor):
        if 0 < fft_auto_scale_factor <= 1:
            self.auto_scale_fft_factor = fft_auto_scale_factor
            if (self.data_suffix == 'SUFFIX_FFT'
                    and not self.ui_pb_sigma.isChecked()
                    and hasattr(self.data, '__len__') and len(self.data) > 0):
                self.AutoScale()
                self.scaleChanged.emit()

    def setDataScaleFixed(self, data_scale_fixed):
        self.data_scale_fixed = data_scale_fixed

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def AutoScale(self):
        if self.auto_scale_strategy == 'ASS_MAX_MIN':
            std  = np.std(self.data)
            mean = np.mean(self.data)
            self.data_lower_limit = mean - self.data_sigma_factor * std / 2
            self.data_upper_limit = mean + self.data_sigma_factor * std / 2
        elif self.auto_scale_strategy == 'ASS_HISTGRAM':
            self.data_lower_limit = min(self.data)
            if self.data_suffix == 'SUFFIX_FFT':
                self.data_upper_limit = max(self.data) * self.auto_scale_fft_factor
            else:
                self.data_upper_limit = max(self.data)

        self.data_lower_value = self.data_lower_limit
        self.data_upper_value = self.data_upper_limit
        self.setSlierPosition()
        self.setIndicators(self.data_lower_value, self.data_upper_value)

    def dataValueChanged(self):
        self.setSlierPosition()
        self.scaleChanged.emit()

    def setSlierPosition(self):
        d_l_v = self.data_lower_value
        d_u_v = self.data_upper_value
        d_l_l = self.data_lower_limit
        d_u_l = self.data_upper_limit

        exponents = [self.getFloatExponent(v) for v in (d_l_v, d_u_v, d_l_l, d_u_l)]
        ept_min = min(exponents)

        if (d_u_l - d_l_l) != 0 and (exponents[2] + exponents[3]) > -40:
            coeff = pow(10, ept_min)
            d_l_v_s = d_l_v * coeff
            d_u_v_s = d_u_v * coeff
            d_l_l_s = d_l_l * coeff
            d_u_l_s = d_u_l * coeff

            s_min, s_max = self.slider_min, self.slider_max
            s_l_v = int((d_l_v_s - d_l_l_s) * (s_max - s_min) / (d_u_l_s - d_l_l_s)) + s_min
            s_u_v = int((d_u_v_s - d_l_l_s) * (s_max - s_min) / (d_u_l_s - d_l_l_s)) + s_min
            self.ui_rangeSlider.setValue(s_l_v, s_u_v)

    def setIndicators(self, d_lower_value, d_upper_value):
        self.ui_le_data_lower_value.setText(NumberExpression.float_to_simplified_number(d_lower_value))
        self.ui_le_data_upper_value.setText(NumberExpression.float_to_simplified_number(d_upper_value))

    def getFloatExponent(self, value):
        if value == 0:
            return 0
        return math.floor(math.log10(abs(value)))
