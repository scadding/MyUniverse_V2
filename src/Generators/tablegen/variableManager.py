#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from src.Generators.tablegen.tableNode import tableVariableNode
from anytree import RenderTree
from src.Singleton import Singleton

class variableManager(metaclass=Singleton):
    variables : tableVariableNode
    globals : tableVariableNode
    state : tableVariableNode
    current : tableVariableNode
    base : tableVariableNode
    def __init__(self):
        self.variables = tableVariableNode("Variables")
        self.globals = tableVariableNode("Globals", parent=self.variables)
        self.state = tableVariableNode("State", parent=self.variables)
        self.current = tableVariableNode("Current", parent=self.variables)
        self.base = tableVariableNode("Base", parent=self.variables)
    def printVariableTree(self):
        for pre, _, n in RenderTree(self.variables):
            treestr = u"%s%s" % (pre, n.name)
            print(treestr.ljust(8))
    def getVariableNode(self, root, node, name=None):
        path = node.nodePath()
        if name:
            path.append(name)
        variablenode = root
        for n in path:
            matchNode = None
            for childNode in variablenode.children:
                if n == childNode.name:
                    matchNode = childNode
                    break
            if matchNode:
                variablenode = matchNode
            else:
                variablenode = tableVariableNode(n, parent = variablenode)
        return variablenode
    def getAllBaseVariables(self, node):
        rootVariableNode = self.getVariableNode(self.base, node)
        for name in rootVariableNode.variabledict:
            yield name, rootVariableNode.variabledict[name]
    def getBaseVariable(self, node, var):
        variablenode = self.getVariableNode(self.base, node)
        return variablenode.getVariable(var)
    def setBaseVariable(self, node, var, val):
        variablenode = self.getVariableNode(self.base, node)
        variablenode.setVariable(var, val)
    def getStateVariable(self, node, name, var):
        variablenode = self.getVariableNode(self.state, node, name=name)
        return variablenode.getVariable(var)
    def setStateVariable(self, node, name, var, val):
        variablenode = self.getVariableNode(self.state, node, name=name)
        variablenode.setVariable(var, val)
    def saveState(self, node, name):
        variableNode = self.getVariableNode(self.current, node)
        for n in variableNode.variabledict:
            if n[0] == '_':
                # temp variable
                continue
            v = variableNode.variabledict[n]
            print('<<%s>> = "%s"' % (n, v))
            self.setStateVariable(node, name, n, v)
    def getVariable(self, node, var):
        variablenode = self.getVariableNode(self.current, node)
        return variablenode.getVariable(var)
    def setVariable(self, node, var, val):
        variablenode = self.getVariableNode(self.current, node)
        variablenode.setVariable(var, val)
    def clearVariables(self, node):
        variablenode = self.getVariableNode(self.current, node)
        variablenode.clearVariables()

