"""
    Python 3
    Usage: python3 client.py port 
    coding: utf-8
    
    Author: Huaizheng Zhang (Assignment for COMP6481)
"""
import socket
import threading
import sys, select
import time
import ssl
#import errno

# acquire server host and port from command line parameter
if len(sys.argv) != 2:
    print("\n===== Error usage, python3 client.py SERVER_PORT ======\n");
    exit(0);
serverHost = "127.0.0.1"
serverPort = int(sys.argv[1])
serverAddress = (serverHost, serverPort)
#clientsocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)    # The socket between client and server
#clientsocket.connect(serverAddress)     # The connection between client and server

clientsocket_AF_INET = socket.socket(socket.AF_INET) #HZ
context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
context.minimum_version = ssl.TLSVersion.TLSv1_2
context.maximum_version = ssl.TLSVersion.TLSv1_3
context.check_hostname = False
context.verify_mode=ssl.CERT_NONE

clientsocket = context.wrap_socket(clientsocket_AF_INET, server_hostname=serverHost)
clientsocket.connect((serverHost, serverPort))


#context.get_ciphers() #HZ
print(clientsocket.cipher()) # !!! Print the cipher method used in the connection.

#p2paddress = ('', 0)
privateHostAddr = "127.0.0.1"
privateHostPort = 0
privatestatus = ['off', '', '']
#p2pstatus = 'off'
#privatehostaddress = ['', 0]
# For example: privatestatus = ['on', 'hans', 'client'] This is means that another client initiate a startprivate request to hans
# privatestatus = ['on', 'hans', 'host'] This is that hans initiates a startprivate request to another client
# privatestatus is a list has three items. First is 'off'/'verifying'/'on', second item is the username the client is privatewith
# Third item has two values, 'host' or 'client'. 
# If a user initiate startprivate, it will be a client.
# If a user accept the start private request, it will be a server.

datareceiver = [clientsocket, sys.stdin]

pwdtrialtimes = 0
receivedMessage = ''
sendMessage = ''


def client_receive():
    status = 'offline'
    button = 'off'
    task = 'username'
    #privatereply = ''
    p2pInitiatesocket = socket.socket()
    p2phostwelcomesocket = socket.socket()
    tostopsocket = socket.socket()
    emptynumber = 0
    p2phostaddress = ('', 0)
    threadAlive = True
    global receivedMessage
    global clientsocket
    global clientPort
    global privatestatus
    global p2paddress
    #global p2pstatus
    while threadAlive:
        if status == 'offline' and task == 'username':
            message = input("Username:")
            username = message
            message = 'login ' + message
            clientsocket.sendall(message.encode())
            receivedMessage = clientsocket.recv(1024).decode('utf-8')
            task = 'pwd'

        elif receivedMessage == 'server: Already online': # concurrently already login
            print('The account has already been active in another terminal!\nThe username cannot be used concurrently by two clients!')
            message = input("Please enter a non-active username:")
            username = message
            message = 'login ' + message
            clientsocket.sendall(message.encode())
            receivedMessage = clientsocket.recv(1024).decode('utf-8')
            task = 'pwd'

        elif receivedMessage == 'server: log in during the block duration': # login during block duration
            print('Error. Log in failed during block duration!')
            clientsocket.close()
            break

        # Existing user
        elif status == 'offline' and receivedMessage == "server: pwd":  # username valid, server requires pwd
            message = input("Password:")
            message = 'pwd ' + username + ' ' + message
            #print('client: ', message)
            clientsocket.sendall(message.encode())
            receivedMessage = clientsocket.recv(1024).decode('utf-8')
            #print(receivedMessage)
            status = 'verifying'
        elif receivedMessage == "server: pwd wrong" or receivedMessage == "server: pwdempty":    # username valid, pwd wrong
            print('Invalid Password. Please try again')
            message = input("Password:")
            message = 'pwd ' + username + ' ' + message
            #print('client: ', message)
            clientsocket.sendall(message.encode())
            receivedMessage = clientsocket.recv(1024).decode('utf-8')
            status = 'verifying'

        elif len(receivedMessage.split())>=2 and receivedMessage.split()[0] == 'loginblock': # pws failed 3 times.
            print('Password has failed 3 times! The account will be blocked for ' + receivedMessage.split()[1] + ' seconds.')
            clientsocket.close()
            break
        
        # New user
        elif len(receivedMessage.split())>=2 and receivedMessage.split()[1] == 'newuserpwd': # message from server = newusername + ' newuserpwd'
            message = input("This is a new user. Enter a password:")
            message = 'newuserpwd ' + receivedMessage.split()[0] + ' ' + message
            #print('client: ', message)
            clientsocket.sendall(message.encode())
            receivedMessage = clientsocket.recv(1024).decode('utf-8')
            status = 'verifying'
        elif len(receivedMessage.split())>=2 and receivedMessage.split()[1] == 'newuserpwdempty':
            message = input("Password can't be empty. Enter a password:")
            message = 'newuserpwd ' + receivedMessage.split()[0] + ' ' + message
            #print('client: ', message)
            clientsocket.sendall(message.encode())
            receivedMessage = clientsocket.recv(1024).decode('utf-8')
            status = 'verifying'
        elif status == 'verifying' and receivedMessage.split()[0] == "loginsuccessfully":    # Client log in successfully.
            status = 'online'
            #clientPort = int(receivedMessage.split()[2])
            p2phostwelcomesocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            welcomehostaddress = (privateHostAddr, 0)    # Operation system will random bind a free port
            p2phostwelcomesocket.bind(welcomehostaddress)
            privateHostPort = p2phostwelcomesocket.getsockname()[1]
            p2phostwelcomesocket.listen(10)
            print("Welcome to the greatest messaging application ever!")
            #print(p2phostwelcomesocket)
        
        if button == 'on':
            privaterequest = privatestatus[1] + ' would like to private message, enter y or n:'
            privatereply = input(privaterequest)
            if privatereply == 'y' and privatestatus[0] == 'verifying':
                msg = 'privateconfirmed ' + privatestatus[1]
                clientsocket.sendall(msg.encode())
                #privateclientsocket.connect(p2paddress)

                ########################### P2P connection ####################
                p2pAcceptsocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                p2pAcceptsocket.connect(p2phostaddress)
                datareceiver.append(p2pAcceptsocket)
                privatestatus[0] = 'on'
                receivedMessage = 'noprint'
            #if privatestatus[0] == 'verifying' and privatereply == 'n':
            if privatereply == 'n' and privatestatus[0] == 'verifying':
                sendMessage = 'startprivaterejected ' + privatestatus[1]
                clientsocket.sendall(sendMessage.encode())
                privatestatus = ['off', '', '']
            button ='off'
        
      
        if status == 'online':
            try:
                readyinput, readyoutput, readyexception = select.select(datareceiver, [], [])
            except:
                break
            for datasource in readyinput:
                if datasource != sys.stdin:
                    #print(datasource)
                    receivedMessage = datasource.recv(1024).decode('utf-8')
                    if receivedMessage == '':
                        tostopsocket = datasource
                        emptynumber += 1
                    if not receivedMessage:
                        break
                    #print('receivedMessage=', receivedMessage)
                    #print(receivedMessage.split()[0])
                    #print(receivedMessage.split()[1])
                    #print(receivedMessage.split())
                    #print('message = ', message)
                else:
                    message = input()
                    if message != '':
                        if message == 'logout':
                            # first check p2p and close p2p if it's active
                            if privatestatus[0] == 'on': # received from server that the private function will be closed.
                                # because startprivate is thourgh server, stopprivate is also through server.
                                if privatestatus[2] == 'Accept':
                                    p2pAcceptsocket.sendall('p2pclose'.encode())
                                    time.sleep(0.1)
                                    datareceiver.remove(p2pAcceptsocket)
                                    p2pAcceptsocket.close()                                    
                                if privatestatus[2] == 'Initiate':
                                    p2pInitiatesocket.sendall('p2pclose'.encode())
                                    time.sleep(0.1)
                                    datareceiver.remove(p2pInitiatesocket)
                                    p2pInitiatesocket.close()
                                privatestatus = ['off', '', '']
                            # logout from server
                            status == 'offline'
                            clientsocket.sendall(message.encode())
                            time.sleep(0.1)
                            clientsocket.close()
                            break
                        elif message.split()[0] != 'private' and message.split()[0] != 'startprivate' and message.split()[0] != 'stopprivate' and message != 'y' and message != 'n':
                            clientsocket.sendall(message.encode())
                        elif message.split()[0] == 'private' and len(message.split()) < 3:
                            print('Error command. private <user> <message>')                       
                        elif message.split()[0] == 'private' and privatestatus[0] == 'on' and privatestatus[1] != message.split()[1]:
                            print('Error. The private message cannot be sent to ' + message.split()[1])
                        elif message.split()[0] == 'private' and privatestatus[0] == 'on' and privatestatus[2] == 'Accept':
                            p2pAcceptsocket.sendall(message.encode())
                            clientsocket.sendall('private'.encode())
                        elif message.split()[0] == 'private' and privatestatus[0] == 'on' and privatestatus[2] == 'Initiate':
                            p2pInitiatesocket.sendall(message.encode())
                            clientsocket.sendall('private'.encode())
                        elif message.split()[0] == 'private' and privatestatus[0] == 'off':
                            print('The private message is not active')
                        elif message.split()[0] == 'startprivate' and len(message.split()) != 2:
                            print('Error command. startprivate <user>')
                        elif message.split()[0] == 'startprivate' and message.split()[1] == username:
                            print('Error. The private message cannot start with yourself.')
                        elif message.split()[0] == 'startprivate' and privatestatus[0] == 'on':
                            print('Error. You have already had an active private connection')
                        elif message.split()[0] == 'startprivate' and privatestatus[0] == 'off' and message.split()[1] != username:
                            privatestatus = ['verifying', message.split()[1], 'Initiate']
                            sendMessage = message + ' ' + privateHostAddr + ' ' + str(privateHostPort)    # sendMessage = 'startprivate hans addr port'
                            clientsocket.sendall(sendMessage.encode())
                        elif message.split()[0] == 'stopprivate' and len(message.split()) != 2:
                            print('Error command. stopprivate <user>')
                        elif message.split()[0] == 'stopprivate' and len(message.split()) == 2:
                            if message.split()[1] != privatestatus[1] or privatestatus[0] != 'on':
                                print('Error. Cannot stopprivate with ' + message.split()[1])
                            elif message.split()[1] == privatestatus[1] and privatestatus[0] == 'on': # received from server that the private function will be closed.
                    # because startprivate is thourgh server, stopprivate is also through server.
                                clientsocket.sendall(message.encode())
                                time.sleep(0.1)
                                # This is important!!! Otherwise, this end firstly, and then the other side will keep on/repeatly receiving '' empty message will replace other recvmessage.
                                if privatestatus[2] == 'Accept':
                                    datareceiver.remove(p2pAcceptsocket)
                                    p2pAcceptsocket.close()
                                    #print('p2pAcceptsocket.close()')
                                if privatestatus[2] == 'Initiate':
                                    datareceiver.remove(p2pInitiatesocket)
                                    p2pInitiatesocket.close()
                                    #print('p2pInitiatesocket.close()')
                                privatestatus = ['off', '', '']
                                print('Private messaging is disconnected.')
                    else:
                        pass
                            
#-------------------------------------------------------------------------------------------------

            # When the client receive a startprivate request from the server, it will become a privatecliensocket if reply 'y'
            if len(receivedMessage.split()) > 1 and receivedMessage.split()[0] == 'startprivate':
                #print(receivedMessage)
                privatestatus = ['verifying', receivedMessage.split()[1], 'Accept']
                p2phostaddress = (receivedMessage.split()[2], int(receivedMessage.split()[3]))
                button = 'on'
                receivedMessage = 'noprint'
                #privaterequest = privatestatus[1] + ' would like to private message, enter y or n:'
                #privatereply = input(privaterequest)
                #receivedMessage = 'noprint'
            #if privatestatus[0] == 'verifying' and privatereply == 'y':     #message == 'y':   

               
            if privatestatus[0] == 'verifying' and receivedMessage.split()[0] == 'startprivateconfirmed':
                p2pInitiatesocket, p2pAcceptaddress = p2phostwelcomesocket.accept()
                datareceiver.append(p2pInitiatesocket)
                receivedMessage = 'noprint'
                if p2pInitiatesocket:
                    print(privatestatus[1] + ' accepts private messaging')
                    privatestatus[0] = 'on'
                    privatestatus[2] = 'Initiate'


            if privatestatus[0] == 'verifying' and receivedMessage.split()[0] == 'startprivaterejected':
                receivedMessage = 'noprint'
                print(privatestatus[1] + ' rejects private messaging')
                privatestatus = ['off', '', '']

 
            if privatestatus[0] == 'verifying' and receivedMessage.split()[0] == 'startprivatefailed':
                printmessage = " ".join(receivedMessage.split()[1:])
                print(printmessage)
                privatestatus = ['off', '', '']
                receivedMessage = 'noprint'


            # stopprivate
            if len(receivedMessage.split()) == 2 and receivedMessage.split()[0] == 'stopprivate': # received from server that the private function will be closed.
                # because startprivate is thourgh server, stopprivate is also through server.
                if receivedMessage.split()[1] == privatestatus[1]:
                    if privatestatus[2] == 'Accept':
                        datareceiver.remove(p2pAcceptsocket)
                        p2pAcceptsocket.close()
                        #print('p2pInitiatesocket.close()')
                        print('Private message is disconnected')
                    if privatestatus[2] == 'Initiate':
                        datareceiver.remove(p2pInitiatesocket)
                        p2pInitiatesocket.close()
                        #print('p2pInitiatesocket.close()')
                        print('Private message is disconnected')
                    receivedMessage = 'noprint'
                    privatestatus = ['off', '', '']

            if emptynumber > 10:
                if privatestatus[2] == 'Accept':
                    if tostopsocket == p2pAcceptsocket:
                        datareceiver.remove(p2pAcceptsocket)
                        p2pAcceptsocket.close()
                        print('emptynumber p2pInitiatesocket.close()')
                        print('Private message is disconnected')
                if privatestatus[2] == 'Initiate':
                    if tostopsocket == p2pInitiatesocket:                    
                        datareceiver.remove(p2pInitiatesocket)
                        p2pInitiatesocket.close()
                        print('emptynumber p2pInitiatesocket.close()')
                        print('Private message is disconnected')
                receivedMessage = 'noprint'
                privatestatus = ['off', '', '']
                emptynumber = 0
                    
            if receivedMessage == 'p2pclose': # received from server that the private function will be closed.
                # because startprivate is thourgh server, stopprivate is also through server.
                if privatestatus[0] == 'on':
                    printmessage = privatestatus[1] + ' logged out, private chat concluding'
                    if privatestatus[2] == 'Accept':
                        datareceiver.remove(p2pAcceptsocket)
                        p2pAcceptsocket.close()
                        print(printmessage)
                        #print('p2pInitiatesocket.close()')
                    if privatestatus[2] == 'Initiate':
                        datareceiver.remove(p2pInitiatesocket)
                        p2pInitiatesocket.close()
                        print(printmessage)
                        #print('p2pInitiatesocket.close()')
                    privatestatus = ['off', '', '']
                    receivedMessage = 'noprint'
                    
            #private message
            elif len(receivedMessage.split()) > 2 and receivedMessage.split()[0] == 'private':
                if privatestatus[0] == 'on' and username == receivedMessage.split()[1]:
                    privatemessage = privatestatus[1]+'(private): ' + " ".join(receivedMessage.split()[2:])
                    receivedMessage = 'noprint' 
                    print(privatemessage)

            # Broadcast                
            elif len(receivedMessage.split()) > 1 and receivedMessage.split()[0] == 'broadcast':
                 messageprint = ' '.join(receivedMessage.split()[1:])
                 print(messageprint)
                 receivedMessage = 'noprint'

            # Timeout
            elif receivedMessage == 'server: timeout': # Client timeout
                # first check p2p and close p2p if it's active
                if privatestatus[0] == 'on': # received from server that the private function will be closed.
                    # because startprivate is thourgh server, stopprivate is also through server.
                    if privatestatus[2] == 'Accept':
                        p2pAcceptsocket.sendall('p2pclose'.encode())
                        time.sleep(0.1)
                        datareceiver.remove(p2pAcceptsocket)
                        p2pAcceptsocket.close()                                    
                    if privatestatus[2] == 'Initiate':
                        p2pInitiatesocket.sendall('p2pclose'.encode())
                        time.sleep(0.1)
                        datareceiver.remove(p2pInitiatesocket)
                        p2pInitiatesocket.close()
                    privatestatus = ['off', '', '']
                # server timeout
                print('Timeout. The account will be automatically log out.')
                clientsocket.sendall('timeout'.encode())
                receivedMessage = 'noprint'
                status == 'offline'
                clientsocket.close()
                break
            
            #whoelse
            elif len(receivedMessage.split()) >= 1 and receivedMessage.split()[0] == 'whoelse':
                if len(receivedMessage.split()) == 1:
                    print('Nobody else is online.')
                elif len(receivedMessage.split()) > 1:
                    for i in range(len(receivedMessage.split())-1):
                        print(receivedMessage.split()[i+1])
                receivedMessage = 'noprint'
            
            #whoelsesince
            elif len(receivedMessage.split()) >= 1 and receivedMessage.split()[0] == 'whoelsesince':
                if len(receivedMessage.split()) == 1:
                    print('Nobody else is or was online.')
                elif len(receivedMessage.split()) > 1:
                    for i in range(len(receivedMessage.split())-1):
                        print(receivedMessage.split()[i+1])
                receivedMessage = 'noprint'
                
            elif len(receivedMessage.split()) > 1 and receivedMessage.split()[0] == 'message':   # 'message hans: good morning! How are you?
                #for i in range(len(receivedMessage.split())-1):
                 messageprint = ' '.join(receivedMessage.split()[1:])
                 print(messageprint)
                 receivedMessage = 'noprint'
            elif receivedMessage == 'Error. Invalid user':
                print(receivedMessage)
                receivedMessage = 'noprint'
            elif receivedMessage == 'Error. Invalid command':
                print(receivedMessage)
                receivedMessage = 'noprint'
            #block
            elif len(receivedMessage.split()) == 2 and receivedMessage.split()[0] == 'blocked':   # 'blocked username'
                 messageprint = receivedMessage.split()[1] + ' is blocked'
                 print(messageprint)
                 receivedMessage = 'noprint'
            elif receivedMessage == 'Your message could not be delivered as the recipient has blocked you':
                print(receivedMessage)
                receivedMessage = 'noprint'
            elif receivedMessage == 'Your message could not be delivered to some recipients':
                print(receivedMessage)
                receivedMessage = 'noprint'
            elif receivedMessage == 'It is not allowed to block youself':
                print(receivedMessage)
                receivedMessage = 'noprint'
            elif receivedMessage == 'This is a duplicated block':
                print(receivedMessage)
                receivedMessage = 'noprint'
            #unblock
            elif len(receivedMessage.split()) == 2 and receivedMessage.split()[0] == 'unblock':   # 'blocked username'
                 messageprint = receivedMessage.split()[1] + ' is unblocked'
                 print(messageprint)
                 receivedMessage = 'noprint'
            elif receivedMessage == 'It is not allowed to unblock youself':
                print(receivedMessage)
                receivedMessage = 'noprint'
            elif receivedMessage == 'Invalid unblock. The user was not blocked':
                print(receivedMessage)
                receivedMessage = 'noprint'

#---------------------------------------------------------------------------------------------------------------
            elif receivedMessage == 'server: loginblock':   # username valid, three times failed pwd. The counter will be blocked for block_duration.
                print('Invalid Password. Your account has been blocked. Please try again later')
                receivedMessage = 'noprint'
                status = 'offline'
                break
            elif receivedMessage == 'server: log in during the block duration': # Client tries to log in within the block_duration.
                print('Your account is blocked due to multiple login failures. Please try again later')
                receivedMessage = 'noprint'
                status = 'offline'
                break
            elif receivedMessage == 'noprint':
                pass
            else:
                pass             





receive_thread = threading.Thread(target=client_receive)
receive_thread.start()





