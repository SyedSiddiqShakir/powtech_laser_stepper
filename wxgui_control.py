#!/usr/bin/env python
import wx

class My_Frame(wx.Frame):

    def __init__(self, *args, **kw):
        # ensure the parent's __init__ is called
        super(My_Frame, self).__init__(*args, **kw)

        # create a panel in the frame
        pnl = wx.Panel(self)

        # put some text with a larger bold font on it
        st = wx.StaticText(pnl, label="Laser Control")
        font = st.GetFont()
        font.PointSize += 10
        font = font.Bold()
        st.SetFont(font)

        # and create a sizer to manage the layout of child widgets
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(st, wx.SizerFlags().Border(wx.TOP|wx.LEFT, 25))
        pnl.SetSizer(sizer)

        # create a menu bar
        self.makeMenuBar()

        # and a status bar
        self.CreateStatusBar()
        self.SetStatusText("welcome to laser control")


    def makeMenuBar(self):
       
        # a file menu with Hello and Exit items
        fileMenu = wx.Menu()

        # The "\t..." syntax defines an accelerator key that also triggers
        # the same event
        helloItem = fileMenu.Append(-1, "&Hello...\tCtrl-H",
                "Help string shown in status bar for this menu item")
        fileMenu.AppendSeparator()

        # label
        exitItem = fileMenu.Append(wx.ID_EXIT)

        # Now a help menu for the about item
        MoveMenu = wx.Menu()
        aboutItem = MoveMenu.Append(wx.ID_ABOUT)

        menuBar = wx.MenuBar()
        menuBar.Append(fileMenu, "&File")
        menuBar.Append(MoveMenu, "&Movement")

        # Give the menu bar to the frame
        self.SetMenuBar(menuBar)

        # Finally, associate a handler function with the EVT_MENU event for
        # each of the menu items. That means that when that menu item is
        # activated then the associated handler function will be called.
        self.Bind(wx.EVT_MENU, self.OnHello, helloItem)
        self.Bind(wx.EVT_MENU, self.OnExit,  exitItem)
        self.Bind(wx.EVT_MENU, self.OnAbout, aboutItem)


    def OnExit(self, event):
        """Close the frame, terminating the application."""
        self.Close(True)


    def OnHello(self, event):
        """Say hello to the user."""
        wx.MessageBox("welcome again to laser control")


    def OnAbout(self, event):
        """Display an About Dialog"""
        wx.MessageBox("DO you wanna control a laser?",
                      wx.OK|wx.ICON_INFORMATION)


if __name__ == '__main__':
    # When this module is run (not imported) then create the app, the
    # frame, show it, and start the event loop.
    app = wx.App()
    frm = My_Frame(None, title='Hello World 2')
    frm.Show()
    app.MainLoop()