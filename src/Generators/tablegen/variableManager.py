#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from src.Generators.tablegen.tableNode import tableNode, tableVariableNode, tableStateNode
from anytree import RenderTree
from src.Singleton import Singleton
import uuid
from sqlalchemy import create_engine, text, MetaData, Connection, orm
from sqlalchemy import Table, Column, Integer, String, Text, Uuid
from sqlalchemy import select, column, func, table

from src.Generators.tablegen.databaseManager import databaseManager

class variableManager(metaclass=Singleton):
    variables : tableVariableNode
    globals : tableVariableNode
    state : tableVariableNode
    current : tableVariableNode
    base : tableVariableNode
    def __init__(self):
        self.variables = tableVariableNode("Variables")
        self.globals = tableVariableNode("Globals", parent=self.variables)
        self.state = tableStateNode("State", parent=self.variables)
        self.current = tableVariableNode("Current", parent=self.variables)
        self.base = tableVariableNode("Base", parent=self.variables)
    def printVariableTree(self, tree = None):
        if tree is None:
            tree = self.variables
        for pre, _, n in RenderTree(tree):
            treestr = u"%s%s" % (pre, n.name)
            print(treestr.ljust(8))
    def getVariableNode(self, root, node : tableNode, name=None):
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
            elif type(variablenode) is tableStateNode:
                variablenode = tableStateNode(n, parent = variablenode)
            else:
                variablenode = tableVariableNode(n, parent = variablenode)
        return variablenode
    def getAllBaseVariables(self, node : tableNode):
        rootVariableNode = self.getVariableNode(self.base, node)
        for name in rootVariableNode.variabledict:
            yield name, rootVariableNode.variabledict[name]
    def getBaseVariable(self, node : tableNode, var):
        variablenode = self.getVariableNode(self.base, node)
        return variablenode.getVariable(var)
    def setBaseVariable(self, node : tableNode, var, val):
        variablenode = self.getVariableNode(self.base, node)
        variablenode.setVariable(var, val)
    def getStateVariable(self, node : tableNode, name, var):
        variablenode = self.getVariableNode(self.state, node, name=name)
        return variablenode.getVariable(var)
    def setStateVariable(self, node : tableNode, name, var, val):
        variablenode = self.getVariableNode(self.state, node, name=name)
        variablenode.setVariable(var, val)
    def saveState(self, node : tableNode, name):
        variableNode = self.getVariableNode(self.current, node)
        for variableName in variableNode.variabledict:
            if variableName[0] == '_':
                # temp variable
                continue
            value = variableNode.variabledict[variableName]
            print('<<%s>> = "%s"' % (variableName, value))
            self.setStateVariable(node, name, variableName, value)
        self.printVariableTree(self.state)
    def getVariable(self, node : tableNode, var):
        variablenode = self.getVariableNode(self.current, node)
        return variablenode.getVariable(var)
    def setVariable(self, node : tableNode, var, val):
        variablenode = self.getVariableNode(self.current, node)
        variablenode.setVariable(var, val)
    def clearVariables(self, node : tableNode):
        variablenode = self.getVariableNode(self.current, node)
        variablenode.clearVariables()
    def importVariables(self, node : tableNode, id : uuid.UUID):
        for name, value in self.getAllBaseVariables(node):            
            statement = databaseManager().metadata_obj.tables['universe.TableVariables'].insert().values(Node=id, TableName=node.name, Name=name, Value=value)
            with databaseManager().engine.connect() as conn:
                conn.execute(statement)
                conn.commit()
                conn.close()
    def loadVariables(self):
        table = databaseManager().metadata_obj.tables['universe.TableVariables']
        statement = select(table.c.Name, table.c.Value).where(table.c.Node == self.uuid)
        with orm.Session(databaseManager().engine) as session:
            for row in session.execute(statement):
                variableManager().setBaseVariable(self.node, row[0], row[1])
            session.close()

