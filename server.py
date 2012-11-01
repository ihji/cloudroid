#!/usr/bin/env python

import zmq
from Queue import Queue
from threading import Thread
import signal

job_queue = Queue()
analysis_queue = Queue()

class ClientResponder(Thread):
    def __init__(self,socket):
        Thread.__init__(self)
        self.socket = socket
    def run(self):
        print("ClientResponder started.")
        while True:
            msg = self.socket.recv()
            if msg == "update":
                print("put queue update")
                job_queue.put(msg)
                self.socket.send("Got "+msg)

class ServerWorker(Thread):
    def __init__(self,socket):
        Thread.__init__(self)
        self.socket = socket
    def run(self):
        print("ServerWorker started.")
        while True:
            job = job_queue.get()
            if job == "update":
                print("get update from queue")
                self.socket.send("update")
            job_queue.task_done()


class WorkerResponder(Thread):
    def __init__(self,socket):
        Thread.__init__(self)
        self.socket = socket
    def run(self):
        print("WorkerResponder started.")
        while True:
            address = self.socket.recv()
            self.socket.recv()
            msg = self.socket.recv()
            print(msg)
            self.socket.send(address,zmq.SNDMORE)
            self.socket.send("",zmq.SNDMORE)
            self.socket.send("Got "+msg)

def main():
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

    server_thread = ServerWorker(backend_cast)
    server_thread.daemon = True
    server_thread.start()

    worker_thread = WorkerResponder(backend)
    worker_thread.daemon = True
    worker_thread.start()

    signal.pause()

    # infinite loop!

if __name__ == "__main__":
    main();
