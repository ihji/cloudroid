#!/usr/bin/env python

import zmq
from droidblaze import Droidblaze
from Queue import Queue
from threading import Thread
import filetransfer
import signal

server = "tcp://localhost:7980"
server_cast = "tcp://localhost:7981"

job_queue = Queue()

class Receiver(Thread):
    def __init__(self,socket):
        Thread.__init__(self)
        self.socket = socket
    def run(self):
        print("Receiver started")
        while True:
            msg = self.socket.recv()
            if msg == "update":
                print("put queue update")
                job_queue.put(msg)

class Worker(Thread):
    def __init__(self,socket):
        Thread.__init__(self)
        self.socket = socket
    def run(self):
        print("Worker started")
        while True:
            job = job_queue.get()
            if job == "update":
                self.socket.send("request update!")
                res = self.socket.recv()
                print(res)
            job_queue.task_done()

def main():
    context = zmq.Context(1)
    cast_socket = context.socket(zmq.SUB)
    cast_socket.connect(server_cast)
    cast_socket.setsockopt(zmq.SUBSCRIBE,"")
    req_socket = context.socket(zmq.REQ)
    req_socket.connect(server)

    receiver_thread = Receiver(cast_socket)
    receiver_thread.daemon = True
    receiver_thread.start()

    worker_thread = Worker(req_socket)
    worker_thread.daemon = True
    worker_thread.start()

    signal.pause()

    # infinite loop

if __name__ == "__main__":
    main()
