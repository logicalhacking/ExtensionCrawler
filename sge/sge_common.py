import sys
import os
import socket
import re
import tempfile
import subprocess
from datetime import datetime


def get_project_root():
    return os.path.normpath(os.path.join(sys.path[0], os.path.pardir))


def validate_archivepath(basedir):
    datadir = os.path.join(basedir, "data")
    if not os.path.exists(datadir):
        print("ERROR: '{}' does not exist!".format(datadir), file=sys.stderr)
        sys.exit(1)

    dirs = os.listdir(datadir)

    if dirs is []:
        print(
            "ERROR: '{}' is empty, refusing to start".format(datadir),
            file=sys.stderr)
        sys.exit(1)

    for dir in dirs:
        if len(dir) is not 3:
            print(
                "ERROR: '{}' must only contain three-letter-dirs, found '{}'!".
                format(datadir, dir),
                file=sys.stderr)
            sys.exit(1)


def validate_execpath(execpath):
    if not os.path.exists(execpath):
        print("ERROR: {} does not exist!".format(execpath), file=sys.stderr)
        sys.exit(1)


def ensure_sharc():
    if not re.match("sharc-.*.shef.ac.uk", socket.gethostname()):
        print("ERROR: only running on sharc!", file=sys.stderr)
        sys.exit(1)


def validate_outdir(outdir):
    if os.path.exists(outdir):
        print("ERROR: '{}' already exists!".format(outdir), file=sys.stderr)
        sys.exit(1)


def execute_sge(sgecontent):
    with tempfile.NamedTemporaryFile() as f:
        f.write(sgecontent.encode())
        f.flush()
        try:
            output = subprocess.check_output(
                ["qsub", f.name], stderr=subprocess.STDOUT)
            print(output.decode())
        except subprocess.CalledProcessError as e:
            print("ERROR when submitting job:", file=sys.stderr)
            print(e.output.decode())
            sys.exit(1)


def get_stdout_path(name):
    return os.path.expanduser(
        os.path.join("~", "sgelog", name + "_" +
                     datetime.now().strftime("%Y-%m-%d_%H-%M-%S")))
