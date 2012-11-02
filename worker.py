#!/usr/bin/env python

import zmq
from droidblaze import Droidblaze
from Queue import Queue
from threading import Thread
import fileutil
import signal
from cmd import WREQ,SPUB
import os
import shutil
from os import path
import uuid

server = "tcp://localhost:7980"
server_cast = "tcp://localhost:7981"

WORK_DIR = "temp"
WORKER_ID = hex(uuid.getnode())

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
    def filetransfer(self):
        while True:
            msg = self.socket.recv_pyobj()
            cmd = msg['cmd']
            if cmd == WREQ.REP_FILE:
                fileutil.write_req_file(self.socket,msg['path'],msg['target'],WORK_DIR,msg['body'])
            elif cmd == WREQ.REQ_FILE:
                fileutil.send_file(self.socket,msg['path'],msg['target'],msg['loc'])
            elif cmd == WREQ.DONE:
                break
            else:
                print("what?? "+cmd)
    def cleanup(self):
        shutil.rmtree(WORK_DIR)
    def run(self):
        self.cleanup()
        print("Worker started")
        while True:
            print("getting from queue")
            msg = msg_queue.get()
            cmd = msg['cmd']
            print("next cmd: "+cmd)
            if cmd == SPUB.NOTIFY_UPDATE:
                self.socket.send_pyobj({'cmd':WREQ.REQ_FILE,'path':msg['path'],'target':msg['target'],'loc':0})
                self.filetransfer()
                fileutil.untar(WORK_DIR,msg['target'])
            elif cmd == SPUB.ANALYZE_APP:
                self.socket.send_pyobj({'cmd':WREQ.REQ_ANALYSIS})
                res = self.socket.recv_pyobj()
                msg_queue.put(res)
            elif cmd == WREQ.REP_ANALYSIS:
                a = msg['droidblaze']
                app = path.join(WORK_DIR,a.target_apk)
                f = open(app, 'w')
                f.write(msg['app'])
                f.close()
                a.run(WORK_DIR)
                fileutil.tar_result(WORK_DIR,"droidblaze_output.tgz")
                fileutil.send_file(self.socket,path.join(WORK_DIR,"droidblaze_output.tgz"),path.join(a.analysis_id,WORKER_ID,"droidblaze_output.tgz"),0)
                self.filetransfer()
                msg_queue.put({'cmd':SPUB.ANALYZE_APP})
            msg_queue.task_done()

def main():
    if not path.exists(WORK_DIR):
        os.makedirs(WORK_DIR)
    context = zmq.Context(1)
    cast_socket = context.socket(zmq.SUB)
    cast_socket.connect(server_cast)
    cast_socket.setsockopt(zmq.SUBSCRIBE,"")
    req_socket = context.socket(zmq.REQ)
    req_socket.setsockopt(zmq.IDENTITY,WORKER_ID)
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
