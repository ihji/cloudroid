#!/usr/bin/env python

import zmq
from cmd import WREQ

TRANSFER_BUF = 512000

def send_file(socket,path,loc,address=None):
    fn = open(path,"rb")
    fn.seek(loc)
    data = fn.read(TRANSFER_BUF)
    if address:
        socket.send(address,zmq.SNDMORE)
        socket.send("",zmq.SNDMORE)
    socket.send_pyobj({'cmd':WREQ.REP_FILE,'path':path,'body':data})
    fn.close()

def write_req_file(socket,path,data,target,address=None):
    if data:
        t = open(target, 'a')
        t.write(data)
        loc = t.tell()
        if address:
            socket.send(address,zmq.SNDMORE)
            socket.send("",zmq.SNDMORE)
        socket.send_pyobj({'cmd':WREQ.REQ_FILE,'path':path,'loc':loc})
        t.close()
    else:
        socket.send_pyobj({'cmd':WREQ.DONE})
