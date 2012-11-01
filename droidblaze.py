#!/usr/bin/env python

from subprocess import Popen

class Droidblaze:
    java = "java"
    droidblaze_jar = "droidblaze-core-1.0-SNAPSHOT-jar-with-dependencies.jar"
    sdk_dir = "android-sdk"
    target_apk = "SyncMyPix.apk"
    run_analyses = "generate-cpcg"
    jvm_option = "-Xmx2048M"
    debug_option = "-Ddroidblaze.debug.consolemsg=1"
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
        Popen(cmd,cwd="temp").wait()

if __name__ == "__main__":
    dr = Droidblaze()
    dr.run()
