import wx
import os
import importlib
import importlib.machinery
import importlib.util
import sys
import time

import  wx.html as  html
import wx.html2 as webview
import  wx.lib.wxpTag
from src import images
import wx.aui
from src.Logger import Log
import linecache


from src.GeneratorPanel import GeneratorPanel

FRAMETB = True
TBFLAGS = ( wx.TB_HORIZONTAL
            | wx.NO_BORDER
            | wx.TB_FLAT
            #| wx.TB_TEXT
            #| wx.TB_HORZ_LAYOUT
            )

class TestSearchCtrl(wx.SearchCtrl):
    maxSearches = 5
    
    def __init__(self, parent, id=-1, value="",
                 pos=wx.DefaultPosition, size=wx.DefaultSize, style=0,
                 doSearch=None):
        style |= wx.TE_PROCESS_ENTER
        wx.SearchCtrl.__init__(self, parent, id, value, pos, size, style)
        self.Bind(wx.EVT_TEXT_ENTER, self.OnTextEntered)
        self.Bind(wx.EVT_MENU_RANGE, self.OnMenuItem, id=1, id2=self.maxSearches)
        self.doSearch = doSearch
        self.searches = []

    def OnTextEntered(self, evt):
        text = self.GetValue()
        if self.doSearch(text):
            self.searches.append(text)
            if len(self.searches) > self.maxSearches:
                del self.searches[0]
            self.SetMenu(self.MakeMenu())            
        self.SetValue("")

    def OnMenuItem(self, evt):
        text = self.searches[evt.GetId()-1]
        self.doSearch(text)
        
    def MakeMenu(self):
        menu = wx.Menu()
        item = menu.Append(-1, "Recent Searches")
        item.Enable(False)
        for idx, txt in enumerate(self.searches):
            menu.Append(1+idx, txt)
        return menu
    

class MainFrame(wx.Frame):
    def __init__(self, *args, **kwds):
        self.ctrl = False
        self.h = dict()
        self.timer = None
        kwds["style"] = wx.DEFAULT_FRAME_STYLE
        wx.Frame.__init__(self, *args, **kwds)
        
        self.MenuBar()
        self.ToolBar()
        
        self.CreateStatusBar()
                
        self.GenBook = wx.aui.AuiNotebook(self)
        self.generators = dict()
        #self.generators['Character'] = GeneratorPanel(self.notebook_2, CharacterGenerator())
        
        path = "src/Generators/"
        d = os.listdir(path)
        d.sort(reverse=True)
        for filename in d:
            if filename[-12:] != "Generator.py":
                continue
            tablename = filename[0:-12]
            filename = path + filename
            spec = importlib.util.spec_from_file_location(tablename, filename)
            module = importlib.util.module_from_spec(spec)
            sys.modules[tablename] = module
            spec.loader.exec_module(module)
            self.generators[tablename] = GeneratorPanel(self.GenBook, module.Generator())
        
        self.ViewBook = wx.aui.AuiNotebook(self)
                        
        self.txtResults = wx.TextCtrl(self, -1, "", style=wx.TE_MULTILINE)
        # Events
        self.Bind(wx.aui.EVT_AUINOTEBOOK_PAGE_CLOSE, self.OnPaneClosing, self.ViewBook)

        self.__set_properties()
        # end wxGlade
        self.__do_layout()
        path = os.getcwd() + "/" + 'html/about.html'
        url = "file://" + path

        self.Populate('about', file=url)
        self.rolling = False
        
    def __set_properties(self):
        self.SetTitle("RPG Generator")
        self.SetSize((1200, 1000))
        self.cboRolls.SetSelection(0)

    def __do_layout(self):
        sizer_1 = wx.BoxSizer(wx.VERTICAL)
        sizer_2 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_7 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_2.Add(sizer_7, 2, wx.EXPAND, 0)
        sizer_1.Add(sizer_2, 8, wx.EXPAND, 0)
        
        self.txtResults.Show(False)
                        
        for t in self.generators:
            self.generators[t].do_layout()
        
        for t in self.generators:
            self.GenBook.AddPage(self.generators[t], t)

        sizer_2.Add(self.ViewBook, 7, wx.EXPAND, 0)
        sizer_7.Add(self.GenBook, 3, wx.EXPAND, 0)

        logger = Log(self)
        sizer_1.Add(logger, 5, wx.EXPAND, 0)

        self.SetSizer(sizer_1)
        self.Layout()
    
    def ToolBar(self):
        tb = self.CreateToolBar( TBFLAGS )
        tsize = (24,24)

        new_bmp =  wx.ArtProvider.GetBitmap(wx.ART_NEW, wx.ART_TOOLBAR, tsize)
        open_bmp = wx.ArtProvider.GetBitmap(wx.ART_FILE_OPEN, wx.ART_TOOLBAR, tsize)
        copy_bmp = wx.ArtProvider.GetBitmap(wx.ART_COPY, wx.ART_TOOLBAR, tsize)
        paste_bmp= wx.ArtProvider.GetBitmap(wx.ART_PASTE, wx.ART_TOOLBAR, tsize)

        tb.SetToolBitmapSize(tsize)

        #tb.AddSimpleTool(10, new_bmp, "New", "Long help for 'New'")
        tb.AddTool(10, "New", new_bmp, "Long help for 'New'")
        self.Bind(wx.EVT_TOOL, self.OnToolClick, id=10)
        self.Bind(wx.EVT_TOOL_RCLICKED, self.OnToolRClick, id=10)

        #tb.AddSimpleTool(20, open_bmp, "Open", "Long help for 'Open'")
        tb.AddTool(20, "Open", open_bmp, "Long help for 'Open'")
        self.Bind(wx.EVT_TOOL, self.OnToolClick, id=20)
        self.Bind(wx.EVT_TOOL_RCLICKED, self.OnToolRClick, id=20)

        tb.AddSeparator()
        tb.AddTool(30, "Copy", copy_bmp, "Long help for 'Copy'")
        self.Bind(wx.EVT_TOOL, self.OnToolClick, id=30)
        self.Bind(wx.EVT_TOOL_RCLICKED, self.OnToolRClick, id=30)

        tb.AddTool(40, "Paste", paste_bmp, "Long help for 'Paste'")
        self.Bind(wx.EVT_TOOL, self.OnToolClick, id=40)
        self.Bind(wx.EVT_TOOL_RCLICKED, self.OnToolRClick, id=40)

        tb.AddSeparator()

        #tool = tb.AddCheckTool(50, images.Tog1.GetBitmap(), shortHelp="Toggle this")
        tool = tb.AddCheckTool(50, "Checkable", images.Tog1.GetBitmap(),
                                    shortHelp="Toggle this")
        self.Bind(wx.EVT_TOOL, self.OnToolClick, id=50)

        self.Bind(wx.EVT_TOOL_ENTER, self.OnToolEnter)
        self.Bind(wx.EVT_TOOL_RCLICKED, self.OnToolRClick) # Match all
        self.Bind(wx.EVT_TIMER, self.OnClearSB)

        tb.AddSeparator()
        cbID = wx.NewId()

        tb.AddControl(
            wx.ComboBox(
                tb, cbID, "", choices=["", "This", "is a", "wx.ComboBox"],
                size=(150,-1), style=wx.CB_DROPDOWN
                ))
        self.Bind(wx.EVT_COMBOBOX, self.OnCombo, id=cbID)
        tb.AddSeparator()
        
        btnRoll = wx.Button(tb, -1, "Roll", style = wx.BU_EXACTFIT)
        tb.AddControl(btnRoll)
        self.Bind(wx.EVT_BUTTON, self.OnRoll, btnRoll)
        self.cboRolls = wx.ComboBox(tb, -1, choices=["1", "5", "10", "15", "20", "25", "100", "1000"], style=wx.CB_DROPDOWN)
        tb.AddControl(self.cboRolls)

        tb.AddStretchableSpace()
        search = TestSearchCtrl(tb, size=(150,-1), doSearch=self.DoSearch)
        tb.AddControl(search)

        # Final thing to do for a toolbar is call the Realize() method. This
        # causes it to render (more or less, that is).
        tb.Realize()
    
    def DoSearch(self,  text):
        # called by TestSearchCtrl
        self.SetStatusText("Searching for: " + text)
        #("DoSearch: %s\n" % text)
        # return true to tell the search ctrl to remember the text
        return True


    def OnToolClick(self, event):
        #print("tool %s clicked\n" % event.GetId())
        #tb = self.GetToolBar()
        tb = event.GetEventObject()
        tb.EnableTool(10, not tb.GetToolEnabled(10))

    def OnToolRClick(self, event):
        print("tool %s right-clicked\n" % event.GetId())

    def OnCombo(self, event):
        print("combobox item selected: %s\n" % event.GetString())

    def OnToolEnter(self, event):
        #('OnToolEnter: %s, %s\n' % (event.GetId(), event.GetInt()))

        if self.timer is None:
            self.timer = wx.Timer(self)

        if self.timer.IsRunning():
            self.timer.Stop()

        self.timer.Start(2000)
        event.Skip()
    def OnClearSB(self, event):  # called for the timer event handler
        self.SetStatusText("")
        self.timer.Stop()
        self.timer = None
        
    def MenuBar(self):
        # Menu Bar
        self.frame_1_menubar = wx.MenuBar()
        wxglade_file_menu = wx.Menu()
        wxglade_edit_menu = wx.Menu()
        wxglade_generate_menu = wx.Menu()
        self.menuExit = wxglade_file_menu.Append(wx.ID_EXIT, "&Quit", "", wx.ITEM_NORMAL)
        self.menuCopy = wxglade_edit_menu.Append(wx.ID_COPY, "&Copy\tCtrl+C", "", wx.ITEM_NORMAL)
        self.menuGen = wxglade_generate_menu.Append(wx.NewId(), "&Roll\tCtrl+R", "", wx.ITEM_NORMAL)
        self.frame_1_menubar.Append(wxglade_file_menu, "&File")
        self.frame_1_menubar.Append(wxglade_edit_menu, "&Edit")
        self.frame_1_menubar.Append(wxglade_generate_menu, "&Generate")
        self.SetMenuBar(self.frame_1_menubar)
        # Menu Bar end
        self.Bind(wx.EVT_MENU, self.OnExit, self.menuExit)
        self.Bind(wx.EVT_MENU, self.OnRoll, self.menuGen)
        self.Bind(wx.EVT_MENU, self.OnCopy, self.menuCopy)

    def OnExit(self, e):
        self.Close(True)
    
    def OnRoll(self, e):
        while self.rolling:
            wx.Yield()
            time.sleep(0.1)
        self.rolling = True
        numRolls = int(self.cboRolls.GetStrings()[self.cboRolls.GetSelection()])
        current = self.GenBook.GetCurrentPage()
        name = self.GenBook.GetPageText(self.GenBook.GetPageIndex(current))
        try:
            t, filename = current.Roll(numRolls)
            path = os.getcwd() + "/" + filename
            url = "file://" + path
            self.Populate(t, file=url)
        except Exception as inst:
            print("Traceback (most recent call last):")
            t, e, tb = sys.exc_info()
            frame = tb.tb_frame.f_back
            flist = list()
            while frame:
                flist.insert(0, frame)
                frame = frame.f_back

            tb = tb.tb_next
            while tb:
                flist.append(tb.tb_frame)
                tb = tb.tb_next
            for f in flist:
                print('  File \"' + f.f_code.co_filename + '\", Line ' + str(f.f_lineno) + ' in ' + f.f_code.co_name)
                line = linecache.getline(f.f_code.co_filename, f.f_lineno)
                print('    ' + line, end='')
            print(type(inst))
            print(e)
            
# traceback.tb_frame
# Points to the execution frame of the current level.
# Accessing this attribute raises an auditing event object.__getattr__ with arguments obj and "tb_frame".
# traceback.tb_lineno
# Gives the line number where the exception occurred
# traceback.tb_lasti
# Indicates the “precise instruction”.

# frame.f_back
# Points to the previous stack frame (towards the caller), or None if this is the bottom stack frame
# frame.f_code
# The code object being executed in this frame. Accessing this attribute raises an auditing event object.__getattr__ with arguments obj and "f_code".
# frame.f_locals
# The mapping used by the frame to look up local variables. If the frame refers to an optimized scope, this may return a write-through proxy object.
# Changed in version 3.13: Return a proxy for optimized scopes.
# frame.f_globals
# The dictionary used by the frame to look up global variables
# frame.f_builtins
# The dictionary used by the frame to look up built-in (intrinsic) names
# frame.f_lasti
# The “precise instruction” of the frame object (this is an index into the bytecode string of the code object)
   

# codeobject.co_name
# The function name
# codeobject.co_qualname
# The fully qualified function name
# codeobject.co_argcount
# The total number of positional parameters (including positional-only parameters and parameters with default values) that the function has
# codeobject.co_posonlyargcount
# The number of positional-only parameters (including arguments with default values) that the function has
# codeobject.co_kwonlyargcount
# The number of keyword-only parameters (including arguments with default values) that the function has
# codeobject.co_nlocals
# The number of local variables used by the function (including parameters)
# codeobject.co_varnames
# A tuple containing the names of the local variables in the function (starting with the parameter names)
# codeobject.co_cellvars
# A tuple containing the names of local variables that are referenced from at least one nested scope inside the function
# codeobject.co_freevars
# A tuple containing the names of free (closure) variables that a nested scope references in an outer scope. See also function.__closure__.
# codeobject.co_code
# A string representing the sequence of bytecode instructions in the function
# codeobject.co_consts
# A tuple containing the literals used by the bytecode in the function
# codeobject.co_names
# A tuple containing the names used by the bytecode in the function
# codeobject.co_filename
# The name of the file from which the code was compiled
# codeobject.co_firstlineno
# The line number of the first line of the function
# codeobject.co_lnotab
# A string encoding the mapping from bytecode offsets to line numbers. For details, see the source code of the interpreter.
# codeobject.co_stacksize
# The required stack size of the code object
# codeobject.co_flags
# An integer encoding a number of flags for the interpreter.                

        self.rolling = False
        
    def Populate(self, name, content=u'', file=''):
        if name in self.h:
            html = self.h[name]
            for i in range(self.ViewBook.GetPageCount()):
                if self.ViewBook.GetPageText(i) == name:
                    self.ViewBook.SetSelection(i)
                    break
        else:
            sizer_7 = wx.BoxSizer(wx.HORIZONTAL)
            notebook_pane = wx.Panel(self.ViewBook, wx.ID_ANY)
            #html = MyHtmlWindow(notebook_pane, -1)
            html = webview.WebView.New(notebook_pane)
            sizer_7.Add(html, 10, wx.EXPAND, 0)
            notebook_pane.SetSizer(sizer_7)
            self.ViewBook.AddPage(notebook_pane, name)
            self.ViewBook.SetSelection(self.ViewBook.GetPageCount() - 1)
            self.h[name] = html
            self.Bind(webview.EVT_WEBVIEW_NAVIGATING, self.OnNavigate, html)

        if file != '':
            html.SetPage("", name)
            html.LoadURL(file)
            self.Layout()
        else:
            if type(name) == bytes:
                # TODO: find where this is happening and fix it
                name = str(name)[2:-1]
            f = open('tmp/' + name + '.html', 'w', encoding="utf-8")
            u = ''
            if content.__class__.__name__ == "unicode":
                u = content
            else:
                u = content
            f.write(u)
            f.close()
            html.SetPage("", name)
            path = os.getcwd() + '/tmp' + "/" + name + ".html"
            url = "file://" + path
            html.LoadURL(url)
            self.Layout()
            #os.remove(name + '.html')

    def OnPaneClosing(self, event):
        current = event.GetSelection()
        name = self.ViewBook.GetPageText(current)
        if name in self.h:
            del self.h[name]
        # 'closing ' + name
        
    def OnNavigate(self, event):
        url = event.GetURL()
        if url[0:4] == "genr":
            s = url.replace('%20', ' ')[7:]
            #print s
            i = s.find(' ')
            g = s[:i]
            s = s[i+1:]
            #print g
            p = dict()
            while s != '':
                i = s.find(' ')
                a = s[:i]
                s = s[i+1:]
                i = s.find(' ')
                if i > 0:
                    v = s[:i]
                    s = s[i+1:]
                else:
                    v = s
                    s = ''
                p[a] = v
            event.Veto()
            t, c = self.generators[g].generator.generate(p)
            self.Populate(t, str(c))

    def OnCopy(self, e):
        t = self.html.SelectionToText()
        clipdata = wx.TextDataObject()
        clipdata.SetText("Hi folks!")
        wx.TheClipboard.Open()
        wx.TheClipboard.SetData(clipdata)
        wx.TheClipboard.Close()

