#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from stat import S_ISDIR, S_ISREG
import re
import random as rand
import uuid
from sqlalchemy import create_engine, text, MetaData, Connection, orm
from sqlalchemy import Table, Column, Integer, String, Text, Uuid
from sqlalchemy import select, column, func, table
import csv
import sys
import codecs
from src.Generators.tablegen.tableNode import tableNode
from src.Generators.tablegen.variableManager import variableManager
from src.Generators.tablegen.databaseManager import databaseManager

from anytree import Node, RenderTree, AsciiStyle, LevelOrderIter, NodeMixin

class SubTable(object):
    def __init__(self, tablename, continuous, csvflag=False):
        self.values = dict()
        self.index = 0
        self.tablename = tablename
        self.continuous = continuous
        self.csvflag = csvflag
    def add(self, i, v):
        if i == 0:
            return
        if self.continuous:
            self.index = i
        else:
            self.index += i
        if not self.csvflag:
            if not self.values.get(self.index):
                self.values[self.index] = dict()
            self.values[self.index][0] = v
        else:
            for row in csv.reader([v]):
                self.values[self.index] = row
    def getvalue(self, index, column=0):
        if index > self.index:
            return 'Error: Out of Range'
        if column > 0 and not self.csvflag:
            return 'Error: Out of Range'
        d = index
        while self.values.get(d) is None:
            d = d + 1
        if len(self.values[d]) < (column + 1):
            return ''
        return self.values[d][column]
    def roll(self, column=0, roll=-1):
        if self.index == 0:
            return ''
        if roll == -1:
            roll = self.get_random_index()
        return self.getvalue(roll, column)
    def get_random_index(self):
        return rand.randrange(self.index) + 1
    def getCount(self):
        return self.index
    

class tableGroup(object):
    def __init__(self, node):
        self.variableManager = variableManager()
        self.node = node
    def start(self):
        return self.run('Start')


class tableDB(tableGroup):
    def __init__(self, node : tableNode):
        tableGroup.__init__(self, node)
        self.uuid = node.uuid
        self.count = dict()
        self.type = dict()
        self.tables = list()
        self.loadVariables()
        self.getMetaData()
    def getMetaData(self):
        table = databaseManager().metadata_obj.tables['universe.Tables']
        statement = select(table.c.SubTableName, table.c.Type, table.c.Length).where(table.c.Node == self.uuid)
        with orm.Session(databaseManager().engine) as session:
            for row in session.execute(statement):
                self.tables.append(row[0])
                self.type[row[0]] = row[1]
                self.count[row[0]] = row[2]
            session.close()
    def loadVariables(self):
        table = databaseManager().metadata_obj.tables['universe.TableVariables']
        statement = select(table.c.Name, table.c.Value).where(table.c.Node == self.uuid)
        with orm.Session(databaseManager().engine) as session:
            for row in session.execute(statement):
                variableManager().setBaseVariable(self.node, row[0], row[1])
            session.close()
    def getType(self, t):
        return self.type[t]
    def getCount(self, t):
        return self.count[t]
    def getLines(self, t='Start'):
        retval = list()
        table = databaseManager().metadata_obj.tables['universe.TableLines']
        statement = select(table.c.Roll, table.c.Line).where(table.c.Node == self.uuid).where(table.c.SubTableName == t).order_by(table.c.Roll)
        isCsv = self.getType(t)
        with orm.Session(databaseManager().engine) as session:
            for row in session.execute(statement):
                l = list()
                if isCsv:
                    l.append(row[0])
                    tmp = row[1].split(',')
                    t = list()
                    for e in tmp:
                        t.append(e.strip())
                    l.append(t)
                else:
                    l.append(row[0])
                    l.append(row[1])
                retval.append(l)
        session.close()
        return retval
    def start(self):
        return self.run()
    def run(self, t='Start', roll=-1, column=0):
        t=t.strip()
        if t not in self.tables:
            return self.autorunStart()
        retVal = u''
        length = self.getCount(t)
        if length == 0:
            return ''
        if roll == -1:
            roll = rand.randrange(length) + 1
        table = databaseManager().metadata_obj.tables['universe.TableLines']
        statement = select(table.c.Line).where(table.c.Node == self.uuid).where(table.c.SubTableName == t).where(table.c.Roll >= roll).order_by(table.c.Roll)
        with orm.Session(databaseManager().engine) as session:
            row = session.execute(statement).first()
            retVal = row[0]
            session.close()
        if self.getType(t) == 'csv':
            l = retVal.split(',')
            if len(l) < (column + 1):
                retVal = ''
            else:
                retVal = l[column].strip()
        return retVal
        print('Error: *** No [' + t + '] Table from [' + self.node.name + '] ***')
        return ''
    def autorunStart(self):
        s = ''
        for t in self.tables:
            s = s + '<b>' + t + ': </b><br>'
            s = s + self.run(t) + '<br><br>'
        return s
    def get_random_index(self, t='Start'):
        if t in self.length:
            return rand.randrange(self.length[t]) + 1
        return -1

class tableFile(tableGroup):
    comment = re.compile(r'^\s*#.*$')
    whitespace = re.compile(r'^\s*$')
    tabledeclaration = re.compile(r'^\s*:([!,/\'\w \+-]*)$')
    tabledeclarationalt = re.compile(r'^\s*;([!,/\'\w \+-]*)$')
    tabledeclarationcsv = re.compile(r'^\s*@([!,/\'\w \+-]*)$')
    # veritcal |
    # horizontal -
    # action *
    tableline = re.compile(r'^\s*(\d*)\s*,(.*)')
    tablelinealt = re.compile(r'^\s*(\d*)-(\d*)\s*,(.*)')
    continuation = re.compile(r'^_(.*)$')
    variabledeclarationAlt = re.compile(r'^\s*%%(.*)%%\s*=\s*(.*)$')
    variabledeclaration = re.compile(r'^\s*<<(.*)>>\s*=\s*(.*)$')
    parameterdeclaration = re.compile(r'^\s*@.*$')
    pragmadeclaration = re.compile(r'^\.(.*)\:(.*)$')
    namespec = re.compile(r'^[/\w _~,-]*/(.*)\.tab$')
    filename = ''
    def __init__(self, filename, node : tableNode):
        tableGroup.__init__(self, node)
        self.table = dict()
        self.pragmas = dict()
        self.filename = filename
        self.tablename = ''
        current = ''
        previous = ''
        m = self.namespec.match(filename)
        if m:
            self.name = m.group(1)
            for l in codecs.open(filename, 'r', "utf-8"):
                current = l.strip()
                m7 = self.continuation.match(current)
                if m7:
                    x = m7.group(1)
                    previous = previous + ' ' + x
                    continue
                self.addTableLine(previous)
                previous = current
            self.addTableLine(previous)
    def addTableLine(self, line):
        if self.comment.match(line): #comment
            pass
        elif self.whitespace.match(line):
            pass
        elif m := self.tabledeclaration.match(line):
            self.tablename = m.group(1)
            self.table[self.tablename] = SubTable(self.tablename, True)
        elif m := self.tabledeclarationalt.match(line):
            self.tablename = m.group(1)
            self.table[self.tablename] = SubTable(self.tablename, False)
        elif m := self.tabledeclarationcsv.match(line):
            self.tablename = m.group(1)
            self.table[self.tablename] = SubTable(self.tablename, True, True)
        elif m := self.tableline.match(line):
            self.table[self.tablename].add(int(m.group(1)), m.group(2))
        elif m := self.tablelinealt.match(line):
            d = int(m.group(2))
            self.table[self.tablename].add(d, m.group(3))
        elif m := self.variabledeclaration.match(line):
            self.variableManager.setBaseVariable(self.node, m.group(1), m.group(2))
        elif m := self.variabledeclarationAlt.match(line):
            self.variableManager.setBaseVariable(self.node, m.group(1), m.group(2))
        elif m := self.parameterdeclaration.match(line):
            pass
        elif m := self.pragmadeclaration.match(line):
            self.pragmas[m.group(1)] = m.group(2)
        else:
            print('Error: unidentified line ' + self.filename + ' - ' + line)
    def pragma(self, pragma):
        if pragma in self.pragmas:
            return self.pragmas[pragma]
        return None
    def run(self, t='Start', roll=-1, column=0):
        t = t.strip()
        if self.table.get(t):
            return self.table[t].roll(column=column, roll=roll)
        elif t == 'Start':
            return self.autorunStart()
        print('Error: *** No [' + t + '] Table from [' + self.node.name + '] ***')
        return ''
    def autorunStart(self):
        s = ''
        for t in self.table:
            s = s + '<b>' + t + ': </b><br>'
            s = s + self.table[t].roll() + '<br><br>'
        return s
    def get_random_index(self, t='Start'):
        if self.table.get(t):
            return self.table[t].get_random_index()
        return -1
    def getCount(self, t='Start'):
        if self.table.get(t):
            return self.table[t].getCount()
        return 0
    def getLines(self, s='Start'):
        retval = list()
        for i in self.table[s].values:
                l = list()
                if self.table[s].csvflag:
                    l.append(i)
                    tmp = self.table[s].values[i]
                    t = list()
                    for e in tmp:
                        t.append(e.strip())
                    l.append(t)
                else:
                    l.append(i)
                    l.append(self.table[s].values[i])
                retval.append(l)
        return retval

