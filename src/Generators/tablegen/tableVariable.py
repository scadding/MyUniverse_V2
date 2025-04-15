#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from stat import S_ISDIR, S_ISREG
import re
import random as rand
import importlib
import importlib.machinery
import csv
from optparse import OptionParser
from src.Generators.tablegen import tableFunctions
import pyparsing
import sqlite3 as lite
import sys
import codecs
from src.Generators.tablegen.table import tableNode
from src.Configuration import Configuration

from anytree import Node, RenderTree, AsciiStyle, LevelOrderIter, NodeMixin


class tableVariableNode(tableNode):
    variabledict : dict
    def __init__(self, name, parent=None, children=None):
        super().__init__(name, parent=parent, children=children)
        self.variabledict = dict()
    def getVariable(self, var):
        if var in self.variabledict:
            return self.variabledict[var]
        return ""
    def setVariable(self, var, val):
        self.variabledict[var] = val
    def removeVariable(self, var, val):
        del self.variabledict[var]
    def clearVariables(self):
        self.variabledict = dict()

