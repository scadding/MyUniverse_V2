#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
from src.Generators.tablegen import tableFunctions
import pyparsing
from src.Generators.tablegen.tableNode import tableNode

class parseManager(object):
    def __init__(self):
        pass
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
            found, ret = self.expandTableAlt(node, ret)
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
        nestedItems = self.nestedExpr("[[", "]]")
        for t, s, e in nestedItems.scanString(text):
            n = n + text[last:s]
            last = e
            for i in t:
                l = self.parseList(i, start='[[', finish=']]')
                c = self.parseTable(node, self.parse(node, l[0]))
                n = n + c
                found = True
        ret = n + text[last:]
        return found, ret
    def expandTableAlt(self, node, text):
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
    def parseVariable(self, node : tableNode, exp):
        # parse args
        # get node
        tablenode = node
        exp = self.parse(tablenode, exp)
        path, sub = self.parseSubAndPath(tablenode, exp)
        if path:
            node = tablenode.pathToNode(path)
        n = self.getVariable(tablenode, sub)
        if n == "":
            # initialize variable
            n = self.parse(tablenode, self.getBaseVariable(tablenode, sub))
            self.setVariable(tablenode, sub, n)
        return n
    def getArguments(self, node, exp, args):
        # table args
        at_arg = re.compile(r'(.*)@([0-9]+)(.*)')
        par_arg = re.compile(r'(.*)\((.*?)\)(.*)')
        # capture and remove arguments
        m = par_arg.match(exp)
        if m:
            exp = m.group(1) + m.group(3)
            args['()'] = int(m.group(2))
        m = at_arg.match(exp)
        if m:
            exp = m.group(1) + m.group(3)
            args['@'] = int(self.parse(node, m.group(2)))
        return exp
    def getSubAndNode(self, node, exp):
        # subtable
        subtable = re.compile(r'([\w -\.]+)\.([\w -]+)$')
        single = re.compile(r'([\w -]+)$')
        # local subtable
        m = single.match(exp)
        if m:
            sub = m.group(1)
            return sub, node
        # subtable
        m = subtable.match(exp)
        if m:
            exp = m.group(1)
            sub = m.group(2)
        target = node.pathToNode(exp)
        if target is not None:
            if not target.loaded:
                self.loadtable(target)
            return sub, target
        message = "bad table - '%s' in '%s'" % (exp, node.name)
        print(message)
        raise Exception("bad table")
    def parseTable(self, node, exp):
        args = dict()
        args['@'] = 0
        args['()'] = -1
        exp = self.getArguments(node, exp, args)
        column = args['@']
        roll = args['()']
        sub, node = self.getSubAndNode(node, exp)
        return self.parse(node, node.table.run(sub, roll, column))
        raise Exception('bad table')
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
            for x in range(start, stop + 1):
                self.setVariable(node, n[0], str(x))
                s = s + self.parse(node, n[3])           
        elif f == "ifstr":
            logic = self.parse(node, n[0]).strip()
            l = [char for char in logic]
            for i in range(len(l)):
                if l[i] == '=' and l[i + 1] == '=':
                    s1 = ''.join(l[:i]).strip()
                    s2 = ''.join(l[i+2:]).strip()
                    if s1 == s2:
                        s = s + self.parse(node, n[1])
                elif l[i] == '!' and l[i + 1] == '=':
                    s1 = ''.join(l[:i]).strip()
                    s2 = ''.join(l[i+2:]).strip()
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
            self.setVariable(node, variable, value)
        elif f == "state":
            path = self.parse(node, n[0])
            name = self.parse(node, n[1])
            self.saveState(node, path, name)
        elif f == "table":
            tableName = self.parse(node, n[0])
            highroll = self.parse(node, n[1])
            sub, tnode = self.getSubAndNode(node, tableName)
            index = tnode.table.getCount(sub)
            self.setVariable(node, highroll, str(index))
            s = s + str(index)
        elif f == "find":
            tableName = self.parse(node, n[0])
            column = int(self.parse(node, n[1]))
            value = self.parse(node, n[2]).strip()
            retcol = int(self.parse(node, n[3]))
            sub, tnode = self.getSubAndNode(node, tableName)
            for line in tnode.table.getLines(sub):
                if line[1][column] == value:
                    return line[1][retcol].strip()
        else:
            p = list()
            for i in n:
                p.append(self.parse(node, i))
            s = s + getattr(tableFunctions, f)(p)
        return s
