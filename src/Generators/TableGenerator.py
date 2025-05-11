
from src.Generators.tablegen import table
import wx
import codecs
from src.Configuration import Configuration
from src.Generators.tablegen.tableNode import tableNode
from src.Generators.tablegen.tableManager import tableMgr

class Generator:
    def __init__(self):
        self.tm = tableMgr()
        self.parameters = dict()
        self.parameters['Seed'] = ['', '0']
        self.parameters['Generators'] = self.tm.getTree()
        self.pList = ['Seed', 'Generators']

        #self.parameters['Group'] = self.GetGeneratorGroups()
        #self.parameters['Generators'] = []
        #self.pList = ['Seed', 'Group', 'Generators']
    def Update(self, p):
        config = Configuration()
        self.tm = tableMgr()
        self.tm.walktree(config.getValue("Data", "directory"), self.tm.addfile, load=False)
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
        if 'Seed' in p:
            self.tm.setSeed(int(p['Seed']))
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
        # fix this
        return t, filename
        
