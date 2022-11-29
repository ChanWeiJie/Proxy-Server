import sys
import time
from _thread import *
from socket import *

BUFFER_SIZE = 8192
TIMEOUT = 10
UPDATERATE = 1
IMAGESUBLINK = b'http://ocna0.d2.comp.nus.edu.sg:50000/change.jpg'
ATTACKRESPONSE = b'200 OK\r\n\r\n<html>\n<body>\nYou are being attacked!\n</body>\n</html>\n'
INVALIDHTTP = b'HTTP/1.1 400 Bad Request\r\n\r\n\n'
HTTPNOTFOUND = b'<html>\n<body>\n404 Not Found\n</body>\n</html>\n'
DICT = {}
portNum = int(sys.argv[1])
isSubstitude = int(sys.argv[2])
isAttack = int(sys.argv[3])


# function to see if HTTP request is valid
def checkHTTP(data):
    try:
        validFunctions = [b'GET', b'HEAD', b'POST', b'PUT', b'DELETE', b'TRACE', b'OPTIONS', b'CONNECT']
        validHTTPVersions = [b'HTTP/1.1', b'HTTP/1.0']
        isFunctionValid = False
        isHTTPVersionValid = False
        isBeginFromRoot = False
        isHostHeaderPresent = False

        data_Split = data.split(b'\n')
        first_line = data_Split[0].split()
        function = first_line[0]
        url = first_line[1]
        httpVersion = first_line[2]

        http_pos = url.find(b'://')  # Finding the position of ://

        if http_pos == -1:
            temp = url
        else:
            temp = url[(http_pos + 3):]  # get the rest of url

        if temp.find(b'/') != -1:
            isBeginFromRoot = True

        if function in validFunctions:
            isFunctionValid = True

        if httpVersion in validHTTPVersions:
            isHTTPVersionValid = True

        if isHTTPVersionValid and httpVersion == b'HTTP/1.1':
            try:
                second_line = data_Split[1].split()
                hostHeader = second_line[0]
                if hostHeader == b'Host:':
                    isHostHeaderPresent = True
            except Exception as e:
                return False

        if isHTTPVersionValid and httpVersion == b'HTTP/1.0':
            isHostHeaderPresent = True

        return isFunctionValid and isHTTPVersionValid and isBeginFromRoot and isHostHeaderPresent

    except IndexError:
        return False


def replacePicture(data):
    validPictureTypes = [b'apng', b'avif', b'gif', b'jpg', b'jpeg', b'jfif', b'pjpeg', b'pjp', b'png', b'svg', b'webp',
                         b'ico', b'bmp', b'cur', b'tif', b'tiff']
    first_line = data.split(b'\n')[0]
    url = first_line.split()[1]
    requestedPic = url.split(b'/')[-1]
    extension = (requestedPic.split(b'.')[-1]).lower()

    # check extension
    if extension in validPictureTypes:
        data = data.replace(url, IMAGESUBLINK)
    return data


def craftAttackMessage(data):
    first_line = data.split(b'\n')[0]
    httpVersion = first_line.split()[2]
    message = httpVersion + ATTACKRESPONSE
    return message


def connDetails(clientSocket, clientAddr, data):  # Parsing the URL
    data = data.replace(b'Connection: keep-alive', b'Connection: close')  # Change to non persistent
    first_line = data.split(b'\n')[0]
    url = first_line.split()[1]
    http_pos = url.find(b'://')  # Finding the position of ://

    if http_pos == -1:
        temp = url
    else:
        temp = url[(http_pos + 3):]  # get the rest of url

    port_pos = temp.find(b':')  # find the port pos
    webserver_pos = temp.find(b'/')

    if webserver_pos == -1:
        webserver_pos = len(temp)
    if port_pos == -1 or webserver_pos < port_pos:
        port = 80
        webserver = temp[:webserver_pos]
    else:
        port = int((temp[(port_pos + 1):])[:webserver_pos - port_pos - 1])
        webserver = temp[:port_pos]

    refererURL = None
    # Check if its a referer request (Referer field is used to determine if a request are from the same webpage)
    if data.find(b'Referer: ') != -1:
        refererURL = data.split(b'Referer: ')[1].split(b'\r\n')[0]

    connectToActualServer(webserver, port, clientSocket, clientAddr, data, url, refererURL)


def connectToActualServer(webserver, port, clientSocket, clientAddr, data, url, refererURL):
    isAbleToPrint = False
    originalURL = None

    if refererURL is None:  # Original Website
        # dict is <((url, clientIP) , (data size, timeout value))>
        DICT[(url, clientAddr[0])] = (0, TIMEOUT)
        isAbleToPrint = True
        originalURL = url
    else:
        if (refererURL, clientAddr[0]) not in DICT:
            DICT[(refererURL, clientAddr[0])] = (0, TIMEOUT)
            isAbleToPrint = True
        originalURL = refererURL

    webserverSocket = socket(AF_INET, SOCK_STREAM)

    try:
        webserverSocket.connect((webserver, port))
    except Exception as e:
        clientSocket.sendall(HTTPNOTFOUND)
        clientSocket.shutdown(SHUT_RDWR)
        clientSocket.close()
        if isAbleToPrint:
            del DICT[(originalURL, clientAddr[0])]
        return

    webserverSocket.send(data)
    finalPacket = b''
    dataSize = 0

    while True:
        reply = webserverSocket.recv(BUFFER_SIZE)
        if len(reply) > 0:
            finalPacket = finalPacket + reply
            clientSocket.send(reply)
        else:
            clientSocket.shutdown(SHUT_RDWR)
            break

        # For every item sent, refresh the timmer
        size = DICT[(originalURL, clientAddr[0])][0]
        DICT[(originalURL, clientAddr[0])] = (size, TIMEOUT)

    # Proxy Closing the connections
    webserverSocket.close()
    clientSocket.close()

    packetBody = finalPacket.split(b'\r\n\r\n')
    if len(packetBody) > 1:
        dataSize = len(packetBody[1])

    # update the size in my key value pair
    updateSize = DICT[(originalURL, clientAddr[0])][0] + dataSize
    remainingTime = DICT[(originalURL, clientAddr[0])][1]
    DICT[(originalURL, clientAddr[0])] = (updateSize, remainingTime)

    if isAbleToPrint:
        # Finish the time (internal timeout)
        while DICT[(originalURL, clientAddr[0])][1] > 0:
            updateSize = DICT[(originalURL, clientAddr[0])][0]
            remainingTime = DICT[(originalURL, clientAddr[0])][1] - UPDATERATE
            DICT[(originalURL, clientAddr[0])] = (updateSize, remainingTime)

            # Acutally pausing for 1 second
            time.sleep(UPDATERATE)

        updateSize = DICT[(originalURL, clientAddr[0])][0]
        print(originalURL.decode("utf-8") + ",", updateSize) # Print Telemetry
        if (originalURL, clientAddr[0]) in DICT.items(): # check if item exist before deleting
            del DICT[(originalURL, clientAddr[0])]


def start():
    serverSocket = socket(AF_INET, SOCK_STREAM)  # Create socket
    serverSocket.bind(('', portNum))  # bind socket
    serverSocket.listen()  # listen for incommming TCP reqeuest

    try:
        while True:
            clientSocket, clientAddr = serverSocket.accept()
            data = clientSocket.recv(BUFFER_SIZE)
            isValid = checkHTTP(data)

            if isValid:
                if isAttack:
                    clientSocket.sendall(craftAttackMessage(data))
                    clientSocket.close()
                    continue
                elif isSubstitude:
                    data = replacePicture(data)
                start_new_thread(connDetails, (clientSocket, clientAddr, data))
            else:
                clientSocket.sendall(INVALIDHTTP)
                clientSocket.close()
                continue
    except KeyboardInterrupt:
        serverSocket.close()
        sys.exit(0)


start()
