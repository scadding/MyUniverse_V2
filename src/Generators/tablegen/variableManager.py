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
    def getVariable(self, node, var):
        variablenode = self.getVariableNode(self.current, node)
        return variablenode.getVariable(var)
    def setVariable(self, node, var, val):
        variablenode = self.getVariableNode(self.current, node)
        variablenode.setVariable(var, val)
    def clearVariables(self, node):
        variablenode = self.getVariableNode(self.current, node)
        variablenode.clearVariables()

