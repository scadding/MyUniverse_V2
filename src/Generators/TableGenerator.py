
import wx
import codecs
from src.Generators.tablegen.tableNode import tableNode
from src.Generators.tablegen.tableManager import tableMgr

class Generator:
    tm : tableMgr
    def __init__(self):
        self.tm = tableMgr()
        self.parameters = dict()
        self.parameters['Seed'] = ['', '0']
        self.parameters['Generators'] = self.tm.getTree()
        self.pList = ['Seed', 'Generators']
    def Update(self, p):
        pass
    def roll(self, p, numRolls):
        t = u''
        if 'Seed' in p:
            self.tm.setSeed(int(p['Seed']))
        if 'Generators' in p:
            t = p['Generators']
        if type(t) == tableNode:
            filename = "tmp/" + t.name + ".html"
        else:
            filename = "tmp/" + t + ".html"
            raise TypeError
        f = codecs.open(filename, 'w', "utf-8")
        for j in range(numRolls):
            wx.Yield()
            result = self.tm.roll(t)
            f.write(result)
            f.write('<br>')
        f.close()
        if type(t) == tableNode:
            t = t.name
        # fix this
        return t, filename
        
