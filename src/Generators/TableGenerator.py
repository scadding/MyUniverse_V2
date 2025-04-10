
from src.Generators.tablegen import table
import wx
import codecs
from src.Configuration import Configuration
from anytree import Node, RenderTree, AsciiStyle, LevelOrderIter


class Generator:
    def __init__(self):
        self.tm = table.tableMgr()
        self.parameters = dict()
        self.parameters['Seed'] = ['', '0']
        self.parameters['Generators'] = self.tm.getTree()
        self.pList = ['Seed', 'Generators']

        #self.parameters['Group'] = self.GetGeneratorGroups()
        #self.parameters['Generators'] = []
        #self.pList = ['Seed', 'Group', 'Generators']
    def Update(self, p):
        config = Configuration()
        self.tm = table.tableMgr()
        self.tm.walktree(config.getValue("Data", "directory"), self.tm.addfile, load=True)
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
        if type(t) == Node:
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
        if type(t) == Node:
            t = t.name
        return t, filename
        
