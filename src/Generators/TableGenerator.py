
from src.Generators.tablegen import table
import wx
import codecs


class Generator:
    def __init__(self):
        self.tm = table.tableMgr()
        table.walktree('Data/Tables', self.tm.addfile)
        self.parameters = dict()
        self.parameters['Seed'] = ['', '0']
        self.parameters['Group'] = self.GetGeneratorGroups()
        self.parameters['Generators'] = []
        self.pList = ['Seed', 'Group', 'Generators']
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
        results = u''
        filename = "tmp/" + t + ".html"
        f = codecs.open(filename, 'w', "utf-8")
        for j in range(numRolls):
            wx.Yield()
            result = self.tm.roll(t)
            f.write(result)
            f.write('<br>')
        f.close()
        return t, filename
        
