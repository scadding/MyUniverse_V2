#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import uuid

from src.Generators.tablegen.table import tableFile, tableDB
from src.Generators.tablegen.tableNode import tableNode
from src.Generators.tablegen.parseManager import parseManager
from src.Generators.tablegen.variableManager import variableManager
from src.Generators.tablegen.databaseManager import databaseManager
from src.Configuration import Configuration
from src.Singleton import Singleton

class stateManager(variableManager, metaclass=Singleton):
    tree : tableNode
    def __init__(self):
        self.tree = tableNode("Root", uuid=None)
    def getTree(self):
        return self.tree
