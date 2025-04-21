# -*- coding: utf-8 -*-
"""
Created on Sun Apr 14 12:37:37 2024

@author: jiahaoYan
"""

from PyQt5 import QtWidgets
from PyQt5.QtCore import pyqtSignal

from ..general.RegExpSimplifedNumber import RegExpSimplifiedNumber
from ..general.NumberExpression import NumberExpression

class SimplifiedNumberLineEditor(QtWidgets.QLineEdit):
    validTextChanged = pyqtSignal()  # Signal for value change
    
    def __init__(self, parent=None):
        super(SimplifiedNumberLineEditor, self).__init__(parent)
        self.valid_text = ''
        
        self.editingFinished.connect(self.isChangedTextValid)
    
    def snText(self):
        return self.valid_text
    
    def setSNText(self, text):
        if RegExpSimplifiedNumber.isSimplifiedNumber(text):
            self.valid_text = text
            self.setText(text)
    
    def value(self):
        sn_txt = self.valid_text
        return NumberExpression.simplified_number_to_float(sn_txt)
    
    def setValue(self, value):
        sn_txt = NumberExpression.float_to_simplified_number(value)
        self. setSNText(sn_txt)
            
    def isChangedTextValid(self):
        input_text = self.text()
        
        if RegExpSimplifiedNumber.isSimplifiedNumber(input_text):
            self.valid_text = input_text
            self.validTextChanged.emit()
        else:
            self.setText(self.valid_text)