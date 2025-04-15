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
from src.Generators.tablegen.table import tableNode, tableFile, tableDB
from src.Generators.tablegen.tableVariable import tableVariableNode
from src.Configuration import Configuration

from anytree import Node, RenderTree, AsciiStyle, LevelOrderIter, NodeMixin

class tableMgr(object):
    ignoredir = ["__pycache__"]
    ignoreext = ['.tml']
    tree : tableNode
    variables : tableVariableNode
    globals : tableVariableNode
    state : tableVariableNode
    current : tableVariableNode
    config : Configuration
    def __init__(self):
        self.tree = tableNode("Root")
        self.variables = tableVariableNode("Variables")
        self.globals = tableVariableNode("Globals", parent=self.variables)
        self.state = tableVariableNode("State", parent=self.variables)
        self.current = tableVariableNode("Current", parent=self.variables)
        self.config = Configuration()
        self.walktree(self.config.getValue("Data", "directory"), load=False, node=self.tree)
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
        if not node.loaded:
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
            if found:
                continue
            found, ret = self.expandVariableAlt(node, ret)
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
    def expandVariable(self, node, text):
        last = 0
        n = ''
        found = False
        q = pyparsing.QuotedString('<<', multiline=False, unquoteResults=True, endQuoteChar='>>')
        for t, s, e in q.scanString(text):
            n = n + text[last:s]
            last = e
            n = n + self.parseVariable(node, t[0])
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
    def expandVariableAlt(self, node, text):
        last = 0
        n = ''
        found = False
        q = pyparsing.QuotedString('%%', multiline=False, unquoteResults=True, endQuoteChar='%%')
        for t, s, e in q.scanString(text):
            n = n + text[last:s]
            last = e
            n = n + self.parseVariable(node, t[0])
            found = True
        ret = n + text[last:]
        return found, ret
    def parseTemplate(self, node, exp, type='tml'):
        return node.pathToNode(exp, type)
    def parseSubAndPath(self, node, exp):
        sub = ""
        path = None
        # sub
        subelement = re.compile(r'([\w -\.]+)\.([\w -]+)$')
        single = re.compile(r'([\w -]+)$')

        # local subtable
        m = single.match(exp)
        if m:
            sub = m.group(1)
            return path, sub
        # subtable
        m = subelement.match(exp)
        if m:
            path = m.group(1)
            sub = m.group(2)
        return path, sub
    def parseVariable(self, node, exp):
        # parse args

        # get node

        tablenode = node
        exp = self.parse(tablenode, exp)
        path, sub = self.parseSubAndPath(tablenode, exp)

        if path:
            node = tablenode.pathToNode(path)

        n = self.current.getVariable(sub)
        if n == "":
            # initialize variable
            n = self.parse(tablenode, tablenode.table.getBaseVariable(sub))
            self.current.setVariable(sub, n)
        return n
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
            if not node.loaded:
                self.loadtable(node)
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
                self.current.setVariable(n[0], str(x))
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
            self.current.setVariable(variable, self.parse(node, value))
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
        
        s = node.table.start()
        s = self.parse(node, s)
        self.current.clearVariables()
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
    
