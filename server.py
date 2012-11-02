#!/usr/bin/env python

import zmq
import binascii
from Queue import Queue,Empty
from threading import Thread
import signal
import fileutil
from cmd import CREQ,WREQ,SPUB
import os
from os import path
from droidblaze import Droidblaze

cast_queue = Queue()
analysis_queue = Queue()

WORK_DIR = "server_temp"

class ClientResponder(Thread):
    def __init__(self,socket):
        Thread.__init__(self)
        self.socket = socket
    def run(self):
        print("ClientResponder started.")
        while True:
            msg = self.socket.recv_pyobj()
            cmd = msg['cmd']
            print("received from client: "+cmd)
            if cmd == CREQ.NOTIFY_UPDATE:
                cast_queue.put(msg)
                self.socket.send("notified")
            elif cmd == CREQ.ANALYZE_APP:
                a = Droidblaze("test","SyncMyPix.apk","generate-cpcg")
                analysis_queue.put(a)
                cast_queue.put(msg)
                self.socket.send("queued")

class ServerCaster(Thread):
    def __init__(self,socket):
        Thread.__init__(self)
        self.socket = socket
    def run(self):
        print("ServerCaster started.")
        while True:
            msg = cast_queue.get()
            cmd = msg['cmd']
            print("next cmd: "+cmd)
            if cmd == CREQ.NOTIFY_UPDATE:
                self.socket.send_pyobj({'cmd':SPUB.NOTIFY_UPDATE,'path':"droidblaze.tgz",'target':"droidblaze.tgz"})
            elif cmd == CREQ.ANALYZE_APP:
                self.socket.send_pyobj({'cmd':SPUB.ANALYZE_APP})
            cast_queue.task_done()


class WorkerResponder(Thread):
    def __init__(self,socket):
        Thread.__init__(self)
        self.socket = socket
    def getWorkerName(self,address):
        is_text = True
        for c in address:
            if ord(c) < 32 or ord(c) > 128:
                is_text = False
                break
        if is_text:
            # print only if ascii text
            return address
        else:
            # not text, print hex
            return binascii.hexlify(address)
    def run(self):
        print("WorkerResponder started.")
        while True:
            address = self.socket.recv()
            self.socket.recv()
            msg = self.socket.recv_pyobj()
            cmd = msg['cmd']

            worker = self.getWorkerName(address)
            worker_dir = path.join(WORK_DIR,worker)

            print("received from {}: {}".format(worker,cmd))
            if cmd == WREQ.REQ_FILE:
                fileutil.send_file(self.socket,msg['path'],msg['target'],msg['loc'],address)
            elif cmd == WREQ.REP_FILE:
                fileutil.write_req_file(self.socket,msg['path'],msg['target'],WORK_DIR,msg['body'],address)
            elif cmd == WREQ.REQ_ANALYSIS:
                try:
                    a = analysis_queue.get_nowait()
                    # TODO: get apk from somewhere and transfer with message
                    app = path.join(WORK_DIR,a.target_apk)
                    f = open(app,'rb')
                    app_data = f.read()
                    f.close()
                    self.socket.send(address,zmq.SNDMORE)
                    self.socket.send("",zmq.SNDMORE)
                    self.socket.send_pyobj({'cmd':WREQ.REP_ANALYSIS,'droidblaze':a,'app':app_data})
                except Empty:
                    self.socket.send(address,zmq.SNDMORE)
                    self.socket.send("",zmq.SNDMORE)
                    self.socket.send_pyobj({'cmd':WREQ.DONE})
            elif cmd == WREQ.DONE:
                self.socket.send(address,zmq.SNDMORE)
                self.socket.send("",zmq.SNDMORE)
                self.socket.send_pyobj({'cmd':WREQ.DONE})
                    


def main():
    if not path.exists(WORK_DIR):
        os.makedirs(WORK_DIR)

    context = zmq.Context(1)

    frontend = context.socket(zmq.REP)
    frontend.bind("tcp://*:7979")
    backend = context.socket(zmq.ROUTER)
    backend.bind("tcp://*:7980")
    backend_cast = context.socket(zmq.PUB)
    backend_cast.bind("tcp://*:7981")

    client_thread = ClientResponder(frontend)
    client_thread.daemon = True
    client_thread.start()

    server_thread = ServerCaster(backend_cast)
    server_thread.daemon = True
    server_thread.start()

    worker_thread = WorkerResponder(backend)
    worker_thread.daemon = True
    worker_thread.start()

    while True:
        signal.pause()

    # infinite loop!

if __name__ == "__main__":
    main();
