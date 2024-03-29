#!/usr/bin/env python

import zmq
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
client_status = {}
updated_client = set()

WORK_DIR = "server_temp"

class ClientResponder(Thread):
    def __init__(self,socket):
        Thread.__init__(self)
        self.socket = socket
    def existingResults(self,analysisID):
        analysisDir = path.join(WORK_DIR,analysisID)
        dirs = []
        if not path.exists(analysisDir):
            return set()
        for f in os.listdir(analysisDir):
            if f.startswith("0x") and path.isdir(path.join(analysisDir,f)):
                dirs.append(path.join(analysisDir,f))
        apks = set()
        for d in dirs:
            for r in os.listdir(d):
                if r.endswith(".tgz"):
                    apks.add(r.replace(".tgz",".apk"))
        return apks
    def run(self):
        print("ClientResponder started.")
        while True:
            msg = self.socket.recv_pyobj()
            cmd = msg['cmd']
            print("received from client: "+cmd)
            if cmd == CREQ.NOTIFY_UPDATE:
                cast_queue.put(msg)
                self.socket.send("notified")
            elif cmd == CREQ.NOTIFY_ANALYZE:
                cast_queue.put({'cmd':CREQ.ANALYZE_APP})
                self.socket.send("notified")
            elif cmd == CREQ.NOTIFY_STOP:
                cast_queue.put(msg)
                self.socket.send("notified")
            elif cmd == CREQ.ANALYZE_APP:
                existing = self.existingResults(msg['id'])
                if msg['apk'] not in existing:
                    a = Droidblaze(msg['id'],msg['apk'],msg['task'])
                    app = path.join(WORK_DIR,msg['apk'])
                    analysis_queue.put({'droidblaze':a,'file':app})
                    cast_queue.put(msg)
                    self.socket.send("queued")
                else:
                    self.socket.send("analysis result already exists: {}".format(msg['apk']))
            elif cmd == CREQ.ANALYZE_DIR:
                target_dir = msg['dir']
                existing = self.existingResults(msg['id'])
                answer = ["queued"]
                for f in os.listdir(target_dir):
                    if f.endswith(".apk"):
                        if f not in existing:
                            a = Droidblaze(msg['id'],f,msg['task'])
                            app = path.join(target_dir,f)
                            analysis_queue.put({'droidblaze':a,'file':app})
                        else:
                            answer.append("analysis result already exists: {}".format(f))
                cast_queue.put({'cmd':CREQ.ANALYZE_APP})
                self.socket.send("\n".join(answer))
            elif cmd == CREQ.REPORT_STATUS:
                self.socket.send("report: {}".format(client_status))
            elif cmd == CREQ.EMPTY_ANALYSIS_QUEUE:
                with analysis_queue.mutex:
                    analysis_queue.queue.clear()
                self.socket.send("done")

class ServerCaster(Thread):
    def __init__(self,socket):
        Thread.__init__(self)
        self.socket = socket
    def rutineJobs(self):
        for c in client_status.keys():
            if c not in updated_client:
                client_status.pop(c)
        updated_client.clear()
        self.socket.send_pyobj({'cmd':SPUB.UPDATE_STATUS}) # heartbeat
    def run(self):
        print("ServerCaster started.")
        while True:
            self.rutineJobs()
            try:
                msg = cast_queue.get(True,10)
            except Empty:
                continue
            cmd = msg['cmd']
            print("next cmd: "+cmd)
            if cmd == CREQ.NOTIFY_UPDATE:
                md5 = fileutil.getmd5(msg['file'])
                self.socket.send_pyobj({'cmd':SPUB.NOTIFY_UPDATE,'path':msg['file'],'md5':md5})
            elif cmd == CREQ.ANALYZE_APP:
                self.socket.send_pyobj({'cmd':SPUB.ANALYZE_APP})
            elif cmd == CREQ.NOTIFY_STOP:
                self.socket.send_pyobj({'cmd':SPUB.NOTIFY_STOP,'address':msg['address']})
            cast_queue.task_done()


class WorkerResponder(Thread):
    def __init__(self,socket):
        Thread.__init__(self)
        self.socket = socket
    def run(self):
        print("WorkerResponder started.")
        while True:
            address = self.socket.recv()
            self.socket.recv()
            msg = self.socket.recv_pyobj()
            cmd = msg['cmd']

            worker_dir = path.join(WORK_DIR,address)

            print("received from {}: {}".format(address,cmd))
            if cmd == WREQ.REQ_FILE:
                fileutil.send_file(self.socket,msg['path'],msg['target'],msg['loc'],address)
            elif cmd == WREQ.REP_FILE:
                fileutil.write_req_file(self.socket,msg['path'],msg['target'],WORK_DIR,msg['body'],address)
            elif cmd == WREQ.REQ_ANALYSIS:
                try:
                    w = analysis_queue.get_nowait()
                    a = w['droidblaze']
                    # TODO: get apk from somewhere and transfer with message
                    app = w['file']
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
            elif cmd == WREQ.FIN_ANALYSIS:
                a = msg['droidblaze']
                ret = msg['status']
                fileutil.untar(path.join(WORK_DIR,a.analysis_id),msg['result'])
                a.merging_summary(path.join(WORK_DIR,a.analysis_id),ret)
                self.socket.send(address,zmq.SNDMORE)
                self.socket.send("",zmq.SNDMORE)
                self.socket.send_pyobj({'cmd':WREQ.DONE})
            elif cmd == WREQ.DONE:
                self.socket.send(address,zmq.SNDMORE)
                self.socket.send("",zmq.SNDMORE)
                self.socket.send_pyobj({'cmd':WREQ.DONE})
            elif cmd == WREQ.STATUS:
                status = msg['status']
                client_status[address] = status
                updated_client.add(address)
                self.socket.send(address,zmq.SNDMORE)
                self.socket.send("",zmq.SNDMORE)
                self.socket.send_pyobj({'cmd':WREQ.DONE})

            else:
                print("what?: "+cmd)
 
def launch():
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

def main():

    launch()

    while True:
        signal.pause()

    # infinite loop!

if __name__ == "__main__":
    main()
