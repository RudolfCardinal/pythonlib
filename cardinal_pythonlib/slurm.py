#!/usr/bin/env python
# cardinal_pythonlib/slurm.py

"""
===============================================================================

    Original code copyright (C) 2009-2018 Rudolf Cardinal (rudolf@pobox.com).

    This file is part of cardinal_pythonlib.

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.

===============================================================================

**Library functions to launch jobs under the Slurm workload manager.**

See https://slurm.schedmd.com/.

RNC: SLURM job launcher.

- You can't use environment variables in ``#SBATCH`` syntax.
- ``sbatch`` stops looking at the first non-comment line that is not an
  ``#SBATCH`` line (and the rest goes to the job's shell).
- We want to be able to use variable substitution in places, and no
  substitution in others (for later substitution).
- The HPHI has Python 3.4.2 (as of 2018-02-17) so no Python 3.5 stuff without
  installing a newer Python and ``venv`` (but let's do that).

To find out what you have available in terms of partitions, clusters, etc.:

.. code-block:: bash

    $ sinfo                            # summarizes partitions, nodes
                                       # NB: default partition has "*" appended
    $ scontrol show node <NODENAME>    # details of one node
    $ sacctmgr show qos                # show Quality of Service options
    $ squeue -u <USERNAME> --sort=+i   # show my running jobs

"""

from datetime import timedelta
import logging
import os
from subprocess import PIPE, Popen
from typing import List

from cardinal_pythonlib.datetimefunc import strfdelta
from cardinal_pythonlib.fileops import pushd

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


SLURM_TIMEDELTA_FMT = "{D}-{H:02}:{M:02}:{S:02}"


def launch_slurm(jobname: str,
                 cmd: str,
                 memory_mb: int,
                 project: str,
                 qos: str,
                 email: str,
                 duration: timedelta,
                 tasks_per_node: int,
                 cpus_per_task: int,
                 partition: str = "",
                 modules: List[str] = None,
                 directory: str = os.getcwd(),
                 encoding: str = "ascii") -> None:
    """
    Launch a job into the SLURM environment.

    Args:
        jobname: name of the job
        cmd: command to be executed
        memory_mb: maximum memory requirement per process (Mb)
        project: project name
        qos: quality-of-service name
        email: user's e-mail address
        duration: maximum duration per job
        tasks_per_node: tasks per (cluster) node
        cpus_per_task: CPUs per task
        partition: cluster partition name
        modules: SLURM modules to load
        directory: directory to change to
        encoding: encoding to apply to launch script as sent to ``sbatch``
    """
    if partition:
        partition_cmd = "#SBATCH -p {}".format(partition)
    else:
        partition_cmd = ""
    if modules is None:
        modules = ["default-wbic"]

    log.info("Launching SLURM job: {}".format(jobname))
    script = """#!/bin/bash

#! Name of the job:
#SBATCH -J {jobname}

#! Which project should jobs run under:
#SBATCH -A {project}

#! What QoS [Quality of Service] should the job run in?
#SBATCH --qos={qos}

#! How much resource should be allocated?
#SBATCH --tasks-per-node={tasks_per_node}
#SBATCH --cpus-per-task={cpus_per_task}

#! Memory requirements
#SBATCH --mem={memory_mb}

#! How much wall-clock time will be required?
#SBATCH --time={duration}

#! What e-mail address to use for notifications?
#SBATCH --mail-user={email}

#! What types of email messages do you wish to receive?
#SBATCH --mail-type=ALL

#! Uncomment this to prevent the job from being requeued (e.g. if
#! interrupted by node failure or system downtime):
#! SBATCH --no-requeue

#! Partition
{partition_cmd}

#! sbatch directives end here (put any additional directives above this line)

#! ############################################################
#! Modify the settings below to specify the application's environment, location
#! and launch method:

#! Optionally modify the environment seen by the application
#! (note that SLURM reproduces the environment at submission irrespective of ~/.bashrc):
. /etc/profile.d/modules.sh                # Leave this line (enables the module command)
module purge                               # Removes all modules still loaded
module load {modules}                      # Basic one, e.g. default-wbic, is REQUIRED - loads the basic environment

#! Insert additional module load commands after this line if needed:

#! Full path to your application executable:
application="hostname"

#! Run options for the application:
options=""

#! Work directory (i.e. where the job will run):
workdir="$SLURM_SUBMIT_DIR"  # The value of SLURM_SUBMIT_DIR sets workdir to the directory
                             # in which sbatch is run.

#! Are you using OpenMP (NB this is **unrelated to OpenMPI**)? If so increase this
#! safe value to no more than 24:
export OMP_NUM_THREADS=24

# Command line to be submited by SLURM:
CMD="{cmd}"

###############################################################
### You should not have to change anything below this line ####
###############################################################

cd $workdir
echo -e "Changed directory to `pwd`.\n"

JOBID=$SLURM_JOB_ID

echo -e "JobID: $JOBID\n======"
echo "Time: `date`"
echo "Running on master node: `hostname`"
echo "Current directory: `pwd`"

if [ "$SLURM_JOB_NODELIST" ]; then
    #! Create a machine file:
    export NODEFILE=`/usr/bin/generate_pbs_nodefile`
    cat $NODEFILE | uniq > machine.file.$JOBID
    echo -e "\nNodes allocated:\n================"
    echo `cat machine.file.$JOBID | sed -e 's/\..*$//g'`
fi

echo -e "\nExecuting command:\n==================\n$CMD\n"

eval $CMD
    """.format(  # noqa
        cmd=cmd,
        cpus_per_task=cpus_per_task,
        duration=strfdelta(duration, SLURM_TIMEDELTA_FMT),
        email=email,
        jobname=jobname,
        memory_mb=memory_mb,
        modules=" ".join(modules),
        partition_cmd=partition_cmd,
        project=project,
        qos=qos,
        tasks_per_node=tasks_per_node,
    )
    cmdargs = ["sbatch"]
    with pushd(directory):
        p = Popen(cmdargs, stdin=PIPE)
        p.communicate(input=script.encode(encoding))


def launch_cambridge_hphi(
        jobname: str,
        cmd: str,
        memory_mb: int,
        qos: str,
        email: str,
        duration: timedelta,
        cpus_per_task: int,
        project: str = "hphi",
        tasks_per_node: int = 1,
        partition: str = "wbic-cs",  # 2018-02: was "wbic", now "wbic-cs"
        modules: List[str] = None,
        directory: str = os.getcwd(),
        encoding: str = "ascii") -> None:
    """
    Specialization of :func:`launch_slurm` (q.v.) with defaults for the
    University of Cambridge WBIC HPHI.
    """
    if modules is None:
        modules = ["default-wbic"]
    launch_slurm(
        cmd=cmd,
        cpus_per_task=cpus_per_task,
        directory=directory,
        duration=duration,
        email=email,
        encoding=encoding,
        jobname=jobname,
        memory_mb=memory_mb,
        modules=modules,
        partition=partition,
        project=project,
        qos=qos,
        tasks_per_node=tasks_per_node,
    )
