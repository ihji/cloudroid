#!/usr/bin/env python

TRANSFER_BUF = 1024000

def push_file(socket,path):
    fn = open(path,"rb")

    while True:
        msg = socket.recv_pyobj()
        fn.seek(msg['loc'])
        data = fn.read(TRANSFER_BUF)
        socket.send_pyobj({'body':data})
        if not data:
            break

def get_file(socket,path):
    t = open(path, 'w+')
    msg = {'loc' : 0}

    while True:
        socket.send_pyobj(msg)
        data = socket.recv_pyobj()
        if data['body']:
            t.write(data['body'])
            msg['loc'] = t.tell()
        else:
            break
