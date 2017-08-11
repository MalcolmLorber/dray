#!/usr/bin/python3

import socket
import sys
import json
import threading

DEFAULTPORT=50000

#debug print function
def dprint(s):
    if hasattr(dprint, 'number'):
        sys.stderr.write("%02d: %s"%(dprint.number, s) + '\n')
    else:
        sys.stderr.write(str(s)+'\n')

#Generates the neighbor mapping on each node
def findneighbors(treefile, ipfile, number):
    """Magic black box that I don't understand after writing"""
    with open(ipfile,'r') as f:
        neighbors = ['0.0.0.0'] + json.loads(f.read())
    with open(treefile,'r') as f:
        lines = filter(lambda l: str(number) in l, f.read().split('\n'))
        edges = [eval(l) for l in lines]

    # return in form {n: (ip,port)}
    ips = {n: neighbors[n] for n in [e[0] if e[0] != number else e[1] for e in edges]}
    connections = {n: (neighbors[n], DEFAULTPORT + neighbors[:n].count(neighbors[n])) for n in ips}
    port = DEFAULTPORT + neighbors[:number].count(neighbors[number])
    # debug
    dprint(connections)
    return connections, port

#create a distributed file
def createfile(filename, neighbors, locks, ldata, srcnum, number):
    #check for file and create if it does not exist
    if filename in locks:
        return

    locks[filename] = srcnum
    ldata[filename] = ''
    dprint("Locks: %s"%str(locks))
    
    #update all our neighbors about the new file
    for n in neighbors:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(neighbors[n])
        s.send(("%2d"%number) + "crt " + filename)
        s.close()

#delte a distributed file
def delfile(filename, neighbors, locks, ldata, number):
    #check for file and delte it if it exists
    if not filename in locks:
        return

    del locks[filename]
    dprint("Locks: %s"%str(locks))
    
    #update all our neighbors to delte the file
    for n in neighbors:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(neighbors[n])
        s.send(("%2d"%number) + "del " + filename)
        s.close()

#local command line parsing function
def parsecmd(cmd, neighbors, locks, ldata, con, number):
    command = cmd.split(' ')[0]
    if command == "create":
        # this assumes no spaces in filenames or other invalid characters
        filename = cmd.split(' ')[1]
        createfile(filename, neighbors, locks, ldata, 0, number)
    elif command == "delete":
        # this assumes no spaces in filenames or other invalid characters
        filename = cmd.split(' ')[1]
        acquirelock(locks, neighbors, filename, ldata, number)
        ldata[filename] = ''
        delfile(filename, neighbors, locks, ldata, number)

    elif command == "read":
        #dont need to do anything fancy or distributed here, just spit out the file
        if len(cmd.split(' ')) < 2:
            print("read requires filename")
            return
        filename = cmd.split(' ')[1]
        acquirelock(locks, neighbors, filename, ldata, number)
        if not filename in locks:
            return
        print(ldata[filename])

    elif command == "append":
        if len(cmd.split(' ')) < 2:
            print("append requires filename")
            return
        filename = cmd.split(' ')[1]
        line = cmd[len(" append " + filename):] + '\n'
        acquirelock(locks, neighbors, filename, ldata, number)
        if not filename in locks:
            return
        ldata[filename] += line

#core function to acquire the lock on a file so we may change it
def acquirelock(locks, neighbors, filename, ldata, number):
    if not filename in locks:
        dprint("No such file %s"%filename)
        return

    if locks[filename] != 0:
        dprint("Attempting to acquire lock from %d"%locks[filename])
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(neighbors[locks[filename]])
        s.send(("%2d"%number) + "acq " + filename)
        ldata[filename] = s.recv(2**16)[4:]
        locks[filename] = 0
        s.close()
        dprint("Acquired lock for %s"%filename)
    else:
        dprint("Already have lock for %s"%filename)

#local thread for listening for messages from our neighbors
def listenloop(neighbors, port, number):
    locks = {}
    ldata = {}
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('0.0.0.0', port))
    s.listen(5)

    while True:
        con,address = s.accept()
        msg = con.recv(2**16)

        dprint("recieved: %s"%msg)
        srcnum = int(msg[:2])

        # try:
        if msg[2:6] == "cmd ":
            parsecmd(msg[6:], neighbors, locks, ldata, con, number)
            # Command line interface parsing

        elif msg[2:6] == "crt ":
            createfile(msg[6:],neighbors, locks, ldata, srcnum, number)
            # Check if file exists
            # Create file command. Foreward to all neighbors

        elif msg[2:6] == "del ":
            delfile(msg[6:],neighbors, locks, ldata, number)
            # Delete file command. Do same as above

        elif msg[2:6] == "acq ":
            acquirelock(locks, neighbors, msg[6:], ldata, number)
            con.send("lol " + ldata[msg[6:]])
            locks[msg[6:]] = srcnum
            del ldata[msg[6:]]
            # Get the lock, give to the connecting socket

        # except Exception as e:
        #     dprint("Error: %s"%str(e))


#local console input loop
def commandloop(port, number):
    cmd = ''
    while cmd != "quit":
        cmd = raw_input("%d> "%number)

        if len(cmd) > 1:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect(('127.0.0.1',port))
            s.send("0 cmd " + cmd)
            s.close()

#init function, create our local console thread and network listening thread and move on
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: %s <id_num>" % sys.argv[0])
        sys.exit(1)
    number = int(sys.argv[1])
    dprint.number = number
    neighbors,port = findneighbors("tree.txt", "ips.json", number)

    listenthread = threading.Thread(target=listenloop, args=(neighbors, port, number))
    listenthread.start()

    commandloop(port, number)
