import os
import os.path
import time
import random

import urllib.request
from urllib3.exceptions import MaxRetryError

from DirTools import *
from DriverAgent import *
from LogMaker import *


class rsrcCrawler():
    
    def __init__(self, rootURL, resourceDict):
        
        self.initializeSession( rootURL, resourceDict )
        self.logInfo( "initialized session" )
        
        self.main()
    
    
    def initializeSession( self, rootURL, resourceDict ):
        
        self.rootURL = rootURL
        self.resourceDict = resourceDict
        
        self.cwdir = os.path.dirname(os.path.abspath(__file__))
        os.chdir(self.cwdir)
        self.tempDL = self.cwdir + "\\" + "_tempDL"
        self.logDir = self.cwdir + "\\" + "_logs"
        
        for dirPath in [ self.tempDL, self.logDir ]: 
            if not os.path.exists(dirPath): os.makedirs(dirPath)
        
        dirTools = DirTools()
        self.waitRename = dirTools.waitRename
        self.tryRename = dirTools.tryRename
        self.tryMove = dirTools.tryMove
        self.dtStamp = dirTools.dtStamp
        self.storePKL = dirTools.storePKL
        self.cleanString = dirTools.cleanString
        
        logMaker = LogMaker( self.logDir )
        self.log = logMaker.make( "rsrcCrawl", "info" )
        self.infoDict = {}
    
    
    def logInfo( self, item ):
        ''' add to dictionary as well as logging ( key as datetime ) '''
        self.infoDict[self.dtStamp()] = item
        self.log.info( item )
    
    
    def main( self ):
        
        self.startBrowser( headless=False )
        self.login()
        
        for rsrcName in self.resourceDict:
            
            self.rsrcRoot = self.rootURL + self.resourceDict[rsrcName]
            self.rsrcName = rsrcName
            self.resourceGet()  # TEST LIMIT: loLim=3, hiLim=4
            
            self.logInfo( f"COMPLETED {self.rsrcName}" )
    
    
    def resourceGet(self, loLim=0, hiLim=None, headless=False):
        
        print( f"Crawling {self.rsrcName}" )
        self.initializeDirectory()
        self.getModIndex()
        self.rsrcDict = {}
        
        titles = []
        collecting = False
        cPos = 0
        for i in self.modIndex:
            if cPos >= loLim : collecting = True
            if hiLim and ( cPos > hiLim ): collecting = False
            if collecting: titles.append(i)
            cPos +=1
            
        pos = loLim; leng = len(self.modIndex)
        for title in titles:
            print( f"\nGET RESOURCE {pos+1} of {leng}:" )
            print( f"TITLE: [ {title} ]\nURL:   [ {self.modIndex[title]} ]")
            self.getPage( title, self.modIndex[title] )
            time.sleep( self.randDbl( 0.5, 1.5) )
            self.storePKL( self.rsrcDict, 'rsrcDict', self.modDir, "_data" )
            pos +=1
    
    
    def initializeDirectory( self ): 
        
        print( f"\n rsrcName {self.rsrcName} SET AS SESSION DIRECTORY ")
        if not os.path.exists(self.rsrcName): os.makedirs(self.rsrcName)
        self.modDir = self.cwdir + "\\" + self.rsrcName
        os.chdir(self.modDir)
        
        self.mediaDir = self.cwdir + "\\" + "_MEDIA"
        
        if not os.path.exists(self.mediaDir): os.makedirs(self.mediaDir)
    
    
    def startBrowser( self, headless=False ):
        
        agent = DriverAgent( self.tempDL )
        agent.getBrowser(headless=headless)
        
        # for quicker reference
        self.driver = agent.driver
        self.actions = agent.actions
        self.xpathEC = agent.xpathEC
        self.keys = agent.keys
    
    
    def login( self ):
        
        menuXP = "//*[@id='menu']"
        self.driver.get( self.rootURL )
        if self.xpathEC(menuXP, 5, 6): return
        
        loggedIn = False
        while ( not loggedIn ):
            
            unamXP = "//*[@id='username']"
            unamEC = self.xpathEC(unamXP)
            unamEC.send_keys("########")
            time.sleep(self.randDbl(0.5, 1))
            
            passXP = "//*[@id='password']"
            unamEC = self.xpathEC(passXP)
            unamEC.send_keys("########")
            time.sleep(self.randDbl(0.5, 1))
            
            lbutXP = "//*[@id='kc-login']"
            lbutEC = self.xpathEC(lbutXP)
            self.actions.move_to_element(lbutEC).click().perform()
            
            if self.xpathEC(menuXP, 10, 15): loggedIn = True    
    
    
    def getModIndex( self ):
        
        self.driver.get(self.rsrcRoot + "/modules")
        
        mditXP = "//*[@class='ig-title title item_link']"
        if not self.xpathEC(mditXP): 
            self.logInfo( f"No rsrc subitems: {self.driver.current_url}" )
            return
        
        try: modItems = self.driver.find_elements(By.XPATH, mditXP)
        except Exception as e: 
            self.logInfo( f"Lost rsrc subitems: {self.driver.current_url}"
                + f"\nEXC: {type(e).__name__} \n{e}" ); return
        
        self.modIndex = {}
        for obj in modItems:
            rawTitle = obj.get_attribute('title')
            title = self.cleanString(rawTitle, 'M', stamp=True)
            self.modIndex[title] = obj.get_attribute('href')
    
    
    def getPage(self, title, url):
        
        def createPageDir():
            if not os.path.exists(title): os.makedirs(title)
            else: print( f"located subdir [ {title} ]" )
        
        def getPDF(): 
            
            self.driver.execute_script('window.print();')
            curTitlePath = self.cwdir + "\\" + "printed_temp.pdf"
            newTitlePath = self.cwdir + "\\" + title + ".pdf"
            
            if not self.tryRename( curTitlePath, newTitlePath ): return False
            elif not self.tryMove( newTitlePath, self.subdir ): return False
            else: return True
        
        self.subdir = self.modDir + "\\" + title
        pageDict = {}
        self.rsrcDict[title] = pageDict; self.randSleep(2, 3)
        
        while True:
            self.randSleep(1, 2)
            try: self.driver.get(url)
            except TimeoutException: self.logInfo( f"TimeoutExc on {url}" )
            else: break
            
        createPageDir(); self.randSleep(1, 1.5)
        if not getPDF(): logInfo( f"failed getPDF for {title} at\n{url}" )
        else: self.randSleep(1, 1.5)
        self.getFiles()
        iframes = self.getIFrames()
        if not self.retrieveMedia( iframes ): 
            self.logInfo( f"DL failed: {link}" )
    
    
    def getFiles( self ):
        
        fileLinks = self.getFileLinks()
        if len(fileLinks) > 0: print( f"got {len(fileLinks)} fileLinks")
        else: 
            self.logInfo( f"no fileLinks at {self.driver.current_url}" )
            return
        
        contentXP = "//*[@id='content']"
        nameXP = "./h2"
        
        fPos = 1
        for link in fileLinks:
            print(f"checking {fPos}"); fPos+=1
            try: self.driver.get(link)
            except TimeoutException as e:
                self.logInfo( f"TimeoutException at {link}" ); return
            
            contentEC = self.xpathEC(contentXP)
            if contentEC:
                nameEC = self.xpathEC( nameXP, drobject=contentEC)
                dlName = nameEC.get_attribute("innerHTML")
                if "&amp;" in dlName: dlName = ''.join(dlName.split("amp;"))
                name = self.cleanString(dlName, isFile=True, stamp=True)
                
                try: self.driver.get(link+"/download")
                except TimeoutException:
                    self.logInfo( f"filelink timeout {link+'/download'}" )
                
                dlPathN = self.tempDL + "\\" + dlName
                nameP = self.tempDL + "\\" + name
                self.tryRename( dlPathN, nameP )
                self.tryMove( nameP, self.subdir )
                
            else: self.logInfo( f"no contentEC for {link}" ); return
    
    
    def getFileLinks( self ):
        
        fURL = self.rsrcRoot+"/files"
        try: linkObjs = self.driver.find_elements(By.XPATH, "//a[@href]")
        except: self.logInfo( f"EXC linkObjs: {self.driver.current_url}" )
        
        fileLinks = []
        for obj in linkObjs:
            href = obj.get_attribute("href")
            if fURL in href: 
                hrefClean = f"{fURL}/{href.split(fURL)[1].split('/')[1]}"
                if hrefClean not in fileLinks: fileLinks.append(hrefClean)
                
        return fileLinks    
    
    
    def getIFrames( self ):
        
        iframes = []
        ifrObjs = self.driver.find_elements(By.XPATH, "//iframe")
        
        for ob in ifrObjs: 
            src = ob.get_attribute('src')
            if (len(src)>1) and (src != "about:blank"): iframes.append(src)
            
        return iframes
    
    
    def retrieveMedia( self ): pass
    
    
    def randDbl( self, loLimit=0.4, hiLimit=1.9 ):
        return random.uniform(loLimit, hiLimit)
    
    
    def randSleep( self, lo=2, hi=3 ): time.sleep( self.randDbl(lo, hi) )

