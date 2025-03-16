
from src.Generators.tablegen import table
import wx
import codecs
from src.Configuration import Configuration
from anytree import Node, RenderTree, AsciiStyle, LevelOrderIter


class Generator:
    def __init__(self):
        config = Configuration()
        self.tm = table.tableMgr()
        table.walktree(config.getValue("Data", "directory"), self.tm.addfile)
        self.parameters = dict()
        self.parameters['Seed'] = ['', '0']
        self.parameters['Generators'] = self.GetGeneratorTree()
        self.pList = ['Seed', 'Generators']
    def GetGeneratorTree(self):
        root = Node("Root")
        for t in self.tm.groups():
            parent = Node(t, parent=root) 
            for x in self.tm.group[t]:
                pass
                Node(x, parent=parent)
        return root
    def GetGeneratorGroups(self):
        # Get list of generators
        groupList = []
        for t in self.tm.groups():
            groupList.append(t)
        groupList.sort()
        return groupList
    def Update(self, p):
        self.parameters['Generators'] = self.GetGeneratorList(p['Group'])
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
        filename = "tmp/" + t + ".html"
        f = codecs.open(filename, 'w', "utf-8")
        for j in range(numRolls):
            wx.Yield()
            result = self.tm.roll(t)
            f.write(result)
            f.write('<br>')
        f.close()
        return t, filename
        
