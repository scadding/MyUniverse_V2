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
from src.Generators.tablegen.server import server
from src.Configuration import Configuration

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
    def getvaluedict(self, index):
        if index > self.index:
            return 'Error: Out of Range'
        d = index
        while self.values.get(d) is None:
            d = d + 1
        return self.values[d]
    def rolldict(self, roll=-1):
        if self.index == 0:
            return ''
        if roll == -1:
            roll = self.get_random_index()
        return self.getvaluedict(roll)
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
    

class tableNode(NodeMixin):
    def __init__(self, name, parent=None, children=None, **kwargs):
        self.__dict__.update(kwargs)
        self.name = name
        self.parent = parent
        if children:
            self.children = children
    def getNode(self, name, type=None):
        parent = self
        for c in parent.children:
            if c.name == name:
                if type:
                    if type == c.type:
                        return c
                else:
                    return c
        raise TypeError
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

class tableGroup(object):
    currentstack = dict()
    def __init__(self):
        self.stack = dict()
        self.currentstack = dict()
    def getBaseVariable(self, var):
        if var in self.stack:
            return self.stack[var]
        raise TypeError
        return ""
    def getVariable(self, var):
        if var in self.currentstack:
            return self.currentstack[var]
        return ""
    def setVariable(self, var, val):
        self.currentstack[var] = val
    def setBaseVariable(self, var, val):
        self.stack[var] = val
    def removeVariable(self, var, val):
        del self.currentstack[var]
    def start(self):
        self.currentstack = dict()
        return self.run('Start')

class tableDB(tableGroup):
    def __init__(self, table, genre, con):
        self.con = con
        self.table = table
        self.genre = genre
        cur = con.cursor()
        cur.execute("SELECT SubTableName, Type, Length FROM Tables WHERE " +
                    "TableName == \"%s\"" % (table))
        self.length = dict()
        self.type = dict()
        for sub, t, l in cur.fetchall():
            self.length[sub] = l
            self.type[sub] = t
    def start(self):
        self.loadVariables()
        return self.run()
    def loadVariables(self):
        cur = self.con.cursor()
        cur.execute("SELECT Name, Value FROM TableVariables WHERE TableName == \"%s\"" % self.table)
        for var, value in cur.fetchall():
            self.currentstack[var] = value
            self.setBaseVariable(var, value)
    def run(self, t='Start', roll=-1, column=0):
        retVal = u''
        if t in self.length:
            if self.length[t] == 0:
                return ''
            if roll == -1:
                roll = self.get_random_index(t)
            cur = self.con.cursor()
            cur.execute("select Line from TableLines where TableName == \"%s\" and SubTableName == \"%s\" and Roll >= %d ORDER BY Roll Limit 1" % (self.table, t, roll))
            for Line in cur.fetchall():
                retVal = Line[0]
            if self.type[t] == 'csv':
                l = retVal.split(',')
                if len(l) < (column + 1):
                    retVal = ''
                else:
                    retVal = l[column].strip()
            return retVal
        print('Error: *** No [' + t + '] Table***', file=sys.stderr)
        return ''
    def get_random_index(self, t='Start'):
        if t in self.length:
            #print 'length -', self.table, '-', t, '-', self.length[t]
            return rand.randrange(self.length[t]) + 1
        return -1
    def getCount(self, t='Start'):
        if t in self.length:
            return self.length[t]
        return 0

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
    def __init__(self, filename):
        tableGroup.__init__(self)
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
            self.setBaseVariable(m8.group(1), m8.group(2))
        elif m8a: # variable declaration
            self.setBaseVariable(m8a.group(1), m8a.group(2))
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
    def rundict(self, t='Start', roll=-1):
        if self.table.get(t):
            return self.table[t].rolldict(roll=roll)
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
    def importTable(self, genre, table, cur):
        for i in self.table:
            Type = 'table'
            if self.table[i].csvflag:
                Type = 'csv'
            cur.execute("INSERT INTO Tables VALUES('%s', '%s', '%s', '%s', %d)" % (genre, table, i, Type, self.table[i].getCount()))
            for j in self.table[i].values:
                value = ''
                index = 0
                if self.table[i].values[j].__class__.__name__ == 'dict':
                    for k in self.table[i].values[j]:
                        if index > 0:
                            value = value + ', '
                        value = value + self.table[i].values[j][k]
                        index = index + 1
                        value = value.replace('"', '\'')
                elif self.table[i].values[j].__class__.__name__ == 'list':
                    for k in self.table[i].values[j]:
                        if index > 0:
                            value = value + ', '
                        value = value + k
                        index = index + 1
                        value = value.replace('"', '\'')
                else:
                    print(self.table[i].values[j].__class__.__name__)
                cur.execute("INSERT INTO TableLines VALUES(\"%s\", \"%s\", %d, \"%s\")" % (table, i, j, value))
        for k in self.stack:
            print('variable', k, self.stack[k])
            value = self.stack[k].replace('"', '\'')
            cur.execute("INSERT INTO TableVariables VALUES(\"%s\", \"%s\", \"%s\")" % (table, k, value))


