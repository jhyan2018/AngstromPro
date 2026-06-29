# -*- coding: utf-8 -*-
"""
Created on Sun Apr 14 12:37:37 2024

@author: jiahaoYan
"""
from angstrompro.utils.qt_compat import QtWidgets, Signal

from ..general.RegExpSimplifedNumber import RegExpSimplifiedNumber
from ..general.NumberExpression import NumberExpression


class SimplifiedNumberLineEditor(QtWidgets.QLineEdit):
    validTextChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.valid_text = ''
        self.editingFinished.connect(self.isChangedTextValid)

    def snText(self):
        return self.valid_text

    def setSNText(self, text):
        if RegExpSimplifiedNumber.isSimplifiedNumber(text):
            self.valid_text = text
            self.setText(text)

    def value(self):
        return NumberExpression.simplified_number_to_float(self.valid_text)

    def setValue(self, value):
        sn_txt = NumberExpression.float_to_simplified_number(value)
        self.setSNText(sn_txt)

    def isChangedTextValid(self):
        input_text = self.text()
        if RegExpSimplifiedNumber.isSimplifiedNumber(input_text):
            self.valid_text = input_text
            self.validTextChanged.emit()
        else:
            self.setText(self.valid_text)
