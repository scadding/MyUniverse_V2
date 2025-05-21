#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from stat import S_ISDIR, S_ISREG
import random as rand
import importlib
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

class tableMgr(object):
    ignoredir = ["__pycache__"]
    ignoreext = ['.tml']
    _instance = None
    tree : tableNode
    config : Configuration
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(tableMgr, cls).__new__(cls)
            cls.variableManager = variableManager()
            cls.parseManager = parseManager()
            cls.tree = tableNode("Root", uuid=None)
            cls.config = Configuration()
            cls._instance.walktree(cls.config.getValue("Data", "directory"), load=False, node=cls.tree)
            cls._instance.loaddb()
        return cls._instance
    def loaddb(self):
        if not self.config.getValue("Data", "dbconnection"):
            return
        self.engine = create_engine(self.config.getValue("Data", "dbconnection"), echo=False)
        self.metadata_obj = MetaData()
        self.metadata_obj.reflect(self.engine)
        with self.engine.connect() as conn:
            if not self.engine.dialect.has_table(conn, 'universe.Tables'):
                conn.close()
                self.createDatabase()
            else:
                conn.close()
                self.loadTree(self.tree)
    def loadTree(self, node : tableNode):
        table = self.metadata_obj.tables['universe.Nodes']
        statement = select(table.c.Node, table.c.Name).where(table.c.Parent == None)
        with orm.Session(self.engine) as session:
            row = session.execute(statement).first()
            if not row:
                return
            node.uuid = uuid.UUID(row[0])
            self.loadChildren(session, node)
        session.close()
    def loadChildren(self, session : orm.Session, parent : tableNode):
        table = self.metadata_obj.tables['universe.Nodes']
        statement = select(table.c.Node, table.c.Name).where(table.c.Parent == parent.uuid)
        for row in session.execute(statement):
            node = tableNode(row[1], parent=parent, table=None, display=True, uuid=uuid.UUID(row[0]))
            self.loadChildren(session, node)
    def prepareMetaData(self):
        objects = Table(
            "universe.Objects",
            self.metadata_obj,
            Column("Object", Uuid, primary_key=True),
            Column("Node", Uuid, nullable=False),
        )
        Variables = Table(
            "universe.Variables",
            self.metadata_obj,
            Column("Object", Uuid, nullable=False),
            Column("Name", Text, nullable=False),
            Column("Value", Text, nullable=False),
        )
        TableVariables = Table(
            "universe.TableVariables",
            self.metadata_obj,
            Column("Node", Uuid, nullable=False),
            Column("TableName", Text, nullable=False),
            Column("Name", Text, nullable=False),
            Column("Value", Text, nullable=False),
        )
        TableLines = Table(
            "universe.TableLines",
            self.metadata_obj,
            Column("Node", Uuid, nullable=False),
            Column("TableName", Text, nullable=False),
            Column("SubTableName", Text, nullable=False),
            Column("Roll", Integer, nullable=False),
            Column("Line", Text, nullable=False),
        )
        Tables = Table(
            "universe.Tables",
            self.metadata_obj,
            Column("Node", Uuid, nullable=False),
            Column("TableName", Text, nullable=False),
            Column("SubTableName", Text, nullable=False),
            Column("Type", Text, nullable=False),
            Column("Length", Integer, nullable=False),
        )
        Nodes = Table(
            "universe.Nodes",
            self.metadata_obj,
            Column("Node", Uuid, primary_key=True),
            Column("Name", Text, nullable=False),
            Column("Parent", Uuid),
        )
    def createDatabase(self):
        self.prepareMetaData()
        with self.engine.connect() as conn:
            self.metadata_obj.create_all(conn)
        conn.commit()
        conn.close()
        self.importNode(self.tree)
    def importTable(self, node : tableNode, id : uuid):
        self.checkload(node)
        t : tableFile = node.table
        self.importVariables(node, id)
        for subTable in t.table:
            self.importSubTable(subTable, node, id)
    def importSubTable(self, name, node : tableNode, id : uuid):
        subTable = node.table.table[name]
        if subTable.csvflag:
            ttype = 'csv'
        else:
            ttype = 'continuous'
        statement = self.metadata_obj.tables['universe.Tables'].insert().values(Node=id, TableName=node.name, SubTableName=name, Type=ttype, Length=subTable.index)
        with self.engine.connect() as conn:
            conn.execute(statement)
            count = 0
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
                statement = self.metadata_obj.tables['universe.TableLines'].insert().values(Node=id, TableName=node.name, SubTableName=name, Roll=index, Line=line)
                conn.execute(statement)
                count += 1
            conn.commit()
            conn.close()
    def importVariables(self, node : tableNode, id : uuid):
        rootVariableNode = self.getVariableNode(self.base, node)
        for name in rootVariableNode.variabledict:
            value = rootVariableNode.variabledict[name]
            statement = self.metadata_obj.tables['universe.TableVariables'].insert().values(Node=id, TableName=node.name, Name=name, Value=value)
            with self.engine.connect() as conn:
                conn.execute(statement)
                conn.commit()
                conn.close()
    def importNode(self, node : tableNode, parent : uuid=None):
        id = uuid.uuid4()
        self.metadata_obj.tables['universe.Nodes']
        statement = self.metadata_obj.tables['universe.Nodes'].insert().values(Node=id, Name=node.name, Parent=parent)
        with self.engine.connect() as conn:
            conn.execute(statement)
            conn.commit()
            conn.close()
        if node.is_leaf and node.type == "tab":
            print('imorting table - %s' % node.filename)
            self.importTable(node, id)
        for child in node.children:
            self.importNode(child, parent=id)
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
        name, extension = os.path.splitext(basename)
        display = True
        if extension in self.ignoreext:
            display = False
        if name.startswith("_"):
            display = False
        node = tableNode(name, parent=parent, table=None, type=extension[1:], filename=filename, display=display, uuid=None)
        if not(extension == '.py' or extension == '.tab'):
            return
        if load:
            self.loadtable(node)
        return
    def loadtable(self, node : tableNode):
        node.loaded = True
        if node.uuid:
            node.table = tableDB(node, self)
            return
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
    def rollAll(self, node : tableNode):
        path = ''
        retval = ''
        for ancestor in node.path:
            path += ancestor.name + '.'
        #print(path[:-1])
        retval += '<br><br><b>'
        retval += path[:-1]
        retval += ':</b><br>'
        if node.children:
            for c in node.children:
                retval += self.rollAll(c)
        elif node.type == 'tab':
            retval += self.roll(node)
        return retval
    def roll(self, node : tableNode):
        if type(node) != tableNode:
            print(type(node))
            return ''
        if node.children:
            return self.rollAll(node)
        self.checkload(node)

        junk = node.table.start()
        test = ''
        retval = ''
        if node.table:
            for retval in self.parseManager.parse(node, junk):
                test = test + retval
        self.variableManager.printVariableTree()
        self.variableManager.clearVariables(node)
        return test

    
