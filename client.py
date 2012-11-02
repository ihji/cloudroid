#!/usr/bin/env python

import zmq,sys
from cmd import CREQ
import time

server = "tcp://localhost:7979"

def main():
    context = zmq.Context(1)
    socket = context.socket(zmq.REQ)
    socket.connect(server)

#    socket.send_pyobj({'cmd':CREQ.NOTIFY_UPDATE,'file':"droidblaze.tgz"})
#    msg = socket.recv()
#    print(msg)
#
#    socket.send_pyobj({'cmd':CREQ.ANALYZE_APP,'id':"test",'apk':"SyncMyPix.apk",'task':"generate-cpcg"})
#    msg = socket.recv()
#    print(msg)

#    socket.send_pyobj({'cmd':CREQ.ANALYZE_DIR,'id':"test",'dir':"server_temp",'task':"generate-cpcg"})
#    msg = socket.recv()
#    print(msg)

    socket.send_pyobj({'cmd':CREQ.UPDATE_STATUS})
    msg = socket.recv()
    print(msg)
    time.sleep(2)
    socket.send_pyobj({'cmd':CREQ.REPORT_STATUS})
    msg = socket.recv()
    print(msg)

    socket.close()

if __name__ == "__main__":
    main()
