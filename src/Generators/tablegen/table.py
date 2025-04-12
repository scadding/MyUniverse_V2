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


def walktree(top, callback, load=False, node=None):
    ignoredir = ("__pycache__")
    if node is None:
        node = Node("Root")
    for filename in os.listdir(top):
        pathname = os.path.join(top, filename)
        mode = os.stat(pathname).st_mode
        root, ext = os.path.splitext(filename)
        head, tail = os.path.split(filename)
        if S_ISDIR(mode):
            # It's a directory, recurse into it
            if tail in ignoredir:
                continue
            previous = node
            node = Node(tail, parent=previous, table=None)
            walktree(pathname, callback, load, node=node)
            node = previous
        elif S_ISREG(mode):
            # It's a file, call the callback function
            table = callback(pathname, load)
            if callback(pathname, load):
                Node(root, parent=node, table=table, loaded=load, filename=pathname)
        else:
            # Unknown file type, print a message
            print('Skipping %s' % pathname)
    return node


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
    

class tableVariable(object):
    def __init__(self):
        pass

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

class tableVariableNode(tableVariable, tableNode):
    def __init__(self, name, parent=None, children=None):
        super().__init__()
        self.name = name
        self.parent = parent
        if children:
            self.children = children

class tableGroup(object):
    currentstack = dict()
    def __init__(self):
        self.stack = dict()
        self.currentstack = dict()
    def getBaseVariable(self, var):
        if var in self.stack:
            return self.stack[var]
        return ""
    def getVariable(self, var):
        if var in self.currentstack:
            return self.currentstack[var]
        return ""
    def setVariable(self, var, val):
        self.currentstack[var] = val
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
            self.stack[var] = value
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
    variabledeclaration = re.compile(r'^\s*%%(.*)%%\s*=\s*(.*)$')
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
            self.stack[m8.group(1)] = m8.group(2)
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

class tableMgr(object):
    ignoredir = ["__pycache__"]
    ignoreext = ['.tml']
    tree : tableNode
    variables : tableVariableNode
    globals : tableVariableNode
    state : tableVariableNode
    def __init__(self):
        self.tree = tableNode("Root")
        self.variables = tableVariableNode("Variables")
        self.globals = tableVariableNode("Globals", parent=self.variables)
        self.state = tableVariableNode("State", parent=self.variables)
        config = Configuration()
        self.walktree(config.getValue("Data", "directory"), load=True, node=self.tree)
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
        extension = os.path.splitext(node.filename)[1]
        if extension == '.tab' or extension == '.tml':
            node.table = tableFile(node.filename)
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
        if not node.table:
            self.loadtable(node)
    def nestedExpr(self, opener, closer):
        content = (pyparsing.Combine(pyparsing.OneOrMore(
            ~pyparsing.Literal(opener) +
            ~pyparsing.Literal(closer) + pyparsing.CharsNotIn('\n\r', exact=1))
                                    ).setParseAction(lambda t: t[0].strip()))
        ret = pyparsing.Forward()
        ret <<= pyparsing.Group(pyparsing.Suppress(opener) +
                                pyparsing.ZeroOrMore(ret | content) + pyparsing.Suppress(closer))
        return ret
    def parse(self, node, exp):
        found = True
        ret = exp
        while found:
            found, ret = self.expandFunction(node, ret)
            if found:
                continue
            found, ret = self.expandTable(node, ret)
            if found:
                continue
            found, ret = self.expandTemplate(node, ret)
            if found:
                continue
            found, ret = self.expandVariable(node, ret)
        return ret
    def expandFunction(self, node, text):
        ret = ''
        last = 0
        found = False
        nestedItems = self.nestedExpr("{{", "}}")
        for t, s, e in nestedItems.scanString(text):
            ret = ret + text[last:s]
            last = e
            for i in t:
                ret = ret + self.handleBrace(node, i)
                found = True
        ret = ret + text[last:]
        return found, ret
    def expandTable(self, node, text):
        last = 0
        n = ''
        found = False
        nestedItems = self.nestedExpr("[", "]")
        for t, s, e in nestedItems.scanString(text):
            n = n + text[last:s]
            last = e
            for i in t:
                l = self.parseList(i, start='[', finish=']')
                c = self.parseTable(node, self.parse(node, l[0]))
                n = n + c
                found = True
        ret = n + text[last:]
        return found, ret
    def expandTemplate(self, node, text):
        last = 0
        n = ''
        found = False
        q = pyparsing.QuotedString('@@', multiline=False, unquoteResults=True, endQuoteChar='@@')
        for t, s, e in q.scanString(text):
            n = n + text[last:s]
            last = e
            node = self.parseTemplate(node, t[0])
            if node:
                for l in open(node.filename):
                    n = n + l
                found = True
        ret = n + text[last:]
        return found, ret
    def expandVariable(self, node, text):
        last = 0
        n = ''
        found = False
        q = pyparsing.QuotedString('%%', multiline=False, unquoteResults=True, endQuoteChar='%%')
        for t, s, e in q.scanString(text):
            n = n + text[last:s]
            last = e
            if node.table.getVariable(t[0]) == "":
                v = node.table.getBaseVariable(t[0])
                node.table.setVariable(t[0], self.parse(node, v))
            n = n + node.table.getVariable(t[0])
            found = True
        ret = n + text[last:]
        return found, ret
    def parseTemplate(self, node, exp, type='tml'):
        return node.pathToNode(exp, type)
    def parseTable(self, node, exp):
        roll = -1
        column = 0
        # subtable
        subtable = re.compile(r'([\w -\.]+)\.([\w -]+)$')
        single = re.compile(r'([\w -]+)$')
        # table args
        column_arg = re.compile(r'(.*)@([0-9]+)(.*)')
        roll_arg = re.compile(r'(.*)\((.*?)\)(.*)')

        # capture and remove arguments
        m = column_arg.match(exp)
        if m:
            exp = m.group(1) + m.group(3)
            column = int(m.group(2))
        m = roll_arg.match(exp)
        if m:
            exp = m.group(1) + m.group(3)
            roll = int(self.parse(node, m.group(2)))
        # local subtable
        m = single.match(exp)
        if m:
            sub = m.group(1)
            return self.parse(node, node.table.run(sub, roll, column))
        # subtable
        m = subtable.match(exp)
        if m:
            exp = m.group(1)
            sub = m.group(2)
        node = node.pathToNode(exp)
        if node is not None:
            return self.parse(node, node.table.run(sub, roll, column))
        return ''
    def setTree(self, node):
        self.tree = node
    def parseList(self, l, start='{{', finish='}}'):
        n = None
        for i in l:
            if i.__class__.__name__ == 'ParseResults':
                s = start + self.listToString(i) + finish
                if n == None:
                    n = list()
                    n.append(s)
                else:
                    n[-1] = n[-1] + s
            else:
                t = i.rsplit(',')
                if n == None:
                    n = t
                else:
                    n[-1] = n[-1] + t[0]
                    n.extend(t[1:])
        return n
    def listToString(self, l):
        s = ''
        for i in l:
            if i.__class__.__name__ == 'ParseResults':
                s = '{{' + self.listToString(i) + '}}'
            else:
                s = s + i
        return s
    def handleBrace(self, node, l):
        n = list()
        s = ''
        r1 = re.compile(r'(.*?)(\:|[|]|~)(.*)')
        m = r1.match(l[0])
        if m == None:
            print('malformed function')
            return ''
        f = m.group(1)
        l[0] = m.group(3)
        n = self.parseList(l)
        if f == "for":
            variable = self.parse(node, n[0])
            start = int(self.parse(node, n[1]))
            stop = int(self.parse(node, n[2]))
            for x in range(start, stop):
                node.table.setVariable(n[0], str(x))
                s = s + self.parse(node, n[3])           
        elif f == "ifstr":
            logic = self.parse(node, n[0]).lstrip().rstrip()
            l = [char for char in logic]
            for i in range(len(l)):
                if l[i] == '=' and l[i + 1] == '=':
                    s1 = ''.join(l[:i]).lstrip().rstrip()
                    s2 = ''.join(l[i+2:]).lstrip().rstrip()
                    if s1 == s2:
                        s = s + self.parse(node, n[1])
                elif l[i] == '!' and l[i + 1] == '=':
                    s1 = ''.join(l[:i]).lstrip().rstrip()
                    s2 = ''.join(l[i+2:]).lstrip().rstrip()
                    if s1 != s2:
                        s = s + self.parse(node, n[1])
        elif f == "if":
            logic = list()
            logic.append(self.parse(node, n[0]))
            if tableFunctions.eval(logic) == "True":
                s = s + self.parse(node, n[1])
        elif f == "assign":
            variable = self.parse(node, n[0])
            value = self.parse(node, n[1])
            node.table.setVariable(variable, value)
        else:
            p = list()
            for i in n:
                p.append(self.parse(node, i))
            s = s + getattr(tableFunctions, f)(p)
        return s
    def roll(self, node):
        if type(node) != tableNode:
            raise TypeError
        self.checkload(node)

        # make the variable node

        # set default values
        
        s = node.table.start()
        s = self.parse(node, s)
        return s
    def run(self, node, sub='Start', roll=-1, column=0):
        self.checkload(node)
        s = node.table.run(sub, roll, column)
        s = self.parse(node, s)
        return s
    def rundict(self, node, sub, roll=-1):
        self.checkload(node)
        s = node.table.rundict(sub, roll)
        return s
    def get_random_index(self, node, sub="Start"):
        self.checkload(node)
        return node.table.get_random_index(sub)
    def getCount(self, node, sub="Start"):
        self.checkload(node)
        return node.table.getCount(sub)

class testMgr(tableMgr):
    def __init__(self):
        super().__init__()
    def test(self, count=100, dirname='./test', table=''):
        d = os.path.dirname(dirname)
        if not os.path.exists(dirname):
            os.makedirs(dirname)
        if table == '':
            for t in self.tfile:
                #print("table =", t)
                filename = dirname + '/' + t + '.txt'
                f = None
                for j in range(count):
                    s = self.roll(t)
                    #print('result - ' + s)
                    if s == '':
                        continue
                    if f == None:
                        f = codecs.open(filename, 'w', "utf-8")
                    f.write(s + '\n')
        else:
            #print 'table - ' + table
            filename = dirname + '/' + table + '.txt'
            f = None
            for j in range(count):
                s = self.roll(table)
                if s == '':
                    continue
                if f == None:
                    f = open(filename, 'w')
                f.write(s + '\n')
    def importTables(self):
        con = lite.connect('test.db')
        cur = con.cursor()
        cur.execute("DROP TABLE IF EXISTS Objects")
        cur.execute("DROP TABLE IF EXISTS Variables")
        cur.execute("DROP TABLE IF EXISTS TableVariables")
        cur.execute("DROP TABLE IF EXISTS TableLines")
        cur.execute("DROP TABLE IF EXISTS Tables")

        cur.execute("CREATE TABLE Objects(Id INTEGER PRIMARY KEY, Name TEXT, Type TEXT)")
        cur.execute("CREATE TABLE Variables(Id INTEGER PRIMARY KEY, Object TEXT, Name TEXT, Value TEXT)")
        cur.execute("CREATE TABLE TableVariables(TableName TEXT, Name TEXT, Value TEXT)")
        cur.execute("CREATE TABLE TableLines(TableName TEXT, SubTableName TEXT, Roll INT, Line TEXT)")
        cur.execute("CREATE TABLE Tables(Genre TEXT, TableName TEXT, SubTableName TEXT, Type TEXT, Length INT)")
        #cur.execute("CREATE TABLE Tables(TableName TEXT, SubTableName TEXT, Length INT)")
        #for t in self.tfile:
        #    print 'table - ' + t
        #    if self.tfilename[t][-3:] == 'tab':
        #        self.tfile[t].importTable(t, cur)
        for g in self.group:
            for t in self.group[g]:
                print(g, '-', t)
                if self.tfilename[t][-3:] == 'tab':
                    self.tfile[t].importTable(g, t, cur)
        con.commit()
    def process(self, line):
        line = line.strip()
        if line == "list groups":
            s = ''
            for g in self.group:
                s = s + g + '\n'
            return s
        elif line[0:4] == 'list':
            g = line[5:].strip()
            s = ''
            if g in self.group:
                for t in self.group[g]:
                    s = s + t + '\n'
            else:
                s = 'No such group: ' + g + '\n'
            return s
        else:
            if line in self.tfile:
                return self.roll(line) + '\n'
            else:
                return 'unknown table\n'


def testcallback(option, opt, value, parser, *args, **kwargs):
    t.test()
    sys.exit

def importcallback(option, opt, value, parser, *args, **kwargs):
    #print option
    #print opt
    #print value
    #print parser.largs
    #print parser.rargs
    #print parser.values
    #print args
    #print kwargs
    print(parser.values.datadir)
    t = testMgr()
    walktree(parser.values.datadir, t.addfile, load=True)
    t.importTables()

def allcallback(option, opt, value, parser, *args, **kwargs):
    print(parser.values.datadir)
    t = testMgr()
    walktree(parser.values.datadir, t.addfile, load=True)
    #t.importTables()
    sys.exit


def listencallback(option, opt, value, parser, *args, **kwargs):
    print(parser.values.datadir)
    t = testMgr()
    walktree(parser.values.datadir, t.addfile, load=True)
    #t.importTables()
    while True:    # infinite loop
        n = input("enter your table: ")
        if n == "Quit":
            break  # stops the loop
        print(t.process(n))

def servercallback(option, opt, value, parser, *args, **kwargs):
    server(testMgr, walktree, parser.values.datadir)

def runcallback(option, opt, value, parser, *args, **kwargs):
    print(value)
    t.test(count = 10, table = value)

def groupscallback(option, opt, value, parser, *args, **kwargs):
    for g in t.groups():
        print(g)

def tablescallback(option, opt, value, parser, *args, **kwargs):
    print(value)
    for table in t.group[value]:
        print("\t" + table)

def datacallback(option, opt, value, parser, *args, **kwargs):
    walktree(value, t.addfile, load=True)


if __name__ == '__main__':
    t = testMgr()
    parser = OptionParser()
    parser.add_option("-d", "--data", type="string", dest="datadir", action="callback",
                      help="Data Directory", metavar="Data", default="Data", callback=datacallback)
    parser.add_option("-a", "--all", action="callback", callback=allcallback)
    parser.add_option("", "--test", action="callback", callback=testcallback)
    parser.add_option("-i", "--import", action="callback", callback=importcallback)
    parser.add_option("-l", "--listen", action="callback", callback=listencallback)
    parser.add_option("-s", "--server", action="callback", callback=servercallback)

    parser.add_option("-t", "--table", type="string", dest="table",
                      help="Table Name", metavar="Table", default="")
    parser.add_option("-g", "--group", type="string", dest="group",
                      help="Group Name", metavar="Group", default="junk")

    parser.add_option("-r", "--run", action="callback", callback=runcallback, type="string", default=None)
    parser.add_option("", "--groups", action="callback", callback=groupscallback)
    parser.add_option("", "--tables", action="callback", type="string", default=None, callback=tablescallback)

    (options, args) = parser.parse_args()

