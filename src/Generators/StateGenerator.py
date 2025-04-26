
import wx
import codecs
from src.Generators.tablegen.tableNode import tableNode
from src.Generators.tablegen.tableManager import tableMgr

class Generator:
    def __init__(self):
        self.tm = tableMgr()
        self.parameters = dict()
        self.parameters['Generators'] = self.tm.getTree()
        self.pList = ['Generators']
    def Update(self, p):
        self.parameters['Generators'] = self.tm.getTree()
        pass
    def GetGeneratorList(self, p):
        # Get list of generators
        genList = []
        for x in self.tm.group[p]:
            genList.append(x)
        genList.sort()
        return genList
    def roll(self, p, numRolls):
        t = u''
        if 'Generators' in p:
            t = p['Generators']
        if type(t) == tableNode:
            filename = "tmp/" + t.name + ".html"
        else:
            filename = "tmp/" + t + ".html"
        f = codecs.open(filename, 'w', "utf-8")
        for j in range(numRolls):
            wx.Yield()
            result = self.tm.roll(t)
            f.write(result)
            f.write('<br>')
        f.close()
        if type(t) == tableNode:
            t = t.name
        return t, filename
        
