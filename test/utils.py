import os, subprocess


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
    

def is_in_rootdir():
    """ Check whether the current dir is the root dir of pyelftools
    """
    dirstuff = os.listdir('.')
    return 'test' in dirstuff and 'elftools' in dirstuff
    
