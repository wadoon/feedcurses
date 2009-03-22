#!/usr/bin/python 

#import curses
import time
from datetime import *
import feedparser
import thread
from threading import Timer
import functools 
import sys
import urwid.curses_display
import urwid
from urwid import *
import webbrowser


__author__='Alexander Weigl'
__version__ = 'v0.0.1'
__date__='26. Jul. 2008'

FEEDS = (
    "http://www.heise.de/newsticker/heise-atom.xml",
    "http://rss.golem.de/rss.php?feed=RSS1.0",
    "http://feeds.wired.com/wired/index",
    "http://feedproxy.google.com/TheDailyWtf",
    "http://feeds.feedburner.com/catonmat"  ,
    "http://weblogs.java.net/blog/editors/index.rdf",
    "http://www.javaworld.com/index.xml",
"http://feeds.feedburner.com/techtarget/tsscom/home",
    
    
    )

class ClickText(Text):
    def __init__(self, url = '', updater = lambda x: x,  *args,**kwargs):
        Text.__init__(self,*args,**kwargs)
        self.url = url
        self.updater = updater

    def mouse_event(self, (maxcol,), event, button, x, y, focus):
        #self.callback(self, (maxcol,),event,button, x ,y,focus)
        thread.start_new_thread(webbrowser.open, (self.url,))
        self.updater('open %s ' % self.url)
        return True

class FeedManager:       
    def __init__(self, ui, ui_hook):
        self.ui = ui
        self.data = None 
        self.timer = Timer(60.0, self.refresh)
        self.ui_refresh = ui_hook

    def refresh(self):
        self.ui.set_status('refreshing %d lists ...' % len(FEEDS) )
        new_data = []
        i=1
        for feed in FEEDS:            
            d = feedparser.parse(feed)
            #print feed, '----' , repr(d)
            title  = d.feed.title
            for e in d.entries:
                entry = {
                    'feed_title':title,
                    'title': e.title,
                    'link':e.links[0].href,
                    'date':self.con_date( e.updated_parsed )
                    }
                #print e
                #print entry
                new_data.append(entry)
            del d
            self.ui.set_status('refreshing (%d/%d) lists ...' % (i,len(FEEDS)) )
            i+=1
        new_data.sort(lambda x,y: -cmp(x['date'], y['date']) )  
        del self.data
        self.data = new_data
        self.ui_refresh()

    def con_date(self,feed):
        return datetime(*feed[0:6])        
            
class CursesUi:
    def __init__(self):        
        instruction = urwid.Text("FeedCurses %s Press q to exit." % __version__)
        
        self.status_msg = urwid.Text('Loading...')

        self.header = urwid.AttrWrap( instruction, 'header' )
        self.footer =  urwid.Columns((
                ('weight',1,Button('F1-Help', self.on_f1) ),
                ('weight',1,Button('F2-Setup', self.on_f2)),
                ('weight',1,Button('F3-Log', self.on_f2)),
                ('weight',1,Button('F4-', self.on_f2)),
                ('weight',4,AttrWrap( self.status_msg, 'status' )),
                ))
        
        self.blank = urwid.Divider('-')  
        self.content = [ 
            urwid.Padding(
                urwid.Text(
                    'Program is fetching current RSS feed ...' ),
                ('fixed left',2),('fixed right',2), 20),
                         self.blank, ]
        self.content = urwid.SimpleListWalker( self.content ) 
        self.listbox = urwid.ListBox( self.content  )
        
        body =          urwid.AttrWrap( self.listbox, 'body' ) 
        self.frame = urwid.Frame(body,
                                 footer = self.footer,
                                 header = self.header)

        self.feed = FeedManager(self, self.refresh)        
        
    def set_status(self, text):
        #print text
        self.status_msg.set_text(text)
        self.redraw()
        

    def on_f1(self, sender, user_data=None):
        pass

    def on_f2(self, sender, user_data=None):
        pass
    
    def onEveryThin(self, *args):
        self.set_status('click')

    def main(self):                          
        ui = urwid.curses_display.Screen()
        palette =( [
                ('banner', 'black', 'light gray', ('standout', 'underline')),
                ('streak', 'black', 'dark red', 'standout'),
                ('bg', 'black', 'dark blue'),
                ('body', 'white', 'black'),                
                ('header', 'white', 'black'),
                ('status', 'white','black'),
                ('title', 'light green', 'black' , ('bold', 'underline') ),
                ('link', 'light gray' , 'black'),
                ('feed_title', 'light cyan', 'black'),
                ] )
        ui.register_palette(palette)
        self.screen = ui
        ui.run_wrapper( self.run )


    def run(self):
        self.size = self.screen.get_cols_rows()   
        keys=[]
        running = True
        thread.start_new_thread( 
            (lambda x: self.feed.refresh() ) , (None,)  )
        self.screen.set_mouse_tracking()
#        self.screen.set_input_timeouts(2)
	while running:            
            keys = self.screen.get_input()            
            #if not len(keys): continue
            for k in keys:
                self.status_msg.set_text( str(k) )
                if urwid.is_mouse_event(k):
                    event, button, col, row = k
                    self.listbox.mouse_event( (100,100) , 
                                              event, button, col, row,
                                              focus=True )
                    continue

                if "q" == k:
                    self.status_msg.set_text( "close application " )
                    running = False
                elif k=='r':
                    self.feed.refresh()
                elif "window resize" == k:
                    self.size = self.screen.get_cols_rows()
                self.listbox.keypress(self.size,k)
            self.redraw() 

       
    def redraw(self):
        canvas = self.frame.render( self.size , focus = True )
        self.screen.draw_screen( self.size, canvas )
        
    def refresh(self):
        i = 0
        
        current= datetime.today().date()
        
        self.set_status('fetched %d entries, showing first recently' %
                        (len(self.feed.data)));

        del self.content[:]
        
        for e in self.feed.data:
            i+=1            
            self.set_status('(%d/%d)' % ( i , len(self.feed.data) ) );

            w = [ 
                Columns((
                        ('weight',1,
                         ClickText( e['link'], self.set_status,
                                ('title', "%0d. %s" % (i, e['title'] )))),
                        ('fixed',20,
                         Text( 
                                ('feed_title',  e['feed_title'] ))),
                    )),
#                Text( 
#                    ('link',  "   %s" % e['link']) ),                
                ]                    
            
            if e['date'].date()  < current:
                current = e['date'].date()
                h = [
                    urwid.Divider('-'),
                    urwid.Text( current.strftime('%A, %d. %b') ),
                    urwid.Divider('-')
                    ]
                self.content += h            
            self.content += w

        self.set_status('%d refreshed at %s' 
                        % (len(self.content) ,
                           datetime.now().strftime('%H:%m:%s') ) )
                        
        
        
CursesUi().main()

