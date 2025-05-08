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
    def __init__(self, name, parent=None, children=None, uuid=None, **kwargs):
        self.__dict__.update(kwargs)
        self.name = name
        self.parent = parent
        if children:
            self.children = children
        self.uuid = uuid
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
    def pathToNode(self, exp, type=None):
        target = None
        # table path
        absolute = re.compile(r'([\w -]+)\.(.*)$')
        relative = re.compile(r'\.([\w -]*)\.(.*)$')
        local = re.compile(r'([\w -]+)$')
        m = absolute.match(exp)
        if m:
            target = self.root
        while m:
            exp = m.group(2)
            parent = target
            target = target.getNode(m.group(1))
            m = absolute.match(m.group(2))
        if target:
            return target.getNode(exp)
        m = relative.match(exp)
        if m:
            target = self.parent
        while m:
            target = target.getNode(m.group(1))
            m = relative.match(m.group(2))
        if target:
            return target.getNode(exp)
        m = local.match(exp)
        if m:
            target = self.parent
            return target.getNode(m.group(1))
        return None
    def nodePath(self):
        path = []
        for p in self.path[1:]:
            path.append(p.name)
        return path


class tableVariableNode(tableNode):
    variabledict : dict
    basevariabledict : dict
    def __init__(self, name, parent=None, children=None):
        super().__init__(name, parent=parent, children=children)
        self.variabledict = dict()
        self.basevariabledict = dict()
    def create(self, name):
        return tableVariableNode(name, parent=self)
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

