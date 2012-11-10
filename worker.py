#!/usr/bin/env python

import zmq
from droidblaze import Droidblaze
from Queue import Queue,Empty
from threading import Thread
import fileutil
import signal
from cmd import WREQ,SPUB
import os
import shutil
from os import path
import uuid
import time
import sys
from datetime import datetime

SERVER_ADDRESS = "localhost"

SERVER = "tcp://{}:7980".format(SERVER_ADDRESS)
SERVER_CAST = "tcp://{}:7981".format(SERVER_ADDRESS)

DROIDBLAZE_DIST = "droidblaze.tgz"

msg_queue = Queue()
status = "init"
update_status = False
stop_analyze = False

class CastReceiver(Thread):
    def __init__(self,socket,workerid):
        Thread.__init__(self)
        self.socket = socket
        self.workerid = workerid
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
            elif cmd == SPUB.UPDATE_STATUS:
                global update_status
                update_status = True
            elif cmd == SPUB.NOTIFY_STOP:
                global stop_analyze
                if msg['address'] == self.workerid:
                    stop_analyze = True

class Worker(Thread):
    def __init__(self,socket,workerid,workdir):
        Thread.__init__(self)
        self.socket = socket
        self.workerid = workerid
        self.workdir = workdir
    def report_status(self):
        global update_status
        if update_status:
            self.socket.send_pyobj({'cmd':WREQ.STATUS,'status':status})
            msg = self.socket.recv_pyobj()
            update_status = False
    def filetransfer(self):
        global status
        status = "file transfer"
        while True:
            msg = self.socket.recv_pyobj()
            cmd = msg['cmd']
            self.report_status()
            if cmd == WREQ.REP_FILE:
                fileutil.write_req_file(self.socket,msg['path'],msg['target'],self.workdir,msg['body'])
            elif cmd == WREQ.REQ_FILE:
                fileutil.send_file(self.socket,msg['path'],msg['target'],msg['loc'])
            elif cmd == WREQ.DONE:
                break
            else:
                print("what?? "+cmd)
    def analyzer_run(self,a):
        global status,stop_analyze
        init_time = datetime.now()
        stop_analyze = False
        p = a.run(self.workdir)
        ret = p.poll()
        while ret == None:
            elapsed_time = datetime.now() - init_time
            status = "analyze {}: {} ({})".format(a.analysis_id,a.target_apk,elapsed_time)
            self.report_status()
            if stop_analyze:
                p.terminate()
            time.sleep(1)
            ret = p.poll()
        return ret
    def cleanup(self):
        shutil.rmtree(self.workdir)
    def run(self):
        global status
        print("Worker started")
        while True:
            status = "ready"
            self.report_status()
            try:
                msg = msg_queue.get(True,1)
            except Empty:
                continue
            cmd = msg['cmd']
            print("next cmd: "+cmd)
            if cmd == SPUB.NOTIFY_UPDATE:
                dist = path.join(self.workdir,DROIDBLAZE_DIST)
                if os.path.exists(dist):
                    dist_md5 = fileutil.getmd5(dist)
                else:
                    dist_md5 = None
                if not msg['md5'] == dist_md5:
                    self.cleanup()
                    self.socket.send_pyobj({'cmd':WREQ.REQ_FILE,'path':msg['path'],'target':DROIDBLAZE_DIST,'loc':0})
                    self.filetransfer()
                    fileutil.untar(self.workdir,DROIDBLAZE_DIST)
                    print("updated")
                else:
                    print("already up to date")
            elif cmd == SPUB.ANALYZE_APP:
                self.socket.send_pyobj({'cmd':WREQ.REQ_ANALYSIS})
                res = self.socket.recv_pyobj()
                if res['cmd'] == WREQ.REP_ANALYSIS:
                    a = res['droidblaze']
                    app = path.join(self.workdir,a.target_apk)
                    f = open(app, 'w')
                    f.write(res['app'])
                    f.close()
                    ret = self.analyzer_run(a)
                    app_tgz = path.splitext(a.target_apk)[0]+".tgz"
                    a.tar_result(self.workdir,app_tgz)
                    fileutil.send_file(self.socket,path.join(self.workdir,app_tgz),path.join(a.analysis_id,self.workerid,app_tgz),0)
                    self.filetransfer()
                    msg_queue.put({'cmd':SPUB.ANALYZE_APP})
                    self.socket.send_pyobj({'cmd':WREQ.FIN_ANALYSIS,'droidblaze': a,'result':path.join(self.workerid,app_tgz),'status':ret})
                    res = self.socket.recv_pyobj()
            else:
                print("what?: "+cmd)
            msg_queue.task_done()

def main():
    if len(sys.argv) < 2:
        print("Give me a worker name!\n")

    worker_postfix = sys.argv[1]

    WORKER_ID="{}_{}".format(hex(uuid.getnode()),worker_postfix)
    WORK_DIR="temp_"+WORKER_ID

    if not path.exists(WORK_DIR):
        os.makedirs(WORK_DIR)
    else:
        print("Warning: working directory already exists. Be sure that another worker with the same name is not running on this machine.\n")

    context = zmq.Context(1)
    cast_socket = context.socket(zmq.SUB)
    cast_socket.connect(SERVER_CAST)
    cast_socket.setsockopt(zmq.SUBSCRIBE,"")
    req_socket = context.socket(zmq.REQ)
    req_socket.setsockopt(zmq.IDENTITY,WORKER_ID)
    req_socket.connect(SERVER)

    receiver_thread = CastReceiver(cast_socket,WORKER_ID)
    receiver_thread.daemon = True
    receiver_thread.start()

    worker_thread = Worker(req_socket,WORKER_ID,WORK_DIR)
    worker_thread.daemon = True
    worker_thread.start()

    while True:
        signal.pause()

    # infinite loop

if __name__ == "__main__":
    main()
