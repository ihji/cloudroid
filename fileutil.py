#!/usr/bin/env python

import zmq
from cmd import WREQ
import os
from subprocess import Popen
import hashlib

TRANSFER_BUF = 512000
FILEUTIL_DIR = os.path.dirname(__file__)

def send_file(socket,path,target,loc,address=None):
    fn = open(path,"rb")
    fn.seek(loc)
    data = fn.read(TRANSFER_BUF)
    if address:
        socket.send(address,zmq.SNDMORE)
        socket.send("",zmq.SNDMORE)
    socket.send_pyobj({'cmd':WREQ.REP_FILE,'path':path,'target':target,'body':data})
    fn.close()

def write_req_file(socket,path,target_path,work_dir,data,address=None):
    if data:
        target = os.path.join(work_dir,target_path)
        if not os.path.exists(os.path.dirname(target)):
            os.makedirs(os.path.dirname(target))
        t = open(target, 'a')
        t.write(data)
        loc = t.tell()
        t.close()
        if address:
            socket.send(address,zmq.SNDMORE)
            socket.send("",zmq.SNDMORE)
        socket.send_pyobj({'cmd':WREQ.REQ_FILE,'path':path,'target':target_path,'loc':loc})
    else:
        if address:
            socket.send(address,zmq.SNDMORE)
            socket.send("",zmq.SNDMORE)
        socket.send_pyobj({'cmd':WREQ.DONE})

def tar(work_dir,outfile,target):
    cmd = []
    cmd.append("tar")
    cmd.append("cvzf")
    cmd.append(outfile)
    cmd.append(target)
    Popen(cmd,cwd=work_dir).wait()

def untar(work_dir,infile):
    cmd = []
    cmd.append("tar")
    cmd.append("xvf")
    cmd.append(infile)
    Popen(cmd,cwd=work_dir).wait()

def getmd5(f):
    md5 = hashlib.md5()
    with open(f,'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            md5.update(chunk)
    return md5.digest()

def saxon(work_dir,outfile,xmlfile,xslfile):
    cmd = []
    cmd.append("java")
    cmd.append("-cp")
    cmd.append(os.path.join(FILEUTIL_DIR,"saxon9he.jar"))
    cmd.append("net.sf.saxon.Transform")
    cmd.append("-o:"+outfile)
    cmd.append(xmlfile)
    cmd.append(xslfile)
    Popen(cmd,cwd=work_dir).wait()
