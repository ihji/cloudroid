#!/usr/bin/env python

import daemon
from flask import Flask,render_template

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('status.html',
           status_map = daemon.client_status,
           analysis_queue = daemon.analysis_queue)

if __name__ == '__main__':
    daemon.launch()
    app.run()
