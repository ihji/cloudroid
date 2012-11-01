#!/usr/bin/env python

from subprocess import Popen
import sys

class Droidblaze:
    java = "java"
    droidblaze_jar = "droidblaze-core-1.0-SNAPSHOT-jar-with-dependencies.jar"
    sdk_dir = "android-sdk"
    jvm_option = "-Xmx2048M"
    debug_option = "-Ddroidblaze.debug.consolemsg=1"

    def __init__(self,work_dir,target,analyses):
        self.target_apk = target
        self.run_analyses = analyses
        self.work_dir = work_dir
    def run(self):
        cmd = []
        cmd.append(self.java)
        cmd.append(self.jvm_option)
        cmd.append(self.debug_option)
        cmd.append("-Ddroidblaze.sdkdir={}".format(self.sdk_dir))
        cmd.append("-Ddroidblaze.target.apk={}".format(self.target_apk))
        cmd.append("-Ddroidblaze.run.analyses={}".format(self.run_analyses))
        cmd.append("-jar")
        cmd.append(self.droidblaze_jar)
        Popen(cmd,cwd=self.work_dir).wait()

if __name__ == "__main__":
    dr = Droidblaze(sys.argv[1],sys.argv[2],sys.argv[3])
    dr.run()
