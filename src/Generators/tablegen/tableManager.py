#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from stat import S_ISDIR, S_ISREG
import random as rand
import importlib
import sqlite3 as lite
import sys
from src.Generators.tablegen.table import tableFile, tableDB
from src.Generators.tablegen.tableNode import tableNode
from src.Generators.tablegen.parseManager import parseManager
from src.Generators.tablegen.variableManager import variableManager
from src.Configuration import Configuration

class tableMgr(variableManager, parseManager):
    ignoredir = ["__pycache__"]
    ignoreext = ['.tml']
    _instance = None
    tree : tableNode
    config : Configuration
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(tableMgr, cls).__new__(cls)
            cls.tree = tableNode("Root")
            cls.config = Configuration()
            cls._instance.walktree(cls.config.getValue("Data", "directory"), load=False, node=cls.tree)
        return cls._instance
    def walktree(self, top : str, load=False, node=None):
        for filename in os.listdir(top):
            path = os.path.join(top, filename)
            mode = os.stat(path).st_mode
            head, tail = os.path.split(filename)
            if S_ISDIR(mode):
                # It's a directory, recurse into it
                if tail in self.ignoredir:
                    continue
                previous = node
                node = tableNode(tail, parent=previous, table=None, display=True)
                self.walktree(path, load, node=node)
                node = previous
            elif S_ISREG(mode):
                self.addfile(path, load=load, parent=node)
            else:
                # Unknown file type, print a message
                print('Skipping %s' % path)
    def getTree(self):
        return self.tree
    def setSeed(self, seed):
        rand.seed(seed)
    def addfile(self, filename, parent=None, load=False):
        basename = os.path.basename(filename)
        group = os.path.basename(os.path.dirname(filename))
        name, extension = os.path.splitext(basename)
        display = True
        if extension in self.ignoreext:
            display = False
        if name.startswith("_"):
            display = False
        node = tableNode(name, parent=parent, table=None, loaded=load, type=extension[1:], filename=filename, display=display)
        if extension == '.db':
            self.loadDB(filename, parent=parent)
        if not(extension == '.py' or extension == '.tab'):
            return
        if load:
            self.loadtable(node)
        return
    def loadDB(self, filename, parent=None):
        con = lite.connect(filename)
        cur = con.cursor()
        cur.execute("SELECT DISTINCT Genre FROM Tables")
        groups = dict()
        for row in cur.fetchall():
            group = row[0]
            if not groups.get(group):
                groups[group] = set()
        for g in groups:
            cur.execute("SELECT DISTINCT TableName FROM Tables WHERE Genre == \"%s\"" % (g))
            for row in cur.fetchall():
                name = row[0]
                groups[g].add(name)
                node = tableNode(name, parent=parent, table=tableDB(name, g, con), loaded=True, filename=filename, display=True)
    def loadtable(self, node):
        node.loaded = True
        extension = os.path.splitext(node.filename)[1]
        if extension == '.tab' or extension == '.tml':
            node.table = tableFile(node.filename, self, node)
            return node.table
        elif extension == '.py':
            spec = importlib.util.spec_from_file_location(node.name, node.filename)
            module = importlib.util.module_from_spec(spec)
            sys.modules[node.name] = module
            spec.loader.exec_module(module)
            node.table = module.generator()
            if node.table.version() > 1.0:
                node.table.SetManager(self)
            return node.table
    def checkload(self, node):
        if not node.loaded:
            self.loadtable(node)
    def roll(self, node):
        if type(node) != tableNode:
            raise TypeError
        self.checkload(node)
        s = node.table.start()
        s = self.parse(node, s)
        self.printVariableTree()
        self.clearVariables(node)
        return s
    def run(self, node, sub='Start', roll=-1, column=0):
        self.checkload(node)
        s = node.table.run(sub, roll, column)
        s = self.parse(node, s)
        return s
    def get_random_index(self, node, sub="Start"):
        self.checkload(node)
        return node.table.get_random_index(sub)
    def getCount(self, node, sub="Start"):
        self.checkload(node)
        return node.table.getCount(sub)
    def saveState(self, node, path, name):
        variableNode = self.getVariableNode(self.current, node)
        rootVariableNode = self.getVariableNode(self.base, node)
        for n in rootVariableNode.variabledict:
            if n in variableNode.variabledict:
                v = self.parse(node, variableNode.variabledict[n])
            else:
                v = self.parse(node, rootVariableNode.variabledict[n])
            self.setStateVariable(node, name, n, v)
        for n in variableNode.variabledict:
            if n in rootVariableNode.variabledict:
                v = self.parse(node, rootVariableNode.variabledict[n])
            else:
                v = self.parse(node, variableNode.variabledict[n])
                self.setStateVariable(node, name, n, v)


    
