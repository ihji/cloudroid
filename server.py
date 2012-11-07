#!/usr/bin/env python

import daemon
from flask import Flask,render_template

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('status.html')

@app.route('/workerlist')
def workerlist():
    wlist = ""
    for status in daemon.client_status.items():
        wlist += "<tr><td>{}</td><td>{}</td></tr>\n".format(status[0],status[1])
    return wlist

@app.route('/queuesize')
def queuesize():
    return str(daemon.analysis_queue.qsize())

if __name__ == '__main__':
    daemon.launch()
    app.run()
