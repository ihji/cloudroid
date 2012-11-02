#!/usr/bin/env python

import zmq,sys
from cmd import CREQ

server = "tcp://localhost:7979"

def main():
    context = zmq.Context(1)
    socket = context.socket(zmq.REQ)
    socket.connect(server)

    socket.send_pyobj({'cmd':CREQ.NOTIFY_UPDATE,'file':"droidblaze.tgz"})
    msg = socket.recv()
    print(msg)

    socket.send_pyobj({'cmd':CREQ.ANALYZE_APP})
    msg = socket.recv()
    print(msg)

    socket.close()

if __name__ == "__main__":
    main()
