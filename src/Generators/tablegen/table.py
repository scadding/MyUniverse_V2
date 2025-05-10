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

from anytree import Node, RenderTree, AsciiStyle, LevelOrderIter, NodeMixin

class Table(object):
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
    def __init__(self, tm, node):
        self.tm = tm
        self.node = node
    def start(self):
        return self.run('Start')


class tableDB(tableGroup):
    def __init__(self, node : tableNode, tm):
        tableGroup.__init__(self, tm, node)
        self.uuid = node.uuid
        self.count = dict()
        self.type = dict()
        self.tables = list()
        self.loadVariables()
        self.getMetaData()
    def getMetaData(self):
        table = self.tm.metadata_obj.tables['universe.Tables']
        statement = select(table.c.SubTableName, table.c.Type, table.c.Length).where(table.c.Node == self.uuid)
        with orm.Session(self.tm.engine) as session:
            for row in session.execute(statement):
                self.tables.append(row[0])
                self.type[row[0]] = row[1]
                self.count[row[0]] = row[2]
            session.close()
    def loadVariables(self):
        table = self.tm.metadata_obj.tables['universe.TableVariables']
        statement = select(table.c.Name, table.c.Value).where(table.c.Node == self.uuid)
        with orm.Session(self.tm.engine) as session:
            for row in session.execute(statement):
                self.tm.setBaseVariable(self.node, row[0], row[1])
            session.close()
    def getType(self, t):
        return self.type[t]
    def getCount(self, t):
        return self.count[t]
    def getLines(self, t='Start'):
        retval = list()
        table = self.tm.metadata_obj.tables['universe.TableLines']
        statement = select(table.c.Roll, table.c.Line).where(table.c.Node == self.uuid).where(table.c.SubTableName == t).order_by(table.c.Roll)
        isCsv = self.getType(t)
        with orm.Session(self.tm.engine) as session:
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
        if t not in self.tables:
            return self.autorunStart()
        retVal = u''
        length = self.getCount(t)
        if length == 0:
            return ''
        if roll == -1:
            roll = rand.randrange(length) + 1
        table = self.tm.metadata_obj.tables['universe.TableLines']
        statement = select(table.c.Line).where(table.c.Node == self.uuid).where(table.c.SubTableName == t).where(table.c.Roll >= roll).order_by(table.c.Roll)
        with orm.Session(self.tm.engine) as session:
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
        print('Error: *** No [' + t + '] Table***', file=sys.stderr)
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
    tableline = re.compile(r'^\s*(\d*)\s*,(.*)')
    tablelinealt = re.compile(r'^\s*(\d*)-(\d*)\s*,(.*)')
    continuation = re.compile(r'^_(.*)$')
    variabledeclarationAlt = re.compile(r'^\s*%%(.*)%%\s*=\s*(.*)$')
    variabledeclaration = re.compile(r'^\s*<<(.*)>>\s*=\s*(.*)$')
    parameterdeclaration = re.compile(r'^\s*@.*$')
    pragmadeclaration = re.compile(r'^/.*$')
    namespec = re.compile(r'^[/\w _~,-]*/(.*)\.tab$')
    filename = ''
    def __init__(self, filename, tm, node):
        tableGroup.__init__(self, tm, node)
        self.table = dict()
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
        m1 = self.comment.match(line)
        m2 = self.whitespace.match(line)
        m3 = self.tabledeclaration.match(line)
        m4 = self.tabledeclarationalt.match(line)
        m5 = self.tabledeclarationcsv.match(line)
        m6 = self.tableline.match(line)
        m7 = self.tablelinealt.match(line)
        m8 = self.variabledeclaration.match(line)
        m8a = self.variabledeclarationAlt.match(line)
        m9 = self.parameterdeclaration.match(line)
        m10 = self.pragmadeclaration.match(line)
        if m1: #comment
            pass
        elif m2: #whitespace
            pass
        elif m3: # Table declaration
            self.tablename = m3.group(1)
            self.table[self.tablename] = Table(self.tablename, True)
        elif m4: # Alternate Table Declaration
            self.tablename = m4.group(1)
            self.table[self.tablename] = Table(self.tablename, False)
        elif m5: # Csv table declaration
            self.tablename = m5.group(1)
            self.table[self.tablename] = Table(self.tablename, True, True)
        elif m6: #table line
            self.table[self.tablename].add(int(m6.group(1)), m6.group(2))
        elif m7: #alternate table line
            d = int(m7.group(2))
            self.table[self.tablename].add(d, m7.group(3))
        elif m8: # variable declaration
            self.tm.setBaseVariable(self.node, m8.group(1), m8.group(2))
        elif m8a: # variable declaration
            self.tm.setBaseVariable(self.node, m8a.group(1), m8a.group(2))
        elif m9: #parameter declaration
            pass
        elif m10: #pragma declaration
            pass
        else:
            print('Error: unidentified line ' + self.filename + ' - ' + line)
    def run(self, t='Start', roll=-1, column=0):
        if self.table.get(t):
            return self.table[t].roll(column=column, roll=roll)
        elif t == 'Start':
            return self.autorunStart()
        print('Error: *** No [' + t + '] Table***', file=sys.stderr)
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

