#-------------------------------------------------------------------------------
# test/utils.py
#
# Some common utils for tests
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
from __future__ import print_function
import os, sys, subprocess, tempfile


def run_exe(exe_path, args=[], echo=False):
    """ Runs the given executable as a subprocess, given the
        list of arguments. Captures its return code (rc) and stdout and
        returns a pair: rc, stdout_str
    """
    popen_cmd = [exe_path] + args
    if os.path.splitext(exe_path)[1] == '.py':
        popen_cmd.insert(0, sys.executable)
    if echo:
      print('[cmd]', ' '.join(popen_cmd))
    proc = subprocess.Popen(popen_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    proc_stdout = proc.communicate()[0]
    return proc.returncode, proc_stdout.decode('latin-1')


def is_in_rootdir():
    """ Check whether the current dir is the root dir of pyelftools
    """
    return os.path.isdir('test') and os.path.isdir('elftools')


def dump_output_to_temp_files(testlog, filename, option, *args):
    """ Dumps the output strings given in 'args' to temp files: one for each
        arg. The filename and option arguments contribute to the file name,
        so that one knows which test did the output dump come from.
    """
    for i, s in enumerate(args):
        fd, path = tempfile.mkstemp(
                prefix='out-%d-%s-%s-' % (i + 1, os.path.split(filename)[-1], option),
                suffix='.stdout')
        file = os.fdopen(fd, 'w')
        file.write(s)
        file.close()
        testlog.info('@@ Output #%s dumped to file: %s' % (i + 1, path))
