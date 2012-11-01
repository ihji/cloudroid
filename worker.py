#!/usr/bin/env python

import zmq
from droidblaze import Droidblaze
from Queue import Queue
from threading import Thread
import filetransfer
import signal
from cmd import WREQ,SPUB
import os
from os import path

server = "tcp://localhost:7980"
server_cast = "tcp://localhost:7981"

work_dir = "temp"

msg_queue = Queue()

class CastReceiver(Thread):
    def __init__(self,socket):
        Thread.__init__(self)
        self.socket = socket
    def run(self):
        print("CastReceiver started")
        while True:
            msg = self.socket.recv_pyobj()
            cmd = msg['cmd']
            print("received: "+cmd)
            if cmd == SPUB.NOTIFY_UPDATE:
                msg_queue.put(msg)
            elif cmd == SPUB.ANALYZE_APP:
                msg_queue.put(msg)

class Worker(Thread):
    def __init__(self,socket):
        Thread.__init__(self)
        self.socket = socket
    def run(self):
        print("Worker started")
        while True:
            msg = msg_queue.get()
            cmd = msg['cmd']
            print("next cmd: "+cmd)
            if cmd == SPUB.NOTIFY_UPDATE:
                self.socket.send_pyobj({'cmd':WREQ.REQ_FILE,'path':msg['path'],'loc':0})
            elif cmd == SPUB.ANALYZE_APP:
                self.socket.send_pyobj({'cmd':WREQ.REQ_ANALYSIS})
            elif cmd == WREQ.REP_ANALYSIS:
                a = msg['droidblaze']
                a.run()
                self.socket.send_pyobj({'cmd':WREQ.REQ_ANALYSIS})
            elif cmd == WREQ.REP_FILE:
                filetransfer.write_req_file(self.socket,msg['path'],msg['body'],path.join(work_dir,msg['path']))
            elif cmd == WREQ.REQ_FILE:
                filetransfer.send_file(self.socket,msg['path'],msg['loc'])
            msg_queue.task_done()
            res = self.socket.recv_pyobj()
            if not res['cmd'] == WREQ.DONE:
                msg_queue.put(res)

def main():
    if not path.exists(work_dir):
        os.makedirs(work_dir)
    context = zmq.Context(1)
    cast_socket = context.socket(zmq.SUB)
    cast_socket.connect(server_cast)
    cast_socket.setsockopt(zmq.SUBSCRIBE,"")
    req_socket = context.socket(zmq.REQ)
    req_socket.connect(server)

    receiver_thread = CastReceiver(cast_socket)
    receiver_thread.daemon = True
    receiver_thread.start()

    worker_thread = Worker(req_socket)
    worker_thread.daemon = True
    worker_thread.start()

    while True:
        signal.pause()

    # infinite loop

if __name__ == "__main__":
    main()
