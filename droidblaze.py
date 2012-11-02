#!/usr/bin/env python

from subprocess import Popen
import sys
from os import path
import shutil
import fileutil

class Droidblaze:
    java = "java"
    droidblaze_jar = "droidblaze-core-1.0-SNAPSHOT-jar-with-dependencies.jar"
    sdk_dir = "android-sdk"
    jvm_option = "-Xmx2048M"
    debug_option = "-Ddroidblaze.debug.consolemsg=1"
    output_dir = "droidblaze_output"
    summary_html = path.join(output_dir,"summary.html")
    summary_xsl = path.join(output_dir,"summary.xsl")
    summary_xml = path.join(output_dir,"summary.xml")
    merged_xml = path.join(output_dir,"merged.xml")

    def __init__(self,analysis_id,target,analyses):
        self.analysis_id = analysis_id
        self.target_apk = target
        self.run_analyses = analyses
    def tar_result(self,work_dir,outfile):
        fileutil.tar(work_dir,outfile,self.output_dir)
    def merging_summary(self,work_dir):
        merged = path.join(work_dir,self.merged_xml)
        old_merged = merged+".old"
        summary = path.join(work_dir,self.summary_xml)
        if not path.exists(merged):
            shutil.copyfile(summary,merged)
        else:
            shutil.move(merged,old_merged)
            summary_file = open(summary,"r")
            old_merged_file = open(old_merged,"r")
            summary_contents = summary_file.readlines()
            old_merged_contents = old_merged_file.readlines()
            summary_file.close()
            old_merged_file.close()
            merged_file = open(merged,"w")
            merged_contents = old_merged_contents[:-1]+summary_contents[1:-1]+old_merged_contents[-1:]
            for line in merged_contents:
                merged_file.write(line)
            merged_file.close()
        fileutil.saxon(work_dir,self.summary_html,self.merged_xml,self.summary_xsl)
    def run(self,work_dir):
        output = path.join(work_dir,self.output_dir)
        if path.exists(output):
            shutil.rmtree(output)
        cmd = []
        cmd.append(self.java)
        cmd.append(self.jvm_option)
        cmd.append(self.debug_option)
        cmd.append("-Ddroidblaze.sdkdir={}".format(self.sdk_dir))
        cmd.append("-Ddroidblaze.target.apk={}".format(self.target_apk))
        cmd.append("-Ddroidblaze.run.analyses={}".format(self.run_analyses))
        cmd.append("-jar")
        cmd.append(self.droidblaze_jar)
        Popen(cmd,cwd=work_dir).wait()

if __name__ == "__main__":
    dr = Droidblaze(sys.argv[1],sys.argv[2])
    dr.run(sys.argv[3])
