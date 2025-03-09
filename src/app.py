import wx
from src import MainFrame

def main(argv):
    app = wx.App(False)
    frame_1 = MainFrame.MainFrame(None, -1, "")
    frame_1.Show()
    app.MainLoop()

