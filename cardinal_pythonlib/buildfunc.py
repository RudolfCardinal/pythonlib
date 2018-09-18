#!/usr/bin/env python
# cardinal_pythonlib/platformfunc.py

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

**Support for building software.**

"""

import io
import logging
import os
import platform
import subprocess
import sys
from typing import Any, Callable, Dict, List, TextIO, Tuple

from cardinal_pythonlib.fileops import mkdir_p, require_executable
from cardinal_pythonlib.network import download
from cardinal_pythonlib.tee import teed_call

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


# =============================================================================
# Constants
# =============================================================================

GIT = "git"
TAR = "tar"


# =============================================================================
# Download things
# =============================================================================

def download_if_not_exists(url: str, filename: str,
                           skip_cert_verify: bool = True,
                           mkdir: bool = True) -> None:
    """
    Downloads a URL to a file, unless the file already exists.
    """
    if os.path.isfile(filename):
        log.info("No need to download, already have: {}".format(filename))
        return
    if mkdir:
        directory, basename = os.path.split(os.path.abspath(filename))
        mkdir_p(directory)
    download(url=url,
             filename=filename,
             skip_cert_verify=skip_cert_verify)


# =============================================================================
# Git functions
# =============================================================================

def git_clone(prettyname: str, url: str, directory: str,
              branch: str = None,
              commit: str = None,
              clone_options: List[str] = None,
              run_func: Callable[[List[str]], Any] = None) -> bool:
    """
    Fetches a Git repository, unless we have it already.

    Args:
        prettyname: name to display to user
        url: URL
        directory: destination directory
        branch: repository branch
        commit: repository commit tag
        clone_options: additional options to pass to ``git clone``
        run_func: function to use to call an external command

    Returns:
        did we need to do anything?
    """
    run_func = run_func or subprocess.check_call
    clone_options = clone_options or []  # type: List[str]
    if os.path.isdir(directory):
        log.info("Not re-cloning {} Git repository: using existing source "
                 "in {}".format(prettyname, directory))
        return False
    log.info("Fetching {} source from {} into {}".format(
        prettyname, url, directory))
    require_executable(GIT)
    gitargs = [GIT, "clone"] + clone_options
    if branch:
        gitargs += ["--branch", branch]
    gitargs += [url, directory]
    run_func(gitargs)
    if commit:
        log.info("Resetting {} local Git repository to commit {}".format(
            prettyname, commit))
        run_func([GIT,
                  "-C", directory,
                  "reset", "--hard", commit])
        # Using a Git repository that's not in the working directory:
        # https://stackoverflow.com/questions/1386291/git-git-dir-not-working-as-expected  # noqa
    return True


# def fix_git_repo_for_windows(directory: str):
#     # https://github.com/openssl/openssl/issues/174
#     log.info("Fixing repository {!r} for Windows line endings".format(
#         directory))
#     with pushd(directory):
#         run([GIT, "config", "--local", "core.autocrlf", "false"])
#         run([GIT, "config", "--local", "core.eol", "lf"])
#         run([GIT, "rm", "--cached", "-r", "."])
#         run([GIT, "reset", "--hard"])


# =============================================================================
# tar functions
# =============================================================================

def untar_to_directory(tarfile: str, directory: str,
                       verbose: bool = False,
                       gzipped: bool = False,
                       skip_if_dir_exists: bool = True,
                       run_func: Callable[[List[str]], Any] = None) -> None:
    """
    Unpacks a TAR file into a specified directory.

    Args:
        tarfile: filename of the ``.tar`` file
        directory: destination directory
        verbose: be verbose?
        gzipped: is the ``.tar`` also gzipped, e.g. a ``.tar.gz`` file?
        skip_if_dir_exists: don't do anything if the destrination directory
            exists?
        run_func: function to use to call an external command
    """
    if skip_if_dir_exists and os.path.isdir(directory):
        log.info("Skipping extraction of {} as directory {} exists".format(
            tarfile, directory))
        return
    log.info("Extracting {} -> {}".format(tarfile, directory))
    require_executable(TAR)
    mkdir_p(directory)
    args = [TAR, "-x"]  # -x: extract
    if verbose:
        args.append("-v")  # -v: verbose
    if gzipped:
        args.append("-z")  # -z: decompress using gzip
    if platform.system() != "Darwin":  # OS/X tar doesn't support --force-local
        args.append("--force-local")  # allows filenames with colons in (Windows!)  # noqa
    args.extend(["-f", tarfile])  # -f: filename follows
    args.extend(["-C", directory])  # -C: change to directory
    run_func(args)


# =============================================================================
# Environment functions
# =============================================================================

def make_copy_paste_env(env: Dict[str, str]) -> str:
    """
    Convert an environment into a set of commands that can be copied/pasted, on
    the build platform, to recreate that environment.
    """
    windows = platform.system() == "Windows"
    cmd = "set" if windows else "export"
    return (
        "\n".join(
            "{cmd} {k}={v}".format(
                cmd=cmd,
                k=k,
                v=env[k] if windows else subprocess.list2cmdline([env[k]])
            ) for k in sorted(env.keys())
        )
    )
    # Note that even subprocess.list2cmdline() will put needless quotes in
    # here, whereas SET is happy with e.g. SET x=C:\Program Files\somewhere;
    # subprocess.list2cmdline() will also mess up trailing backslashes (e.g.
    # for the VS140COMNTOOLS environment variable).


# =============================================================================
# Run subprocesses in a very verbose way
# =============================================================================

def run(args: List[str],
        env: Dict[str, str] = None,
        capture_stdout: bool = False,
        echo_stdout: bool = True,
        capture_stderr: bool = False,
        echo_stderr: bool = True,
        debug_show_env: bool = True,
        encoding: str = sys.getdefaultencoding(),
        allow_failure: bool = False,
        **kwargs) -> Tuple[str, str]:
    """
    Runs an external process, announcing it.

    Optionally, retrieves its ``stdout`` and/or ``stderr`` output (if not
    retrieved, the output will be visible to the user).

    Args:
        args: list of command-line arguments (the first being the executable)

        env: operating system environment to use (if ``None``, the current OS
            environment will be used)

        capture_stdout: capture the command's ``stdout``?

        echo_stdout: allow the command's ``stdout`` to go to ``sys.stdout``?

        capture_stderr: capture the command's ``stderr``?

        echo_stderr: allow the command's ``stderr`` to go to ``sys.stderr``?

        debug_show_env: be verbose and show the environment used before calling

        encoding: encoding to use to translate the command's output

        allow_failure: if ``True``, continues if the command returns a
            non-zero (failure) exit code; if ``False``, raises an error if
            that happens

        kwargs: additional arguments to :func:`teed_call`

    Returns:
        a tuple: ``(stdout, stderr)``. If the output wasn't captured, an empty
        string will take its place in this tuple.
    """
    cwd = os.getcwd()
    # log.debug("External command Python form: {}".format(args))
    copy_paste_cmd = subprocess.list2cmdline(args)
    csep = "=" * 79
    esep = "-" * 79
    effective_env = env or os.environ
    if debug_show_env:
        log.debug(
            "Environment for the command that follows:\n"
            "{esep}\n"
            "{env}\n"
            "{esep}".format(esep=esep, env=make_copy_paste_env(effective_env))
        )
    log.info(
        "Launching external command:\n"
        "{csep}\n"
        "WORKING DIRECTORY: {cwd}\n"
        "PYTHON ARGS: {args!r}\n"
        "COMMAND: {cmd}\n"
        "{csep}".format(csep=csep, cwd=cwd, cmd=copy_paste_cmd,
                        args=args)
    )
    try:
        with io.StringIO() as out, io.StringIO() as err:
            stdout_targets = []  # type: List[TextIO]
            stderr_targets = []  # type: List[TextIO]
            if capture_stdout:
                stdout_targets.append(out)
            if echo_stdout:
                stdout_targets.append(sys.stdout)
            if capture_stderr:
                stderr_targets.append(err)
            if echo_stderr:
                stderr_targets.append(sys.stderr)
            retcode = teed_call(args,
                                stdout_targets=stdout_targets,
                                stderr_targets=stderr_targets,
                                encoding=encoding,
                                env=env,
                                **kwargs)
            stdout = out.getvalue()
            stderr = err.getvalue()
            if retcode != 0 and not allow_failure:
                # subprocess.check_call() and check_output() raise
                # CalledProcessError if the called process returns a non-zero
                # return code.
                raise subprocess.CalledProcessError(returncode=retcode,
                                                    cmd=args,
                                                    output=stdout,
                                                    stderr=stderr)
        log.debug("\n{csep}\nFINISHED SUCCESSFULLY: {cmd}\n{csep}".format(
            cmd=copy_paste_cmd, csep=csep))
        return stdout, stderr
    except FileNotFoundError:
        require_executable(args[0])  # which is missing, so we'll see some help
        raise
    except subprocess.CalledProcessError:
        log.critical(
            "Command that failed:\n"
            "[ENVIRONMENT]\n"
            "{env}\n"
            "\n"
            "[DIRECTORY] {cwd}\n"
            "[PYTHON ARGS] {args}\n"
            "[COMMAND] {cmd}".format(
                cwd=cwd,
                env=make_copy_paste_env(effective_env),
                cmd=copy_paste_cmd,
                args=args
            )
        )
        raise


def fetch(args: List[str], env: Dict[str, str] = None,
          encoding: str = sys.getdefaultencoding()) -> str:
    """
    Run a command and returns its stdout.

    Args:
        args: the command-line arguments
        env: the operating system environment to use
        encoding: the encoding to use for ``stdout``

    Returns:
        the command's ``stdout`` output

    """
    stdout, _ = run(args, env=env, capture_stdout=True,
                    echo_stdout=False, encoding=encoding)
    log.debug(stdout)
    return stdout
