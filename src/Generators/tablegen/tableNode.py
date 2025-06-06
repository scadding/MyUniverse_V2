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
from src.Configuration import Configuration

from anytree import Node, RenderTree, AsciiStyle, LevelOrderIter, NodeMixin


class tableNode(NodeMixin):
    filename : str
    def __init__(self, name, parent=None, children=None, uuid=None, loaded=False, filename=None, type=None, table=None, **kwargs):
        self.__dict__.update(kwargs)
        self.name = name
        self.parent = parent
        if children:
            self.children = children
        self.uuid = uuid
        self.loaded = loaded
        if filename:
            self.filename=filename
        self.type = type
        self.table = table
    def getNode(self, name, type=None):
        parent = self
        for c in parent.children:
            if c.name == name:
                if type:
                    if type == c.type:
                        return c
                else:
                    return c
        return None
    def pathToNode(self, exp):
        target = self.root
        # table path
        absolute = re.compile(r'([\w -]+)\.(.*)$')
        local = re.compile(r'([\w -]+)$')
        m = absolute.match(exp)
        while m:
            exp = m.group(2)
            parent = target
            target = target.getNode(m.group(1))
            m = absolute.match(m.group(2))
        if target:
            return target.getNode(exp)
        m = local.match(exp)
        if m:
            target = self.parent
            return target.getNode(m.group(1))
        raise Exception('Bad Path')
    def nodePath(self):
        path = []
        for p in self.path[1:]:
            path.append(p.name)
        return path


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

class tableStateNode(tableVariableNode):
    def __init__(self, name, parent=None, children=None, template=None):
        super().__init__(name, parent=parent, children=children)
        self.template = template
    def getVariable(self, var):
        if var in self.variabledict:
            return self.variabledict[var]
        return ""
    def setVariable(self, var, val):
        self.variabledict[var] = val
