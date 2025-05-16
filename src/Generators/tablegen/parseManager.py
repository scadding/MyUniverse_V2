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
    def prepareParsing(self):
        self.myParseDict = dict()
        self.myParseDict['function'] = dict()
        self.myParseDict['function']['start'] = '{{'
        self.myParseDict['function']['end'] = '}}'
        self.myParseDict['function']['parse'] = False
        self.myParseDict['function']['handler'] = self.parseFunction
        self.myParseDict['table'] = dict()
        self.myParseDict['table']['start'] = '[['
        self.myParseDict['table']['end'] = ']]'
        self.myParseDict['table']['parse'] = True
        self.myParseDict['table']['handler'] = self.parseTable
        self.myParseDict['template'] = dict()
        self.myParseDict['template']['start'] = '@@'
        self.myParseDict['template']['end'] = '@@'
        self.myParseDict['template']['parse'] = True
        self.myParseDict['template']['handler'] = self.parseTemplate
        self.myParseDict['variable'] = dict()
        self.myParseDict['variable']['start'] = '<<'
        self.myParseDict['variable']['end'] = '>>'
        self.myParseDict['variable']['parse'] = True
        self.myParseDict['variable']['handler'] = self.parseVariable
        self.myParseDict['variableAlt'] = dict()
        self.myParseDict['variableAlt']['start'] = '%%'
        self.myParseDict['variableAlt']['end'] = '%%'
        self.myParseDict['variableAlt']['parse'] = True
        self.myParseDict['variableAlt']['handler'] = self.parseVariable
        for p in self.myParseDict:
            if self.myParseDict[p]['start'] != self.myParseDict[p]['end']:
                self.myParseDict[p]['isNested'] = True
                self.myParseDict[p]['parser'] = self.nestedExpr(self.myParseDict[p]['start'], self.myParseDict[p]['end'])
            else:
                self.myParseDict[p]['isNested'] = False
                self.myParseDict[p]['parser'] = pyparsing.QuotedString(self.myParseDict[p]['start'],
                                                                       multiline=False, unquoteResults=True,
                                                                       endQuoteChar=self.myParseDict[p]['end']
                                                                       )
    def parse(self, node : tableNode, text):
        self.level += 1
        indent = '  ' * self.level
        exp = text
        lParser = None
        while len(exp):
            index = len(exp)
            for p in self.myParseDict:
                i = exp.find(self.myParseDict[p]['start'])
                if i != -1 and i < index:
                    index = i
                if i == 0:
                    if exp.find(self.myParseDict[p]['end']) == -1:
                        raise ValueError
                    lParser = p
                    break
            if index == 0:
                l = len(self.myParseDict[lParser]['start'])
                for tokens, start, end in self.myParseDict[p]['parser'].scanString(exp):
                    arguments = exp[start + l:end - l]
                    if self.myParseDict[lParser]['parse']:
                        arguments = ''
                        for atom in self.parse(node, exp[start + l:end - l]):
                            arguments = arguments + atom
                    try:
                        result = self.myParseDict[lParser]['handler'](node, arguments)
                        exp = result + exp[end:]
                    except:
                        exp = ''
                        raise
                    if exp == text:
                        raise ValueError
                    break
            else:
                retVal = exp[:index]
                exp = exp[index:]
                yield retVal
        self.level -= 1
    def parseSingle(self, node : tableNode, exp):
        retval = ''
        for s in self.parse(node, exp):
            retval = retval + s
        return retval
    def parseTemplate(self, node : tableNode, exp, type='tml'):
        tnode = node.pathToNode(exp, type)
        retval = ''
        if tnode:
            for line in open(tnode.filename):
                retval = retval + line
        else:
            print("unkonwn template - %s in [%s]" % (exp, node.name))
        return retval
    def parseSubAndPath(self, node : tableNode, exp):
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
    def parseVariable(self, node : tableNode, text):
        exp = text
        # parse args
        # get node
        tablenode = node
        exp = self.parseSingle(tablenode, exp)
        path, sub = self.parseSubAndPath(tablenode, exp)
        if path:
            node = tablenode.pathToNode(path)
        n = self.getVariable(tablenode, sub)
        if n == "":
            # initialize variable
            n = self.parseSingle(tablenode, self.getBaseVariable(tablenode, sub))
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
            args['@'] = int(self.parseSingle(node, m.group(2)))
        return exp
    def getSubAndNode(self, node, exp):
        text = exp
        # subtable
        subtable = re.compile(r'([\w \-\.]+)\.([\w \-\+]+)$')
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
        message = "bad table - '%s' in '%s'" % (text, node.name)
        print(message)
        raise Exception("bad table")
    def parseTable(self, node : tableNode, exp):
        args = dict()
        args['@'] = 0
        args['()'] = -1
        exp = self.getArguments(node, exp, args)
        column = args['@']
        roll = args['()']
        try:
            sub, node = self.getSubAndNode(node, exp)
            if sub is None or node is None or node.table is None:
                print(exp)
                return ''
        except:
            message = "bad table - '%s' in '%s'" % (exp, node.name)
            print(message)
            raise Exception('bad table')
        return self.parseSingle(node, node.table.run(sub, roll, column))
    def parseParameters(self, parameterString : str):
        parameters = list()
        remove = list()
        commas = [m.start() for m in re.finditer(',', parameterString)]
        
        for token, start, end in self.myParseDict['function']['parser'].scanString(parameterString):
            for l in commas:
                if l > start and l < end:
                    remove.append(l)
        for r in remove:
            commas.remove(r)
        start = 0
        for l in commas:
            parameters.append(parameterString[start:l].strip())
            start = l + 1
        parameters.append(parameterString[start:].strip())
        return parameters

    def parseFunction(self, node : tableNode, exp):
        r1 = re.compile(r'(.*?)(\:|[|]|~)(.*)')
        m = r1.match(exp)
        if m == None:
            print('malformed function')
            return ''
        functionName = m.group(1).strip()
        parameterString = m.group(3)
        parameters = self.parseParameters(parameterString)
        return self.callFunction(node, functionName, parameters)
    def callFunction(self, node : tableNode, functionName, parameters):
        retval = ''
        if functionName == "for":
            variable = self.parseSingle(node, parameters[0])
            start = int(self.parseSingle(node, parameters[1]))
            stop = int(self.parseSingle(node, parameters[2]))
            for x in range(start, stop + 1):
                self.setVariable(node, parameters[0], str(x))
                retval = retval + self.parseSingle(node, parameters[3])           
        elif functionName == "ifstr":
            logic = self.parseSingle(node, parameters[0]).strip()
            l = [char for char in logic]
            for i in range(len(l)):
                if l[i] == '=' and l[i + 1] == '=':
                    s1 = ''.join(l[:i]).strip()
                    s2 = ''.join(l[i+2:]).strip()
                    if s1 == s2:
                        retval = self.parseSingle(node, parameters[1])
                elif l[i] == '!' and l[i + 1] == '=':
                    s1 = ''.join(l[:i]).strip()
                    s2 = ''.join(l[i+2:]).strip()
                    if s1 != s2:
                        retval = self.parseSingle(node, parameters[1])
        elif functionName == "if":
            logic = list()
            logic.append(self.parseSingle(node, parameters[0]))
            if tableFunctions.eval(logic) == "True":
                retval = self.parseSingle(node, parameters[1])
        elif functionName == "assign":
            variable = self.parseSingle(node, parameters[0])
            value = self.parseSingle(node, parameters[1])
            self.setVariable(node, variable, value)
        elif functionName == "state":
            path = self.parseSingle(node, parameters[0])
            name = self.parseSingle(node, parameters[1])
            self.saveState(node, path, name)
        elif functionName == "table":
            tableName = self.parseSingle(node, parameters[0])
            highroll = self.parseSingle(node, parameters[1])
            sub, tnode = self.getSubAndNode(node, tableName)
            index = tnode.table.getCount(sub)
            self.setVariable(node, highroll, str(index))
            retval = str(index)
        elif functionName == "find":
            tableName = self.parseSingle(node, parameters[0])
            column = int(self.parseSingle(node, parameters[1]))
            value = self.parseSingle(node, parameters[2]).strip()
            retcol = int(self.parseSingle(node, parameters[3]))
            sub, tnode = self.getSubAndNode(node, tableName)
            for line in tnode.table.getLines(sub):
                if line[1][column] == value:
                    retval = line[1][retcol].strip()
        else:
            p = list()
            for i in parameters:
                p.append(self.parseSingle(node, i))
            retval = getattr(tableFunctions, functionName)(p)
        return retval
