#!/usr/bin/env python

import zmq,sys,filetransfer

server = "tcp://localhost:7979"

def main():
    context = zmq.Context(1)
    socket = context.socket(zmq.REQ)
    socket.connect(server)

    socket.send("update")

    msg = socket.recv()
    print(msg)

    socket.close()

if __name__ == "__main__":
    main()
