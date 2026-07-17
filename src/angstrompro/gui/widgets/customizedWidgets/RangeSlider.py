# -*- coding: utf-8 -*-
"""
Created on Mon Apr  8 20:50:25 2024

@author: jiahao yan
"""
from angstrompro.utils.qt_compat import (
    QtCore, QtWidgets, QtGui, Signal,
    Horizontal, LeftButton, StrongFocus, NoPen, Antialiasing,
)


class RangeSlider(QtWidgets.QWidget):
    valueChanged = Signal(int, int)

    def __init__(self, orientation=Horizontal, parent=None):
        super().__init__(parent)
        self.orientation = orientation
        self.minimum = 0
        self.maximum = 1000
        self.lowerValue = 250
        self.upperValue = 750

        self.handleWidth  = 15
        self.handleHeight = 15
        self.isLowerHandleMoving = False
        self.isUpperHandleMoving = False

        self.setMouseTracking(True)
        self.setFocusPolicy(StrongFocus)

        if self.orientation == Horizontal:
            self.setMinimumWidth(120)
            self.setMinimumHeight(15)
        else:
            self.setMinimumWidth(15)
            self.setMinimumHeight(120)

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(Antialiasing)

        borderPen = QtGui.QPen(QtGui.QColor(50, 50, 50), 1)
        painter.setPen(borderPen)

        grooveWidth = 5
        painter.setBrush(QtGui.QColor(235, 235, 235))
        if self.orientation == Horizontal:
            rect = QtCore.QRect(0, (self.height() - grooveWidth) // 2, self.width(), grooveWidth)
        else:
            rect = QtCore.QRect((self.width() - grooveWidth) // 2, 0, grooveWidth, self.height())
        painter.drawRect(rect)

        painter.setPen(NoPen)

        painter.setBrush(QtGui.QColor(0, 120, 215))
        if self.orientation == Horizontal:
            lower_rect = QtCore.QRect(
                int(self.valueToPosition(self.lowerValue) - self.handleWidth // 2),
                int((self.height() - self.handleHeight) // 2),
                int(self.handleWidth), int(self.handleHeight))
        else:
            lower_rect = QtCore.QRect(
                int((self.width() - self.handleWidth) // 2),
                int(self.valueToPosition(self.lowerValue) + self.handleHeight // 2),
                int(self.handleWidth), int(self.handleHeight))
        painter.drawRect(lower_rect)

        painter.setBrush(QtGui.QColor(215, 20, 0))
        if self.orientation == Horizontal:
            upper_rect = QtCore.QRect(
                int(self.valueToPosition(self.upperValue) - self.handleWidth // 2),
                int((self.height() - self.handleHeight) // 2),
                int(self.handleWidth), int(self.handleHeight))
        else:
            upper_rect = QtCore.QRect(
                int((self.width() - self.handleWidth) // 2),
                int(self.valueToPosition(self.upperValue) + self.handleHeight // 2),
                int(self.handleWidth), int(self.handleHeight))
        painter.drawRect(upper_rect)

    def setValue(self, lowerValue, upperValue):
        self.lowerValue = lowerValue
        self.upperValue = upperValue
        self.update()

    def setRange(self, min_value, max_value):
        self.minimum = min_value
        self.maximum = max_value

    def lowerV(self):
        return self.lowerValue

    def upperV(self):
        return self.upperValue

    def mousePressEvent(self, event):
        if event.button() == LeftButton:
            if self.valueToRect(self.lowerValue).contains(event.pos()):
                self.isLowerHandleMoving = True
            elif self.valueToRect(self.upperValue).contains(event.pos()):
                self.isUpperHandleMoving = True

    def mouseMoveEvent(self, event):
        if self.isLowerHandleMoving or self.isUpperHandleMoving:
            if self.orientation == Horizontal:
                pos = event.pos().x()
            else:
                pos = self.height() - event.pos().y() - self.handleHeight / 2
            value = self.rectToValue(pos)
            if self.isLowerHandleMoving:
                self.lowerValue = max(self.minimum, min(value, self.upperValue - 1))
            else:
                self.upperValue = min(self.maximum, max(value, self.lowerValue + 1))
            self.valueChanged.emit(self.lowerValue, self.upperValue)
            self.update()

    def mouseReleaseEvent(self, event):
        self.isLowerHandleMoving = False
        self.isUpperHandleMoving = False

    def valueToRect(self, value):
        Range = self.maximum - self.minimum
        if self.orientation == Horizontal:
            sliderRange = self.width() - self.handleWidth
            x = ((value - self.minimum) / Range) * sliderRange
            return QtCore.QRect(int(x), int((self.height() - self.handleHeight) / 2),
                                self.handleWidth, self.handleHeight)
        else:
            sliderRange = self.height() - self.handleHeight
            y = ((self.maximum - value) / Range) * sliderRange
            return QtCore.QRect(int((self.width() - self.handleWidth) / 2), int(y),
                                self.handleWidth, self.handleHeight)

    def rectToValue(self, pos):
        Range = self.maximum - self.minimum
        if self.orientation == Horizontal:
            sliderLength = self.width() - self.handleWidth
            value = ((pos - self.handleWidth / 2) / sliderLength) * Range + self.minimum
        else:
            sliderLength = self.height() - self.handleHeight
            value = self.maximum - Range * (1 - ((pos - self.handleHeight / 2) / sliderLength)) + self.handleHeight
        return int(value)

    def valueToPosition(self, value):
        Range = self.maximum - self.minimum
        if self.orientation == Horizontal:
            sliderLength = self.width() - self.handleWidth
            return (value - self.minimum) / Range * sliderLength + self.handleWidth / 2
        else:
            sliderLength = self.height() - self.handleHeight
            return (self.maximum - value) / Range * sliderLength - self.handleHeight / 2
