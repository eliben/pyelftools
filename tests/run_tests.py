#!/usr/bin/env python
#-------------------------------------------------------------------------------
# tests/run_tests.py
#
# Automatic test runner for elftools & readelf
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
import os, sys
from difflib import SequenceMatcher
import logging
import subprocess
import tempfile


# Create a global logger object
#
testlog = logging.getLogger('run_tests')
testlog.setLevel(logging.DEBUG)
testlog.addHandler(logging.StreamHandler(sys.stdout))


def discover_testfiles(rootdir):
    """ Discover test files in the given directory. Yield them one by one.
    """
    for filename in os.listdir(rootdir):
        _, ext = os.path.splitext(filename)
        if ext == '.elf':
            yield os.path.join(rootdir, filename)


def run_exe(exe_path, args):
    """ Runs the given executable as a subprocess, given the
        list of arguments. Captures its return code (rc) and stdout and
        returns a pair: rc, stdout_str
    """
    popen_cmd = [exe_path] + args
    if os.path.splitext(exe_path)[1] == '.py':
        popen_cmd.insert(0, 'python')
    proc = subprocess.Popen(popen_cmd, stdout=subprocess.PIPE)
    proc_stdout = proc.communicate()[0]
    return proc.returncode, proc_stdout
    

def run_test_on_file(filename):
    """ Runs a test on the given input filename
    """
    testlog.info("Running test on file '%s'" % filename)
    for option in ['-e', '-s', '-x.text']:
        testlog.info("..option='%s'" % option)
        # stdouts will be a 2-element list: output of readelf and output 
        # of scripts/readelf.py
        stdouts = []
        for exe_path in ['readelf', 'scripts/readelf.py']:
            args = [option, filename]
            testlog.info("....executing: '%s %s'" % (
                exe_path, ' '.join(args)))
            rc, stdout = run_exe(exe_path, args)
            if rc != 0:
                testlog.error("@@ aborting - '%s' returned '%s'" % (exe_path, rc))
                break
            stdouts.append(stdout)
        testlog.info('....comparing output...')
        success, errmsg = compare_output(*stdouts)
        if success:
            testlog.info('.......................SUCCESS')
        else:
            testlog.info('.......................FAIL')
            testlog.info('@@ ' + errmsg)
            dump_output_to_temp_files(*stdouts)


def compare_output(s1, s2):
    """ Compare stdout strings s1 and s2.
        Return pair success, errmsg. If comparison succeeds, success is True
        and errmsg is empty. Otherwise success is False and errmsg holds a
        description of the mismatch.

        Note: this function contains some rather horrible hacks to ignore
        differences which are not important for the verification of pyelftools.
        This is due to some intricacies of binutils's readelf which pyelftools
        doesn't currently implement. Read the documentation for more details.
    """
    lines1 = s1.splitlines()
    lines2 = s2.splitlines()
    if len(lines1) != len(lines2):
        return False, 'Number of lines different: %s vs %s' % (
                len(lines1), len(lines2))

    flag_after_symtable = False

    for i in range(len(lines1)):
        if 'Symbol table' in lines1[i]:
            flag_after_symtable = True
        # Compare ignoring whitespace
        if lines1[i].split() != lines2[i].split():
            if flag_after_symtable:
                sm = SequenceMatcher()
                sm.set_seqs(lines1[i], lines2[i])
                # Detect readelf's adding @ with lib and version after 
                # symbol name.
                changes = sm.get_opcodes()
                if (    len(changes) == 2 and changes[1][0] == 'delete' and
                        lines1[i][changes[1][1]] == '@'):
                    continue

            errmsg = 'Mismatch on line #%s:\n>>%s<<\n>>%s<<\n' % (
                    i, lines1[i], lines2[i])
            return False, errmsg
    return True, ''
    

def dump_output_to_temp_files(*args):
    """ Dumps the output strings given in 'args' to temp files: one for each
        arg.
    """
    for i, s in enumerate(args):
        fd, path = tempfile.mkstemp(
                prefix='out' + str(i + 1) + '_',
                suffix='.stdout')
        file = os.fdopen(fd, 'w')
        file.write(s)
        file.close()
        testlog.info('@@ Output #%s dumped to file: %s' % (i + 1, path))
    

def die(msg):
    testlog.error('Error: %s' % msg)
    sys.exit(1)


def is_in_rootdir():
    """ Check whether the current dir is the root dir of pyelftools
    """
    dirstuff = os.listdir('.')
    return 'tests' in dirstuff and 'elftools' in dirstuff
    

def main():
    if not is_in_rootdir():
        die('Please run me from the root dir of pyelftools!')

    for filename in discover_testfiles('tests/testfiles'):
        run_test_on_file(filename)


if __name__ == '__main__':
    main()
    #testlog.info(list(discover_testfiles('tests/testfiles'))) 
    #print run_exe('scripts/readelf.py', ['-h', 'tests/testfiles/z32.o.elf'])




