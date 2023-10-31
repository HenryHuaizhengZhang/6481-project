"""
    Sample code for Multi-Threaded Server
    Python 3
    Usage: python3 server.py port block_time timeout
    coding: utf-8
    
    Author: Huaizheng Zhang (Assignment for COMP6481)
"""


# 1. add self.username to userblock list
# 2. if userblock is ready in, then send message has been blocked.
# 3. message to block, check blocklist, if there any name in blocklist, send message you are blocked by
# 4. broadcast, check blocklist, if there any name in blocklist, send message some users can't receive because of block
# 5. When a user log in, the broadcast of login whether need to receive feedback some users can't receive because of block?
# When a client stop the connect, ctrl+c, the server should also disconnect. And when the client use the same terminal(port) to connect. The server should setup a new connection.

                    
import socket
import threading
from threading import Thread
import sys, select
import time
import ssl
#import errno

#HZ
context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
context.minimum_version = ssl.TLSVersion.TLSv1_2
context.maximum_version = ssl.TLSVersion.TLSv1_3
context.load_cert_chain(certfile="mycert.pem") 
#HZ


# acquire server host and port from command line parameter
if len(sys.argv) != 4:
    print("\n===== Error usage, python3 server.py SERVER_PORT, block_duration, timeout ======\n");
    exit(0);
serverHost = "127.0.0.1"
serverPort = int(sys.argv[1])
serverAddress = (serverHost, serverPort)

block_duration = int(sys.argv[2])
timeout = int(sys.argv[3])


# define socket for the server side and bind address
#serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
serversocket = socket.socket() #HZ
serversocket.bind(serverAddress)
serversocket.listen(10)

#HZ
context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
context.load_cert_chain(certfile="mycert.pem") 
context.set_ciphers('HIGH')
#context.get_ciphers()
#HZ



listusernames = [] # list of username.
dictusersocket = {} 	# key is username. Value is the clientsocket of each client.
dictsocketuser = {} # key is clientsocket. Value is the username of each client.
dictsocketaddress = {}  # key is clientsocket. Value is the address/port of each client.
userpwd = {}        # key is username. Value is pwd.
userstatus = {}     # key is username. Two values, online, offline
userblocked = {}  # key is username. For each username record the clients whom he/she have blocked. The value will be a list of usernames.
user1stlogin = {}   # key is username. Value is the time of 1st login after the server started. 
userlastlogouttime = {} # key is username. Value is the time of latest logout to support whoelsesince command
userlogintime = {}  # key is username. Value is the time of last login after the server started. 
userloginblock = {} # key is username. Value is True or False. To show whether the client is being login blocked.
userloginfailedtimes = {}   # key is username. Value is 0, 1, 2, 3. To show the times of password failure during login process.
commands = ['message', 'broadcast', 'whoelse', 'whoelsesince', 'block', 'unblock', 'logout', 'private', 'startprivate', 'stopprivate', 'privateconfirmed', 'startprivaterejected']
usertimer = {}
privatewith = {}    # key is clientname, value another clientname. To record the username that the client is private with. Only one private chat is allow to have for each client.
userofflinemessage = {}

#usertimeout = {}    # key is username. The value is 'on' and 'off'. 'on' means timeout. 'off' means no timeout.



#userclientsocket = {} 	# key is username. Value is the clientsocket of each client.
#useraddress = {}
#addressclientsocket = {}    # key is tuple (address, port). Value is the clientsocket of each client tuple (address, port).

with open('credentials.txt', 'r') as f:
    for line in f:
        if len(line.strip()) == 1:
            pass
        else:
            strings = line.strip().split()
            userpwd[strings[0]] = strings[1] # To record the password of each user.
            userstatus[strings[0]] = 'offline' # To record the status of the user. There are two values, 'offline' and 'online'.
            userblocked[strings[0]] = [] # To record the list of users who have blocked this user.
            user1stlogin[strings[0]] = 0 # To record whether a user have logged in before/ whether it's the 1st time log in.
            userlogintime[strings[0]] = [time.time(), time.time()] # To store the 1st login time and the last login time. Set the initial values.
            userloginblock[strings[0]] = False
            userloginfailedtimes[strings[0]] = 0
            userlastlogouttime[strings[0]] = 0
            privatewith[strings[0]] = ''
            userofflinemessage[strings[0]] = []
            dictusersocket[strings[0]] = None
#            usertimeout[strings[0]] = 'off'


def TimingThread(clientsocket):
        username = ''  # To store the username of each CLientThread
        global timeout  # parameter of timeout
        sendmessage = ''
        username = dictsocketuser[clientsocket]
        #print('Start Timing')
        #print(clientsocket)
        #print(username)
        while True:
            t = time.time() - usertimer[username]
            #print(t)
            if t > timeout:
                #print('if time.time() - self.timer > self.timeout: Yes, t=', t)
                sendmessage = 'server: timeout'
                clientsocket.send(sendmessage.encode())
                #print('[send] ' + sendmessage)
                #time.sleep(0.1)
                break
            if userstatus[username] == 'offline':
                break


class ClientThread(Thread):
#    global usertimeout
    def __init__(self, clientsocket):
        Thread.__init__(self)
#        self.clientaddress = clientaddress
        self.clientsocket = clientsocket
        #self.clientsocket.setblocking(0)
        self.clientAlive = False    # To record the status of each ClientThread, True will keep self.clientsocket.recv(1024), False will stop receive message.
        self.login = False  # To record the login status of each CLientThread, there are two values, True for login and False for not login.
        self.username = ''  # To store the username of each CLientThread
        self.block_duration = block_duration
        self.timeout = timeout  # parameter of timeout
        self.timer = 0
        self.newuserloginfailedtime = 0
        
        #print("===== New connection created for: ", dictsocketaddress[clientsocket])
        self.clientAlive = True


    def run(self):
        recvmessage = 'Server started'
        x = 0   # To record how many times of recvmessage == '', which can detect the Ctrl + c force shut down at the user end.
        datareceiver = [self.clientsocket]
        while self.clientAlive:
            readyinput, readyoutput, readyexception = select.select(datareceiver, [], [])
            for datasource in readyinput:
                if datasource == self.clientsocket:
                    recvmessage = self.clientsocket.recv(1024).decode('utf-8')
                    #if recvmessage != '' and recvmessage != ' ':
                    #    print(recvmessage)
                    if not recvmessage:
                        break
            if self.login == False:
                #self.process_login(receivedMessage)
                self.process_login(recvmessage)
            elif self.login == True:
                
                #if recvmessage != '' and recvmessage.split()[0] not in commands and recvmessage != 'check timeout':
                if recvmessage != '' and recvmessage.split()[0] not in commands:
                    sendmessage = 'Error. Invalid command'
                    self.clientsocket.send(sendmessage.encode())
                elif recvmessage != '' and  recvmessage.split()[0] in commands:
                    usertimer[self.username] = time.time()
                    x = 0   # To record how many times of recvmessage == '', which can detect the Ctrl + c force shut down at the user end.
                    
                # call whoelse
                self.whoelse(recvmessage)
                self.whoelsesince(recvmessage)

                # broadcast
                if recvmessage != '' and  recvmessage.split()[0] == 'broadcast':
                    blocknotification = 'unnotified'
                    for clientname in userpwd:
                        if clientname != self.username and self.username not in userblocked[clientname] and userstatus[clientname] == 'online':
                            sendmessage = 'broadcast ' + dictsocketuser[self.clientsocket] + ': ' + " ".join(recvmessage.split()[1:])
                            try:
                                dictusersocket[clientname].send(sendmessage.encode())
                                #print(self.username + ' broadcast: ' + recvmessage)
                            except:
                                #print(clientname, ' connection is broken.')
                                pass
                        elif clientname != self.username and self.username in userblocked[clientname] and blocknotification != 'notified':
                            sendmessage = 'Your message could not be delivered to some recipients'
                            blocknotification = 'notified'
                            self.clientsocket.send(sendmessage.encode())             

                # message 
                if recvmessage != '' and  recvmessage.split()[0] == 'message':
                    if len(recvmessage.split()) >= 2:
                        if recvmessage.split()[1] not in userpwd or recvmessage.split()[1] == self.username:
                            sendmessage = 'Error. Invalid user'
                            #print('recvmessage.split()[1] =', recvmessage.split()[1])
                            #print(dictusersocket)
                            self.clientsocket.send(sendmessage.encode())
                        elif recvmessage.split()[1] in userpwd and self.username in userblocked[recvmessage.split()[1]]:
                            sendmessage = 'Your message could not be delivered as the recipient has blocked you'
                            self.clientsocket.send(sendmessage.encode())
                        elif recvmessage.split()[1] in userpwd and self.username not in userblocked[recvmessage.split()[1]]:
                            # Online message
                            if userstatus[recvmessage.split()[1]] == 'online':
                                msgtoclientsocket = dictusersocket[recvmessage.split()[1]]
                                sendmessage = 'message ' + dictsocketuser[self.clientsocket] + ': ' + " ".join(recvmessage.split()[2:])
                                msgtoclientsocket.send(sendmessage.encode())
                            # Offline message
                            if userstatus[recvmessage.split()[1]] == 'offline':
                                sendmessage = 'message ' + self.username + ': ' + " ".join(recvmessage.split()[2:])
                                userofflinemessage[recvmessage.split()[1]].append(sendmessage)


                            
                # block. setup userblock dictionary to record who has blocked the user.
                if recvmessage != '' and  recvmessage.split()[0] == 'block' and len(recvmessage.split()) == 2:
                    if recvmessage.split()[1] not in userblocked:
                        sendmessage = 'Error. Invalid user'
                        self.clientsocket.send(sendmessage.encode())
                        #print(sendmessage)
                    elif recvmessage.split()[1] == self.username:
                        sendmessage = 'It is not allowed to block youself'
                        self.clientsocket.send(sendmessage.encode())
                        #print(sendmessage)                        
                    elif recvmessage.split()[1] not in userblocked[self.username]:
                        userblocked[self.username].append(recvmessage.split()[1])
                        #print(userblocked[self.username])
                        sendmessage = 'blocked ' + recvmessage.split()[1]
                        self.clientsocket.send(sendmessage.encode())
                        #print(sendmessage)
                    elif recvmessage.split()[1] in userblocked[self.username]:
                        sendmessage = 'This is a duplicated block'
                        self.clientsocket.send(sendmessage.encode())
                        #print(sendmessage)
                if recvmessage != '' and  recvmessage.split()[0] == 'block' and len(recvmessage.split()) != 2:
                    sendmessage = 'Error. Invalid command'
                    self.clientsocket.send(sendmessage.encode())

                # unblock.
                if recvmessage != '' and  recvmessage.split()[0] == 'unblock' and len(recvmessage.split()) != 2:
                    sendmessage = 'Error. Invalid command'
                    self.clientsocket.send(sendmessage.encode())                    
                if recvmessage != '' and  recvmessage.split()[0] == 'unblock' and len(recvmessage.split()) == 2:
                    if recvmessage.split()[1] not in userblocked:
                        sendmessage = 'Error. Invalid user'
                        self.clientsocket.send(sendmessage.encode())
                        #print(sendmessage)
                    elif recvmessage.split()[1] == self.username:
                        sendmessage = 'It is not allowed to unblock youself'
                        self.clientsocket.send(sendmessage.encode())
                        #print(sendmessage)                        
                    elif recvmessage.split()[1] in userblocked[self.username]:
                        userblocked[self.username].remove(recvmessage.split()[1])
                        #print(userblocked[self.username])
                        sendmessage = 'unblock ' + recvmessage.split()[1]
                        self.clientsocket.send(sendmessage.encode())
                        #print(sendmessage)
                    elif recvmessage.split()[1] not in userblocked[self.username]:
                        sendmessage = 'Invalid unblock. The user was not blocked'
                        self.clientsocket.send(sendmessage.encode())
                        #print(sendmessage)
                if recvmessage != '' and  recvmessage.split()[0] == 'block' and len(recvmessage.split()) != 2:
                    sendmessage = 'Error. Invalid command'
                    self.clientsocket.send(sendmessage.encode())

                # private message
                # startprivate
                if recvmessage != '' and recvmessage.split()[0] == 'startprivate' and len(recvmessage.split()) > 2:
                    #print(recvmessage.split()[1])
                    #print(userpwd)
                    if recvmessage.split()[1] not in userpwd:
                        sendmessage = 'startprivatefailed ' + ' The username does not exsit. Private messaging cannot be started'
                        self.clientsocket.send(sendmessage.encode())
                    elif userstatus[recvmessage.split()[1]] == 'offline':
                        sendmessage = 'startprivatefailed ' + recvmessage.split()[1] + ' is not online. Private messaging cannot be started'
                        self.clientsocket.send(sendmessage.encode())
                    elif self.username in userblocked[recvmessage.split()[1]]:
                        sendmessage = 'startprivatefailed Private message cannot be started as the recipient has blocked you'
                        self.clientsocket.send(sendmessage.encode())
                    elif privatewith[recvmessage.split()[1]] != '':
                        sendmessage = 'startprivatefailed Private message cannot be started as the recipient already has an active private connection'
                        self.clientsocket.send(sendmessage.encode())                        
                    elif recvmessage.split()[1] in userpwd and privatewith[recvmessage.split()[1]] == '' and userstatus[recvmessage.split()[1]] == 'online' and recvmessage.split()[1] != self.username and self.username not in userblocked[recvmessage.split()[1]]:
                        sendmessage = 'startprivate ' + self.username + ' ' + recvmessage.split()[2] + ' ' + recvmessage.split()[3]
                        privatewith[self.username] = recvmessage.split()[1]
                        privatewith[recvmessage.split()[1]] = self.username
                        dictusersocket[privatewith[self.username]].send(sendmessage.encode())

                        
                        
                if recvmessage != '' and  recvmessage.split()[0] == 'privateconfirmed' and len(recvmessage.split()) == 2:
                    sendmessage = 'startprivateconfirmed ' + self.username
                    dictusersocket[recvmessage.split()[1]].send(sendmessage.encode())

                if recvmessage != '' and  recvmessage.split()[0] == 'startprivaterejected' and len(recvmessage.split()) == 2:
                    sendmessage = 'startprivaterejected ' + self.username
                    privatewith[self.username] = ''
                    privatewith[recvmessage.split()[1]] = ''
                    dictusersocket[recvmessage.split()[1]].send(sendmessage.encode())


                # stopprivate
                if recvmessage != '' and  recvmessage.split()[0] == 'stopprivate' and len(recvmessage.split()) == 2:
                    if privatewith[self.username] == recvmessage.split()[1]:
                        sendmessage = 'stopprivate ' + self.username
                        dictusersocket[recvmessage.split()[1]].send(sendmessage.encode())                    
                        privatewith[self.username] = ''
                        privatewith[recvmessage.split()[1]] = ''
                        #print('sendmessage=', sendmessage)

                    
                # if the message from client is empty, the client would be off-line then set the client as offline (alive=Flase)
                if recvmessage == 'logout':
                    self.clientAlive = False
                    userlastlogouttime[self.username] = time.time()
                    #print("===== the user disconnected - ", dictsocketaddress[self.clientsocket])
                    # broadcast logout
                    for clientname in userpwd:
                        if clientname != self.username and self.username not in userblocked[clientname] and clientname not in userblocked[self.username] and userstatus[clientname] == 'online':
                            sendmessage = 'broadcast ' + self.username + ' logged out'
                            try:
                                dictusersocket[clientname].send(sendmessage.encode())
                                #print(self.username + ' broadcast: ' + recvmessage)
                            except:
                                #print(clientname, ' connection is broken.')
                                pass                    
                    # Notify p2p client disconnection
                    privatewith[privatewith[self.username]] = ''
                    privatewith[self.username] = ''
                    userstatus[self.username] = 'offline'
                    del dictsocketuser[self.clientsocket]
                    del dictusersocket[self.username]
                    self.clientsocket.close()
                    break

                if recvmessage == 'timeout':
                    self.clientAlive = False
                    userlastlogouttime[self.username] = time.time()
                    #print("===== the user disconnected - ", dictsocketaddress[self.clientsocket])
                    # broadcast logout
                    for clientname in userpwd:
                        if clientname != self.username and self.username not in userblocked[clientname] and clientname not in userblocked[self.username] and userstatus[clientname] == 'online':
                            sendmessage = 'broadcast ' + self.username + ' logged out'
                            try:
                                dictusersocket[clientname].send(sendmessage.encode())
                                #print(self.username + ' broadcast: ' + recvmessage)
                            except:
                                #print(clientname, ' connection is broken.')
                                pass                    
                    # Notify p2p client disconnection 
                    privatewith[privatewith[self.username]] = ''
                    privatewith[self.username] = ''
                    userstatus[self.username] = 'offline'
                    del dictsocketuser[self.clientsocket]
                    del dictusersocket[self.username]
                    self.clientsocket.close()
                    break                   


                # Check if the client has Ctrl + C to shut off the connection, then the server will keep on receiving recvmessage == ''
                # If the server received more than 10 times of recvmessage == '', then the server will logoff the user.
                if recvmessage == '':
                    x += 1
                    if x == 20:
                        self.clientAlive = False
                        userlastlogouttime[self.username] = time.time()
                        #print("===== the user disconnected - ", dictsocketaddress[self.clientsocket])
                        for clientname in userpwd:
                            if clientname != self.username and self.username not in userblocked[clientname] and clientname not in userblocked[self.username] and userstatus[clientname] == 'online':
                                sendmessage = 'broadcast ' + self.username + ' logged out'
                                try:
                                    dictusersocket[clientname].send(sendmessage.encode())
                                    #print(self.username + ' broadcast: ' + recvmessage)
                                except:
                                    #print(clientname, ' connection is broken.')
                                    pass
                        userstatus[self.username] = 'offline'
                        privatewith[strings[0]] = ''
                        del dictsocketuser[self.clientsocket]
                        del dictusersocket[self.username]
                        self.clientsocket.close()
                            


    def process_login(self, recvmessage):
        sendmessage = ''
#        print('userloginblock[clientusername] = ', userloginblock[recvmessage.split()[1]])
        # check if there is any username having empty password
        if recvmessage !='':
            if recvmessage.split()[0] == 'login' and recvmessage.split()[1] in userpwd.keys() and userloginblock[recvmessage.split()[1]] == False and userstatus[recvmessage.split()[1]] == 'offline':
                sendmessage = 'server: pwd'
                self.clientsocket.send(sendmessage.encode())
                #print('[send] ' + sendmessage)
            if recvmessage.split()[0] == 'login' and recvmessage.split()[1] in userpwd.keys() and userstatus[recvmessage.split()[1]] == 'online':
                sendmessage = 'server: Already online'
                self.clientsocket.send(sendmessage.encode())
                #print('[send] ' + sendmessage)                
                
            elif recvmessage.split()[0] == 'login' and recvmessage.split()[1] in userpwd.keys() and userloginblock[recvmessage.split()[1]] == True:
                sendmessage = 'server: log in during the block duration'
                self.clientsocket.send(sendmessage.encode())
                #print('[send] ' + sendmessage)
                self.clientAlive = False
            elif recvmessage.split()[0] == 'login' and recvmessage.split()[1] not in userpwd.keys():
                sendmessage= recvmessage.split()[1] + ' newuserpwd'
                self.clientsocket.send(sendmessage.encode())
                userpwd[recvmessage.split()[1]] = ''
                userloginblock[recvmessage.split()[1]] = False
                userloginfailedtimes[recvmessage.split()[1]] = 0
                #print('[send] ' + sendmessage)
            elif recvmessage.split()[0] == 'newuserpwd' and recvmessage.split()[1] in userpwd.keys():
                if (len(recvmessage.split())) == 2: # If the user input password is emtpy
                    userloginfailedtimes[recvmessage.split()[1]] += 1
                    if userloginfailedtimes[recvmessage.split()[1]] == 3:
                        #print('The client pwd has failed 3 times! The client will be blocked for 60 seconds from log in!')
                        sendmessage = 'loginblock' + str(self.block_duration)
                        self.clientsocket.send(sendmessage.encode())
                        userloginblock[recvmessage.split()[1]] = True
                        self.clientAlive = False
                        time.sleep(self.block_duration)
                        userloginblock[recvmessage.split()[1]] = False
                        userloginfailedtimes[recvmessage.split()[1]] = 0
                        #print('After time.sleep(60), userloginblock[recvmessage.split()[1]] = ', userloginblock[recvmessage.split()[1]])
                    else:
                        sendmessage= recvmessage.split()[1] + ' newuserpwdempty'
                        self.clientsocket.send(sendmessage.encode())
                        userpwd[recvmessage.split()[1]] = ''
                        userloginblock[strings[0]] = False
                        userloginfailedtimes[strings[0]] = 1
                        #print('[send] ' + sendmessage)
                elif (len(recvmessage.split())) > 2:
                    userpwd[recvmessage.split()[1]] = recvmessage.split()[2]
                    f = open('credentials.txt', "a")
                    f.write(userpwd[recvmessage.split()[1]] + ' ' + recvmessage.split()[2] + '\n') 
                    f.close()
                    self.username = recvmessage.split()[1]
                    self.login = True
                    sendmessage = 'loginsuccessfully ' + dictsocketaddress[self.clientsocket][0] + ' ' + str(dictsocketaddress[self.clientsocket][1])
                    #print(self.username, sendmessage)
                    self.clientsocket.send(sendmessage.encode())
                    # Initialize the information for the new user.
                    userstatus[self.username] = 'online' # To record the status of the user. There are two values, 'offline' and 'online'.
                    userblocked[self.username] = [] # To record the list of users who have blocked this user.
                    user1stlogin[self.username] = 1 # To record whether a user have logged in before/ whether it's the 1st time log in.
                    userlogintime[self.username] = [time.time(), time.time()] # To store the 1st login time and the last login time. Set the initial values.
                    userloginblock[self.username] = False
                    userloginfailedtimes[self.username] = 0
                    userlastlogouttime[self.username] = 0
                    privatewith[self.username] = ''
                    userofflinemessage[self.username] = []
                    dictusersocket[self.username] = self.clientsocket
                    dictsocketuser[self.clientsocket] = self.username

                    # start timeout
                    usertimer[self.username] = time.time()
                    #print('before timingThread')
                    timingThread = threading.Thread(target=TimingThread, args=(self.clientsocket,))
                    timingThread.start()
                    # New user login broadcast                        
                    for clientname in userpwd:
                        if clientname != self.username and self.username not in userblocked[clientname] and userstatus[clientname] == 'online':
                            sendmessage = 'broadcast ' + self.username + ' logged in'
                            try:
                                dictusersocket[clientname].send(sendmessage.encode())
                                #print(self.username + ' broadcast: ' + recvmessage)
                            except:
                                #print(clientname, ' connection is broken.')
                                pass                    

            # existing username login
            elif recvmessage.split()[0] == 'pwd' and len(recvmessage.split()) <=2: # If the user input password is empty
                userloginfailedtimes[recvmessage.split()[1]] += 1
                if userloginfailedtimes[recvmessage.split()[1]] == 3:
                    #print('The client pwd has failed 3 times! The client will be blocked for 60 seconds from log in!')
                    sendmessage = 'loginblock ' + str(self.block_duration)
                    self.clientsocket.send(sendmessage.encode())
                    userloginblock[recvmessage.split()[1]] = True
                    self.clientAlive = False
                    time.sleep(self.block_duration)
                    userloginblock[recvmessage.split()[1]] = False
                    userloginfailedtimes[recvmessage.split()[1]] = 0
                    #print('After time.sleep(60), userloginblock[recvmessage.split()[1]] = ', userloginblock[recvmessage.split()[1]])
                    self.clientsocket.close()
                else:
                    sendmessage = 'server: pwd wrong'
                    #print(sendmessage);
                    self.clientsocket.send(sendmessage.encode())  
            elif recvmessage.split()[0] == 'pwd' and len(recvmessage.split()) >2 and userpwd[recvmessage.split()[1]] == recvmessage.split()[2] and userloginblock[recvmessage.split()[1]] == False:
                self.username = recvmessage.split()[1]
                self.login = True
                sendmessage = 'loginsuccessfully ' + dictsocketaddress[self.clientsocket][0] + ' ' + str(dictsocketaddress[self.clientsocket][1])
                #print(self.username, sendmessage)
                self.clientsocket.send(sendmessage.encode())
                userstatus[self.username] = 'online'
                dictusersocket[self.username] = self.clientsocket
                dictsocketuser[self.clientsocket] = self.username
                usertimer[self.username] = time.time()
                #print('before timingThread')
                timingThread = threading.Thread(target=TimingThread, args=(self.clientsocket,))
                timingThread.start()
                #print('after timingThread')
                #broadcast login
                for clientname in userpwd:
                    if clientname != self.username and self.username not in userblocked[clientname] and clientname not in userblocked[self.username] and userstatus[clientname] == 'online':
                        sendmessage = 'broadcast ' + self.username + ' logged in'
                        try:
                            dictusersocket[clientname].send(sendmessage.encode())
                            #print(self.username + ' broadcast: ' + recvmessage)
                        except:
                            #print(clientname, ' connection is broken.')
                            pass                    

                #print('login usertimer[self.username] = ', usertimer[self.username])
                #print('login success, timer = time.time()', self.timer)
                if user1stlogin[self.username] == 0:
                    userlogintime[self.username][0] = time.time()
                    userlogintime[self.username][1] = time.time()
                else:
                    userlogintime[self.username][1] = time.time()
                #print('userlogintime[self.username] = ', userlogintime[self.username])
                
                # Check Offline message after login
                #print('userofflinemessage[self.username]) =', userofflinemessage[self.username])
                if len(userofflinemessage[self.username]) != 0:
                    for msg in userofflinemessage[self.username]:
                        self.clientsocket.send(msg.encode())
                        time.sleep(0.1)
                        #print(msg)
                    userofflinemessage[self.username] = [] # After sending the offline message, empty the list.
            
            # Password failed three times, then block the user.
            elif recvmessage.split()[0] == 'pwd' and userpwd[recvmessage.split()[1]] != recvmessage.split()[2] and userloginblock[recvmessage.split()[1]] == False:
                userloginfailedtimes[recvmessage.split()[1]] += 1
                if userloginfailedtimes[recvmessage.split()[1]] == 3:
                    #print('The client pwd has failed 3 times! The client will be blocked for 60 seconds from log in!')
                    sendmessage = 'loginblock ' + str(self.block_duration)
                    self.clientsocket.send(sendmessage.encode())
                    #print(sendmessage)
                    userloginblock[recvmessage.split()[1]] = True
                    self.clientAlive = False
                    time.sleep(self.block_duration)
                    userloginblock[recvmessage.split()[1]] = False
                    userloginfailedtimes[recvmessage.split()[1]] = 0
                    #print('After time.sleep(60), userloginblock[recvmessage.split()[1]] = ', userloginblock[recvmessage.split()[1]])
                    self.clientsocket.close()
                else:
                    sendmessage = 'server: pwd wrong'
                    #print(sendmessage);
                    self.clientsocket.send(sendmessage.encode())  

    def whoelse(self, recvmessage):
        sendmessage = ''
        if recvmessage == 'whoelse':
            for key in userstatus:
                if userstatus[key] == 'online' and key != self.username and self.username not in userblocked[key]:
                    if sendmessage =='':
                        sendmessage = sendmessage + key
                    elif sendmessage !='':
                        sendmessage = sendmessage + ' ' + key
            sendmessage = 'whoelse ' + sendmessage
            self.clientsocket.send(sendmessage.encode())
            #print(self.username + ' whoelse: ' + sendmessage)


    def whoelsesince(self, recvmessage):
        sendmessage = ''
        if len(recvmessage.split()) == 2 and recvmessage.split()[0] == 'whoelsesince' and recvmessage.split()[1].isnumeric():
            for key in userstatus:
                if userstatus[key] == 'online' and key != self.username and self.username not in userblocked[key]:
                    if sendmessage =='':
                        sendmessage = sendmessage + key
                    elif sendmessage !='':
                        sendmessage = sendmessage + ' ' + key
                elif userstatus[key] == 'offline' and key != self.username and self.username not in userblocked[key]:
                    if time.time() - userlastlogouttime[key] <= int(recvmessage.split()[1]):
                        if sendmessage =='':
                            sendmessage = sendmessage + key
                        elif sendmessage !='':
                            sendmessage = sendmessage + ' ' + key                        
            sendmessage = 'whoelsesince ' + sendmessage
            self.clientsocket.send(sendmessage.encode())
            #print(self.username + ' whoelsesince: ' + sendmessage)
        elif recvmessage != '' and recvmessage.split()[0] == 'whoelsesince':
            if len(recvmessage.split()) != 2 or recvmessage.split()[1].isnumeric():
                sendmessage = 'Error. Invalid command'
                self.clientsocket.send(sendmessage.encode())


#--- Main ---     
def receive():
    while True:
        clientsocket_accept, address = serversocket.accept()
        clientsocket = context.wrap_socket(clientsocket_accept, server_side=True)
        #clientsocket.setblocking(0)
        dictsocketaddress[clientsocket] = address
#        clientsocket.send('you are now connected!'.encode('utf-8'))
        clientThread = ClientThread(clientsocket)
        clientThread.start()
        #clientThreadTimer = ClientThreadTimer(clientsocket)
        #clientThreadTimer.start()
if __name__ == '__main__':
    receive()

