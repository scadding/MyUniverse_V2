#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from stat import S_ISDIR, S_ISREG
import random as rand
import importlib
import sqlite3 as lite
from sqlalchemy import create_engine, text, MetaData, Connection, orm
from sqlalchemy import Table, Column, Integer, String, Text, Uuid
from sqlalchemy import select, column, func, table
import uuid

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
            variableManager.__init__(cls)
            parseManager.__init__(cls)
            cls.tree = tableNode("Root", uuid=None)
            cls.config = Configuration()
            cls._instance.walktree(cls.config.getValue("Data", "directory"), load=False, node=cls.tree)
            cls._instance.loaddb()
        return cls._instance
    def loaddb(self):
        self.engine = create_engine("sqlite+pysqlite:///test.db", echo=False)
        self.metadata_obj = MetaData()
        self.metadata_obj.reflect(self.engine)
        with self.engine.connect() as conn:
            if not self.engine.dialect.has_table(conn, 'Tables'):
                self.createDatabase()
                return
        self.loadTree(self.tree)
    def loadTree(self, node : tableNode):
        table = self.metadata_obj.tables['Nodes']
        statement = select(table.c.Node, table.c.Name).where(table.c.Parent == None)
        with orm.Session(self.engine) as session:
            row = session.execute(statement).first()
            node.uuid = uuid.UUID(row[0])
            self.loadChildren(session, node)
    def loadChildren(self, session : orm.Session, parent : tableNode):
        table = self.metadata_obj.tables['Nodes']
        statement = select(table.c.Node, table.c.Name).where(table.c.Parent == parent.uuid)
        for row in session.execute(statement):
            node = tableNode(row[1], parent=parent, table=None, display=True, uuid=uuid.UUID(row[0]))
            self.loadChildren(session, node)
    def prepareMetaData(self):
        objects = Table(
            "Objects",
            self.metadata_obj,
            Column("Object", Uuid, primary_key=True),
            Column("Node", Uuid, nullable=False),
        )
        Variables = Table(
            "Variables",
            self.metadata_obj,
            Column("Object", Uuid, nullable=False),
            Column("Name", Text, nullable=False),
            Column("Value", Text, nullable=False),
        )
        TableVariables = Table(
            "TableVariables",
            self.metadata_obj,
            Column("Node", Uuid, nullable=False),
            Column("TableName", Text, nullable=False),
            Column("Name", Text, nullable=False),
            Column("Value", Text, nullable=False),
        )
        TableLines = Table(
            "TableLines",
            self.metadata_obj,
            Column("Node", Uuid, nullable=False),
            Column("TableName", Text, nullable=False),
            Column("SubTableName", Text, nullable=False),
            Column("Roll", Integer, nullable=False),
            Column("Line", Text, nullable=False),
        )
        Tables = Table(
            "Tables",
            self.metadata_obj,
            Column("Node", Uuid, nullable=False),
            Column("TableName", Text, nullable=False),
            Column("SubTableName", Text, nullable=False),
            Column("Type", Text, nullable=False),
            Column("Length", Integer, nullable=False),
        )
        Nodes = Table(
            "Nodes",
            self.metadata_obj,
            Column("Node", Uuid, primary_key=True),
            Column("Name", Text, nullable=False),
            Column("Parent", Uuid),
        )
    def createDatabase(self):
        self.prepareMetaData()
        self.metadata_obj.create_all(self.engine)
        with self.engine.connect() as conn:
            self.importNode(conn, self.tree)
            conn.commit()
    def importTable(self, conn : Connection, node : tableNode):
        self.checkload(node)
        t : tableFile = node.table
        self.importVariables(conn, node)
        for subTable in t.table:
            self.importSubTable(conn, subTable, node)
    def importSubTable(self, conn : Connection, name, node : tableNode):
        subTable = node.table.table[name]
        if subTable.csvflag:
            ttype = 'csv'
        else:
            ttype = 'continuous'
        statement = self.metadata_obj.tables['Tables'].insert().values(Node=node.uuid, TableName=node.name, SubTableName=name, Type=ttype, Length=subTable.index)
        compiled = statement.compile()
        conn.execute(statement)
        for index in subTable.values:
            if not  subTable.csvflag:
                line = subTable.values[index][0]
            else:
                line = ''
                i = 0
                for k in subTable.values[index]:
                    if i > 0:
                        line = line + ', '
                    line = line + k
                    i += 1
            statement = self.metadata_obj.tables['TableLines'].insert().values(Node=node.uuid, TableName=node.name, SubTableName=name, Roll=index, Line=line)
            compiled = statement.compile()
            conn.execute(statement)
    def importVariables(self, conn : Connection, node : tableNode):
        rootVariableNode = self.getVariableNode(self.base, node)
        for name in rootVariableNode.variabledict:
            value = rootVariableNode.variabledict[name]
            statement = self.metadata_obj.tables['TableVariables'].insert().values(Node=node.uuid, TableName=node.name, Name=name, Value=value)
            compiled = statement.compile()
            conn.execute(statement)
    def importNode(self, conn : Connection, node : tableNode, parent : uuid=None):
        node.uuid = uuid.uuid4()
        self.metadata_obj.tables['Nodes']
        statement = self.metadata_obj.tables['Nodes'].insert().values(Node=node.uuid, Name=node.name, Parent=parent)
        compiled = statement.compile()
        conn.execute(statement)
        if node.is_leaf and node.type == "tab":
            self.importTable(conn, node)
            print(node.filename)
            conn.commit()
        for child in node.children:
            self.importNode(conn, child, node.uuid)
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
                node = tableNode(tail, parent=previous, table=None, display=True, uuid=None)
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
        node = tableNode(name, parent=parent, table=None, loaded=load, type=extension[1:], filename=filename, display=display, uuid=None)
        if not(extension == '.py' or extension == '.tab'):
            return
        if load:
            self.loadtable(node)
        return
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
        if node.uuid:
            return
        if not node.loaded:
            self.loadtable(node)
    def rollDB(self, node):
        return ''
    def roll(self, node):
        if type(node) != tableNode:
            raise TypeError
        self.checkload(node)
        s = ''
        if node.uuid:
            s = self.rollDB(node)
        elif node.table:
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


    
