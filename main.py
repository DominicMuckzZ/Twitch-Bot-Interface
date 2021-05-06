import tkinter as tk
import tkinter.ttk as ttk
import tkinter.messagebox as messagebox
import tkinter.simpledialog as simpledialog

from threading import Thread
import pickle
import datetime
import socket
import json
import requests
import random
import re

class command():
    def __init__(self,name,description,output,active,lastUsed,userLevel,cooldown=5):
        self.name = name
        self.description = description
        self.output = output
        self.active = active
        self.lastCalled = lastUsed
        self.userLevel = userLevel
        self.cooldown = cooldown

    def isCooleddown(self):
        if self.lastCalled == None or self.lastCalled <= datetime.datetime.now() - datetime.timedelta(minutes=int(self.cooldown)):
            return True
        return False
    
    def getValues(self):
        active = u"\u274C"
        if self.active:
            active = u"\u2713"
        return (active,self.name,self.description,self.output,self.userLevel)

    def getOutput(self):
        return self.output

    def isActive(self):
        return self.active
    
    def invertActive(self):
        self.active = not(self.active)

    def getUserLevel(self):
        return ["viewer","moderator","broadcaster"].index(self.userLevel)

class message():
    def __init__(self,message):
        self.active = True
        self.message = message

    def getValues(self,index):
        active = u"\u274C"
        if self.active:
            active = u"\u2713"
        return (index,active,self.message)

    def getOutput(self):
        return self.message

    def isActive(self):
        return self.active
    
    def invertActive(self):
        self.active = not(self.active)

HOST = "irc.twitch.tv"
PORT = 6667
try:
    botInfo = pickle.load(open("botCredentials.p","rb"))
    CHAN = botInfo["CHAN"]
    NICK = botInfo["NICK"]
    PASS = botInfo["PASS"]
    RMIT = botInfo["RMIT"]
    AMES = botInfo["AMES"]
    EMES = botInfo["EMES"]
except:
    CHAN = "#"
    NICK = ""
    PASS = ""
    RMIT = True
    AMES = False
    EMES = 50

try:
    callableCommands = pickle.load(open("CommandsList.p","rb"))
except Exception as e:
    print(e)
    callableCommands = {}
try:
    randomMessages = pickle.load(open("randomMessages.p","rb"))
except Exception as e:
    print(e)
    randomMessages = []

cross = u"\u274C"
tick = u"\u2713"
moderators = []
    
class Bot():
    def __init__(self):
        self.connected = False
        self.connection = None
        self.thread = None
        self.botApplication = None
        self.viewerList = []
        self.rmIndex = 0

    def startConnection(self,botApplication):
        self.connected = True
        self.botApplication = botApplication
        self.thread = Thread(target=self.connectToChannel)
        self.thread.daemon = True
        self.thread.start()

    def stopConnection(self):
        self.connection = False
        try:
            self.thread.stop()
        except:
            pass

    def sendRandomMessage(self):
        randomMessageList = self.getActiveRM()
        if len(randomMessageList) > 0:
            if self.botApplication.iterateRM:
                outgoingMessage = randomMessageList[self.rmIndex]
                self.rmIndex += 1
                if self.rmIndex > len(randomMessageList):
                    self.rmIndex = 0
            else:
                outgoingMessage = random.choice(randomMessageList)
            self.sendMessage(CHAN,outgoingMessage.getOutput())
        
    def connectToChannel(self):
        self.CHAN = self.botApplication.channelName.get()
        self.connection = socket.socket()
        self.connection.connect((HOST,PORT))

        self.sendPass(PASS)
        self.sendNick(NICK)
        self.joinChannel(self.CHAN)

        data = ""
        messageCount = 0
        try:
            while self.connected:
                data = data+self.connection.recv(1024).decode('UTF-8')

                data_split = re.split(r"[~\r\n]+", data)
                data = data_split.pop()
                
                for line in data_split:
                    line = str.rstrip(line)
                    line = str.split(line)

                    if len(line) >= 1:
                        if line[0] == 'PING':
                            self.sendPong(line[1])

                        if line[1] == 'PRIVMSG':
                            sender = self.getSender(line[0])

                            message = self.getMessage(line)

                            if sender not in self.viewerList:
                                self.viewerList.append(sender)
                                self.botApplication.addViewer(sender)

                            if self.parseMessages(sender,message):
                                messageSplit = message.split(" ")
                                outgoingMessage = callableCommands[messageSplit[0]].getOutput()
                                self.sendMessage(CHAN,self.formatMessage(outgoingMessage,message,sender))
                            else:
                                if self.botApplication.allowMessages:
                                    messageCount += 1
                                    if messageCount >= int(self.botApplication.rmMessages.get()):
                                        messageCount = 0
                                        self.sendRandomMessage()
                            print(sender,message)
        except ConnectionAbortedError:
            self.connected = False
            self.botApplication.connectButton.config(text="Connect",command=self.botApplication.connectBot)
                            
    def getTarget(self,msg,sender):
        messageSplit = msg.replace("@","").split(" ")
        if messageSplit[1]:
            target = messageSplit[1]
        else:
            target = sender
        return target

    def getActiveRM(self):
        activeMessages = []
        for message in randomMessages:
            if message.isActive():
                activeMessages.append(message)
        return activeMessages

    def getUserLevel(self,sender):
        level = 0
        if sender in moderators:
            level = 1
        elif sender == self.CHAN.replace("#",""):
            level = 2
        return level

    def parseMessages(self,sender,msg):
        messageSplit = msg.split(" ")
        if messageSplit[0] in callableCommands:
            currentCommand = callableCommands[messageSplit[0]]
            if currentCommand.isActive():
                if currentCommand.getUserLevel() <= self.getUserLevel(sender):
                    if currentCommand.isCooleddown():
                        currentCommand.lastCalled = datetime.datetime.now()
                        return True
        return False
        
    def getSender(self,msg):
        result = ""
        for char in msg:
            if char =="!":
                break
            if char != ":":
                result += char
        return result

    def getMessage(self,msg):
        result = ""
        i = 3
        length = len(msg)

        while i < length:
            result += msg[i] + " "
            i += 1
        result = result.lstrip(':')
        return result

    def formatMessage(self,outgoingMessage,message,sender):
        formats = {"rv%":random.choice(self.viewerList),
                   "RV%":random.choice(self.viewerList).upper(),
                   "v%":sender,
                   "V%":sender.upper(),
                   "t%":self.getTarget(message,sender).lower(),
                   "T%":self.getTarget(message,sender).upper()}

        for key in formats:
            outgoingMessage = "".join(outgoingMessage).replace(key,formats[key])
        return outgoingMessage
    
    def sendMessage(self, CHAN, MSG):
        self.connection.send(bytes('PRIVMSG {} :{}\r\n'.format(CHAN,MSG),'UTF-8'))
        
    def sendPong(self,MSG):
        self.connection.send(bytes('PONG {}\r\n'.format(MSG),'UTF-8'))
        
    def sendPass(self,PASS):
        self.connection.send(bytes('PASS {}\r\n'.format(PASS),'UTF-8'))

    def sendNick(self,NICK):
        self.connection.send(bytes('NICK {}\r\n'.format(NICK),'UTF-8'))

    def joinChannel(self,CHAN):
        self.connection.send(bytes('JOIN {}\r\n'.format(CHAN),'UTF-8'))

    def partChannel(self,CHAN):
        self.connection.send(bytes('PART {}\r\n'.format(CHAN),'UTF-8'))
        
class CommandDialog():
    def __init__(self,parent,name=None,description=None,output=None,active=True,userLevel="viewer",cooldown=5):
        self.parent = parent
        self.top = tk.Tk()

        self.nameLabel = tk.Label(self.top,text="Name: ")
        self.nameLabel.grid(column=1,row=1)
        self.nameEntry = tk.Entry(self.top)
        self.nameEntry.grid(column=2,row=1)

        self.descLabel = tk.Label(self.top,text="Description: ")
        self.descLabel.grid(column=1,row=2)
        self.descEntry = tk.Entry(self.top)
        self.descEntry.grid(column=2,row=2)

        self.outLabel = tk.Label(self.top,text="Output: ")
        self.outLabel.grid(column=1,row=3)
        self.outEntry = tk.Entry(self.top)
        self.outEntry.grid(column=2,row=3)

        self.active = active

        self.activeLabel = tk.Label(self.top,text="Active: ")
        self.activeLabel.grid(column=1,row=4)
        self.activeEntry = tk.Checkbutton(self.top,command=self.updateActive)
        self.activeEntry.grid(column=2,row=4)

        self.ulLabel = tk.Label(self.top,text="User Level: ")
        self.ulLabel.grid(column=1,row=5)
        self.ulVariable = tk.StringVar(self.top)
        self.ulVariable.set(userLevel)
        self.ulEntry = tk.OptionMenu(self.top, self.ulVariable, "viewer", "moderator", "broadcaster")
        self.ulEntry.grid(column=2,row=5)

        self.cdLabel = tk.Label(self.top,text="Cooldown: ")
        self.cdLabel.grid(column=1,row=6)
        self.cdInput = tk.Spinbox(self.top,from_=0, to=120)
        self.cdInput.grid(column=2,row=6)

        #Insert Default Data
        self.originalName = name
        if name:
            self.nameEntry.insert(0,name)
        if description:
            self.descEntry.insert(0,description)
        if output:
            self.outEntry.insert(0,output)
        if active:
            self.activeEntry.select()
        if cooldown:
            self.cdInput.delete(0,tk.END)
            self.cdInput.insert(0,cooldown)
        #

        self.submitButton = tk.Button(self.top, text="Submit",command=self.submitCommand)
        self.submitButton.grid(column=1,row=7)

        self.cancelButton = tk.Button(self.top, text="Cancel",command=self.cancelCommand)
        self.cancelButton.grid(column=2,row=7)

    def updateActive(self):
        self.active = not(self.active)
    def cancelCommand(self):
        self.top.destroy()
        
    def submitCommand(self):
        name = self.nameEntry.get()
        description = self.descEntry.get()
        active = self.active
        output = self.outEntry.get()
        userLevel = self.ulVariable.get()
        cooldown = self.cdInput.get()

        callableCommands[name] = command(name,description,output,active,None,userLevel,cooldown)

        edit = False
        field = None
        
        if self.originalName:
            for item in self.parent.ccList.get_children():
                temp = self.parent.ccList.item(item,"values")
                if temp[1] == self.originalName:
                    edit = True
                    field = item

        if edit:
            index = self.parent.ccList.get_children().index(field)
            self.parent.ccList.delete(field)
            self.parent.ccList.insert(parent='',index=index, values=callableCommands[name].getValues())    
        else:
            index = len(self.parent.ccList.get_children())
            self.parent.ccList.insert(parent='',index=index, values=callableCommands[name].getValues())
        self.top.destroy()

class Application():
    def __init__(self,bot):
        self.bot = bot
        self.window = tk.Tk()
        self.window.title("Bot Interface")

        self.window.geometry("705x365")
        self.window.resizable(False,False)

        self.connected = False

        self.channelFrame = tk.LabelFrame(self.window, text="Channel: ",padx=5,pady=5)
        self.channelName = tk.Entry(master=self.channelFrame,justify="right")
        self.connectButton = tk.Button(master=self.channelFrame,text="Connect",command=self.connectBot)

        self.commandsFrame = tk.LabelFrame(self.window, text="Commands: ",padx=5,pady=5)
        self.notebook = ttk.Notebook(self.commandsFrame)
        self.ccFrame = tk.Frame(self.notebook)
        self.randomFrame = tk.Frame(self.notebook)

        ######################Callable Commands List#################
        self.ccList = ttk.Treeview(self.ccFrame)
        self.ccList['columns'] = ('Active','Name','Description','Output','User Level')
        self.ccList.column("#0", width=0, stretch=tk.NO)
        self.ccList.column("Active", anchor=tk.CENTER, width=45)
        self.ccList.column("Name", anchor=tk.CENTER, width=65)
        self.ccList.column("Description", anchor=tk.CENTER, width=80)
        self.ccList.column("Output", anchor=tk.CENTER, width=110)
        self.ccList.column("User Level", anchor=tk.CENTER, width=50)

        self.ccList.heading('#0', text='', anchor=tk.CENTER)
        self.ccList.heading('Active', text='Active', anchor=tk.CENTER)
        self.ccList.heading('Name', text='Name', anchor=tk.CENTER)
        self.ccList.heading('Description', text='Description', anchor=tk.CENTER)
        self.ccList.heading('Output', text='Output', anchor=tk.CENTER)
        self.ccList.heading('User Level', text='User Level', anchor=tk.CENTER)

        for item in callableCommands:
            commandValues=callableCommands[item].getValues()
            self.ccList.insert(parent='',index=0, values=commandValues)

        self.ccAddButton = tk.Button(master=self.ccFrame,text="Add",command=self.ccAddCommand)
        self.ccActivateButton = tk.Button(master=self.ccFrame,text="Activate",command=self.ccActivatePress,state='disabled')
        self.ccEditButton = tk.Button(master=self.ccFrame,text="Edit",command=self.ccEditCommand,state='disabled')
        self.ccDeleteButton = tk.Button(master=self.ccFrame,text="Delete",state='disabled',command=self.ccDeleteCommand)    

        self.ccList.bind("<Double-Button-1>",self.ccButtonActivation)
        self.ccAddButton.place(x=450,y=5,width=75)
        self.ccEditButton.place(x=450,y=35,width=75)
        self.ccActivateButton.place(x=450,y=65,width=75)
        self.ccDeleteButton.place(x=450,y=199,width=75)

        self.ccListScrollbar = tk.Scrollbar(self.ccFrame)
        self.ccListScrollbar.config(command=self.ccList.yview)
        self.ccList.config(yscrollcommand = self.ccListScrollbar.set)
        self.ccListScrollbar.place(x=430,y=5,height=220)

        self.rmList = ttk.Treeview(self.randomFrame)
        self.rmList['columns'] = ('Index','Active','Output')
        self.rmList.column('#0', width=0, stretch=tk.NO)
        self.rmList.column('Index', width=25, stretch=tk.NO)
        self.rmList.column('Active', width=45, stretch=tk.NO)
        self.rmList.column('Output', width=353, stretch=tk.NO)

        self.rmList.heading('#0', text='', anchor=tk.CENTER)
        self.rmList.heading('Index', text='#', anchor=tk.CENTER)
        self.rmList.heading('Active', text='Active', anchor=tk.CENTER)
        self.rmList.heading('Output', text='Output', anchor=tk.CENTER)

        for index in range(len(randomMessages)):
            messageValues=randomMessages[index].getValues(index)
            self.rmList.insert(parent='',index=index, values=messageValues)

        self.rmAddButton = tk.Button(master=self.randomFrame,text="Add",command=self.rmAddMessage)
        self.rmActivateButton = tk.Button(master=self.randomFrame,text="Activate",command=self.rmActivatePress,state='disabled')
        self.rmEditButton = tk.Button(master=self.randomFrame,text="Edit",command=self.rmEditMessage,state='disabled')
        self.rmDeleteButton = tk.Button(master=self.randomFrame,text="Delete",state='disabled',command=self.rmDeleteMessage)
        
        self.rmList.bind("<Double-Button-1>",self.rmButtonActivation)

        self.rmAddButton.place(x=450,y=5,width=75)
        self.rmEditButton.place(x=450,y=35,width=75)
        self.rmActivateButton.place(x=450,y=65,width=75)
        self.rmDeleteButton.place(x=450,y=199,width=75)

        self.rmListScrollbar = tk.Scrollbar(self.randomFrame)
        self.rmListScrollbar.config(command=self.rmList.yview)
        self.rmList.config(yscrollcommand = self.rmListScrollbar.set)
        self.rmListScrollbar.place(x=430,y=5,height=220)
        
        ##################################################################

        self.notebook.add(self.ccFrame, text="Callable Commands")
        self.notebook.add(self.randomFrame, text="Random Messages")

        ##################################################################

        #####################Viewer List##################################
        self.viewerFrame = tk.LabelFrame(self.window, text="Viewers: ",padx=5,pady=5)
        self.viewerListbox = tk.Listbox(self.viewerFrame,activestyle="none",exportselection=False,height=285)

        self.viewerListbox.pack()
        self.viewerFrame.place(x=5,y=75,height=285,width=138)
        ##################################################################

        self.channelName.insert(0,CHAN)
        self.channelName.pack()
        self.connectButton.pack()
        self.channelFrame.place(x=5,y=0,height=75)

        self.ccList.place(x=5,y=5,height=220,width=425)
        self.rmList.place(x=5,y=5,height=220,width=425)

        self.notebook.place(x=0,y=0,width=535,height=255)
        self.commandsFrame.place(x=150,y=75,height=285,width=550)

        self.settingsFrame = tk.LabelFrame(self.window, text="Settings: ",padx=5,pady=5)
        self.nickLabel = tk.Label(self.settingsFrame, text="User: ")
        self.nickEntry = tk.Entry(master=self.settingsFrame,justify="right",width=35)
        self.nickEntry.insert(0,NICK)
        self.nickLabel.place(x=0,y=0)
        self.nickEntry.place(x=50,y=0)

        self.oauthLabel = tk.Label(self.settingsFrame, text="Oauth: ")
        self.oauthEntry = tk.Entry(master=self.settingsFrame,justify="right",width=35)
        self.oauthEntry.insert(0,PASS)
        self.oauthLabel.place(x=0,y=20)
        self.oauthEntry.place(x=50,y=20)

        self.separator = ttk.Separator(self.settingsFrame,orient='vertical')
        self.separator.place(x=270,y=-5,height=50)

        self.iterateRM = RMIT

        self.iterateLabel = tk.Label(self.settingsFrame,text="Message Iteration: ")
        self.iterateLabel.place(x=280,y=0)
        self.iterateEntry = tk.Checkbutton(self.settingsFrame,command=self.updateIteration)
        self.iterateEntry.place(x=380,y=0)
        if self.iterateRM:
            self.iterateEntry.select()

        #Checkbox = Command = StartCountdown
        #Checkbox = Allow Message Countdown

        self.rmMessages = tk.Spinbox(self.settingsFrame,from_=1, to=5000)

        self.rmMessages.delete(0,tk.END)
        self.rmMessages.insert(0,EMES)
        
        self.rmMessageLabel = tk.Label(self.settingsFrame,text="Messages: ")

        self.rmMessages.place(x=490,y=0,width=40)
        self.rmMessageLabel.place(x=415,y=0)

        self.allowMessages = AMES

        self.rmAMessageLabel = tk.Label(self.settingsFrame,text="Random Message Active: ")
        self.rmMessagesCheck = tk.Checkbutton(self.settingsFrame,command=self.updateAMes)

        if self.allowMessages:
            self.rmMessagesCheck.select()

        self.settingsLocked = True
        self.lockButton = tk.Button(self.settingsFrame,text="Unlock",command=self.settingsLock)
        
        self.rmAMessageLabel.place(x=280,y=20)
        self.rmMessagesCheck.place(x=420,y=20)
        self.lockButton.place(x=480,y=20,width=50)

        self.rmMessagesCheck.config(state="disabled")
        self.rmMessages.config(state="disabled")
        self.iterateEntry.config(state="disabled")
        self.oauthEntry.config(state="disabled")
        self.nickEntry.config(state="disabled")
        #Random Messages Settings
        #Number of Messages
        #Time between Messages
        
        self.settingsFrame.place(x=150,y=0,height=75,width=550)

        self.window.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.window.mainloop()

    def settingsLock(self):
        self.settingsLocked = not(self.settingsLocked)
        if self.settingsLocked:
            self.lockButton.config(text="Unlock")
            self.rmMessagesCheck.config(state="disabled")
            self.rmMessages.config(state="disabled")
            self.iterateEntry.config(state="disabled")
            self.oauthEntry.config(state="disabled")
            self.nickEntry.config(state="disabled")
        else:
            self.lockButton.config(text="Lock")
            self.rmMessagesCheck.config(state="normal")
            self.rmMessages.config(state="normal")
            self.iterateEntry.config(state="normal")
            self.oauthEntry.config(state="normal")
            self.nickEntry.config(state="normal")
            
    def updateAMin(self):
        self.allowMinutes = not(self.allowMinutes)

    def updateAMes(self):
        self.allowMessages = not(self.allowMessages)
        
    def updateIteration(self):
        self.iterateRM = not(self.iterateRM)
        
    def addViewer(self,viewerName):
        self.viewerListbox.insert(self.viewerListbox.size(),viewerName)
            
    def ccActivatePress(self):
        temp = self.ccList.item(self.ccList.focus(),"values")
        command = callableCommands[temp[1]]
        command.invertActive()
        if command.isActive():
            self.ccActivateButton.config(text="Deactivate")
        else:
            self.ccActivateButton.config(text="Activate")
        self.ccList.item(self.ccList.focus(),values=command.getValues())

    def ccAddCommand(self):
        CommandDialog(self)
            
    def ccDeleteCommand(self):
        try:
            temp = self.ccList.item(self.ccList.focus(),"values")
            answer = messagebox.askokcancel("Question",f"Delete Command {temp[1]}")
            if answer:
                callableCommands.pop(temp[1],None)
                self.ccList.delete(self.ccList.focus())
        except:
            pass

    def ccEditCommand(self):
        try:
            temp = self.ccList.item(self.ccList.focus(),"values")
            command = callableCommands[temp[1]]
            CommandDialog(self,command.name,command.description,command.output,command.active,command.userLevel,command.cooldown)        
        except:
            pass
            
    def ccButtonActivation(self,event):
        temp = self.ccList.item(self.ccList.focus(),"values")
        if temp[0] == tick:
            self.ccActivateButton.config(text="Deactivate")
        else:
            self.ccActivateButton.config(text="Activate")
        self.ccActivateButton.config(state="active")
        self.ccEditButton.config(state="active")
        self.ccDeleteButton.config(state="active")
        ###############################################

        ####################Random Commands List#####################

    def rmActivatePress(self):
        try:
            index = self.rmList.get_children().index(self.rmList.focus())
            message = randomMessages[index]
            message.invertActive()
            if message.isActive():
                self.rmActivateButton.config(text="Deactivate")
            else:
                self.rmActivateButton.config(text="Activate")
            self.rmList.item(self.rmList.focus(),values=message.getValues(index))
        except:
            pass
            
    def rmDeleteMessage(self):
        try:
            index = self.rmList.get_children().index(self.rmList.focus())
            temp = self.rmList.item(self.rmList.focus(),"values")
            answer = messagebox.askokcancel(message=f"Delete Message #{temp[0]}")
            if answer:
                randomMessages.pop(index)
                self.rmList.delete(self.rmList.focus())
        except:
            pass

    def rmAddMessage(self):
        try:
            newMessage = simpledialog.askstring(title="",prompt="Input Message: ",parent=self.window)
            if newMessage:
                newMessage = message(newMessage)
                randomMessages.append(newMessage)
                index = len(self.rmList.get_children())
                self.rmList.insert(parent='',index=index, values=newMessage.getValues(index))
        except:
            pass

    def rmEditMessage(self):
        try:
            index = self.rmList.get_children().index(self.rmList.focus())
            newMessage = simpledialog.askstring(title="",prompt="Input Message: ",parent=self.window)
            randomMessages[index].message = newMessage
                
            self.rmList.item(self.rmList.focus(),values=randomMessages[index].getValues(index))
        except Exception as e:
            print(e)
                       
    def rmButtonActivation(self,event):
        temp = self.rmList.item(self.rmList.focus(),"values")
        index = int(temp[0])
        if temp[1] == tick:
            self.rmActivateButton.config(text="Deactivate")
        else:
            self.rmActivateButton.config(text="Activate")
        self.rmActivateButton.config(state="active")
        self.rmEditButton.config(state="active")
        self.rmDeleteButton.config(state="active")
            
        #####################################################

        #####################Built In Commands List######################

    def connectBot(self):
        self.bot.startConnection(self)
        self.connectButton.config(text="Disconnect",command=self.disconnectBot)

    def disconnectBot(self):
        self.bot.stopConnection()
        self.connectButton.config(text="Connect",command=self.connectBot)

    def getBotValues(self):
        botInfo = {"CHAN":self.channelName.get(),
                   "NICK":self.nickEntry.get(),
                   "PASS":self.oauthEntry.get(),
                   "RMIT":self.iterateRM,
                   "AMES":self.allowMessages,
                   "EMES":self.rmMessages.get()}
        return botInfo
    
    def on_closing(self):
        botInfo = self.getBotValues()
        pickle.dump(botInfo,open("botCredentials.p","wb"))
        pickle.dump(callableCommands,open("CommandsList.p","wb"))
        pickle.dump(randomMessages,open("randomMessages.p","wb"))
        self.window.destroy()

bot = Bot()
Application(bot)
