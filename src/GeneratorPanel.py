import wx
from src import images
from src.Generators.tablegen.tableNode import tableNode


class GeneratorPanel(wx.Panel):
    def __init__(self, parent, generator):
        self.generator = generator
        wx.Panel.__init__(self, parent, wx.ID_ANY)
        self.labels = dict()
        self.fields = dict()
        for n in self.generator.pList:
            self.labels[n] = wx.StaticText(self, -1, n)
            if type(self.generator.parameters[n]) is list:
                if self.generator.parameters[n]:
                    self.fields[n] = wx.ComboBox(self, -1, choices=self.generator.parameters[n], style=wx.CB_DROPDOWN)
                    self.Bind(wx.EVT_COMBOBOX, self.onUpdate, self.fields[n])
                else:
                    self.fields[n] = wx.ListBox(self, -1)
            elif type(self.generator.parameters[n]) is dict:
                l = []
                for a in self.generator.parameters[n]:
                    l.append(a)
                self.fields[n] = wx.ComboBox(self, -1, choices=l, style=wx.CB_DROPDOWN)
            elif type(self.generator.parameters[n]) is tableNode:
                tID = wx.NewIdRef()
                tree = wx.TreeCtrl(self, tID, wx.DefaultPosition, wx.DefaultSize,
                                    wx.TR_HAS_BUTTONS
                                    | wx.TR_EDIT_LABELS
                                    | wx.TR_HIDE_ROOT
                                    #| wx.TR_MULTIPLE
                                    #| wx.TR_HIDE_ROOT
                                    )
                self.fields[n] = tree
                il = wx.ImageList(16, 16)
                fldridx     = il.Add(wx.ArtProvider.GetBitmap(wx.ART_FOLDER,      wx.ART_OTHER))
                fldropenidx = il.Add(wx.ArtProvider.GetBitmap(wx.ART_FOLDER_OPEN, wx.ART_OTHER))
                fileidx     = il.Add(wx.ArtProvider.GetBitmap(wx.ART_NORMAL_FILE, wx.ART_OTHER))
                smileidx    = il.Add(images.Smiles.GetBitmap())

                self.fields[n].SetImageList(il)
                self.il = il
                self.root = self.fields[n].AddRoot(self.generator.parameters[n].name)
                self.fields[n].SetItemData(self.root, None)
                self.fields[n].SetItemImage(self.root, fldridx, wx.TreeItemIcon_Normal)
                self.fields[n].SetItemImage(self.root, fldropenidx, wx.TreeItemIcon_Expanded)

                self.add_children(self.fields[n], self.root, self.generator.parameters[n], fldridx, fldropenidx, fileidx, smileidx)
            else:
                self.fields[n] = wx.TextCtrl(self, -1, self.generator.parameters[n])
    def add_children(self, tree, wx_node_id, node, fldridx, fldropenidx, fileidx, smileidx):
        for n in node.children:
            if not n.display:
                continue
            child = tree.AppendItem(wx_node_id, n.name)
            tree.SetItemData(child, n)
            if n.children:
                tree.SetItemImage(child, fldridx, wx.TreeItemIcon_Normal)
                tree.SetItemImage(child, fldropenidx, wx.TreeItemIcon_Expanded)
                self.add_children(tree, child, n, fldridx, fldropenidx, fileidx, smileidx)
            else:
                tree.SetItemImage(child, fileidx, wx.TreeItemIcon_Normal)
                tree.SetItemImage(child, smileidx, wx.TreeItemIcon_Selected)
        tree.SortChildren(wx_node_id)
    def do_layout(self):
        panelSizer = wx.BoxSizer(wx.VERTICAL)
        for n in self.generator.pList:
            v = 0
            if type(self.fields[n]) is wx.ListBox or type(self.fields[n]) is wx.TreeCtrl:
                paramSizer = wx.BoxSizer(wx.VERTICAL)
                v = 10
            else:
                paramSizer = wx.BoxSizer(wx.HORIZONTAL)
            paramSizer.Add(self.labels[n], 0, wx.ALIGN_CENTER)
            paramSizer.Add(self.fields[n], 1, wx.EXPAND, 0)
            panelSizer.Add(paramSizer, v, wx.ALL | wx.EXPAND, 4)
        self.SetSizer(panelSizer)
    def onUpdate(self, e):
        p = dict()
        for n in self.generator.parameters:
            if type(self.generator.parameters[n]) is tableNode:
                continue
            if type(self.fields[n]) is not wx.ListBox:
                if self.fields[n].GetValue() != "":
                    p[n] = self.fields[n].GetValue()
        self.generator.Update(p)
        for n in self.generator.parameters:
            if type(self.generator.parameters[n]) is tableNode:
                continue
            if type(self.fields[n]) is wx.ListBox:
                self.fields[n].SetSelection(-1)
                self.fields[n].Clear()
                self.fields[n].Set(self.generator.parameters[n])
    def Roll(self, numRolls):
        p = dict()
        for n in self.generator.parameters:
            value = ""
            if type(self.fields[n]) is wx.TreeCtrl:
                value = self.fields[n].GetItemText(self.fields[n].GetFocusedItem())
                value = self.fields[n].GetItemData(self.fields[n].GetFocusedItem())
            elif type(self.fields[n]) is wx.ListBox:
                value = self.fields[n].GetStrings()[self.fields[n].GetSelection()]
            else:
                value = self.fields[n].GetValue()
            if value != "":
                p[n] = value
        # change this
        return self.generator.roll(p, numRolls)
