#!/usr/bin/env python
# cardinal_pythonlib/platformfunc.py

"""
===============================================================================

    Original code copyright (C) 2009-2019 Rudolf Cardinal (rudolf@pobox.com).

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
import os
import platform
import subprocess
import sys
from typing import Callable, Dict, List, TextIO, Tuple

from cardinal_pythonlib.fileops import (
    mkdir_p,
    pushd,
    require_executable,
    which_and_require,
)
from cardinal_pythonlib.logs import get_brace_style_log_with_null_handler
from cardinal_pythonlib.network import download
from cardinal_pythonlib.tee import teed_call

log = get_brace_style_log_with_null_handler(__name__)


# =============================================================================
# Types
# =============================================================================

RunFuncType = Callable
# ... we were using Callable[[List[str]], Any] but that caused type-checking
#     errors with functions that also took keyword arguments
# ... i.e. something that looks like:
#     def somefunc(strlist, **kwargs) -> ...
# ... you can't represent that exactly with Callable;
#     https://docs.python.org/3/library/typing.html#typing.Callable
# ... so the best is Callable, which is Callable[..., Any]


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
        log.info("No need to download, already have: {}", filename)
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
              run_func: RunFuncType = None,
              git_executable: str = None) -> bool:
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
        git_executable: name of git executable (default ``git``)

    Returns:
        did we need to do anything?
    """
    git = which_and_require(git_executable or "git")
    run_func = run_func or subprocess.check_call
    clone_options = clone_options or []  # type: List[str]
    if os.path.isdir(directory):
        log.info(
            "Not re-cloning {} Git repository: using existing source in {}",
            prettyname, directory)
        return False
    log.info("Fetching {} source from {} into {}",
             prettyname, url, directory)
    gitargs = [git, "clone"] + clone_options
    if branch:
        gitargs += ["--branch", branch]
    gitargs += [url, directory]
    run_func(gitargs)
    if commit:
        log.info("Resetting {} local Git repository to commit {}",
                 prettyname, commit)
        run_func([git,
                  "-C", directory,
                  "reset", "--hard", commit])
        # Using a Git repository that's not in the working directory:
        # https://stackoverflow.com/questions/1386291/git-git-dir-not-working-as-expected  # noqa
    return True


# def fix_git_repo_for_windows(directory: str):
#     # https://github.com/openssl/openssl/issues/174
#     log.info("Fixing repository {!r} for Windows line endings", directory)
#     with pushd(directory):
#         run([GIT, "config", "--local", "core.autocrlf", "false"])
#         run([GIT, "config", "--local", "core.eol", "lf"])
#         run([GIT, "rm", "--cached", "-r", "."])
#         run([GIT, "reset", "--hard"])


# =============================================================================
# tar functions
# =============================================================================

def tar_supports_force_local_switch(tar_executable: str) -> bool:
    """
    Does ``tar`` support the ``--force-local`` switch? We ask it.
    """
    tarhelp = fetch([tar_executable, "--help"])
    return "--force-local" in tarhelp


def untar_to_directory(tarfile: str,
                       directory: str,
                       verbose: bool = False,
                       gzipped: bool = False,
                       skip_if_dir_exists: bool = True,
                       run_func: RunFuncType = None,
                       chdir_via_python: bool = True,
                       tar_executable: str = None,
                       tar_supports_force_local: bool = None) -> None:
    """
    Unpacks a TAR file into a specified directory.

    Args:
        tarfile:
            filename of the ``.tar`` file
        directory:
            destination directory
        verbose:
            be verbose?
        gzipped:
            is the ``.tar`` also gzipped, e.g. a ``.tar.gz`` file?
        skip_if_dir_exists:
            don't do anything if the destrination directory exists?
        run_func:
            function to use to call an external command
        chdir_via_python:
            change directory via Python, not via ``tar``. Consider using this
            via Windows, because Cygwin ``tar`` v1.29 falls over when given a
            Windows path for its ``-C`` (or ``--directory``) option.
        tar_executable:
            name of the ``tar`` executable (default is ``tar``)
        tar_supports_force_local:
            does tar support the ``--force-local`` switch? If you pass ``None``
            (the default), this is checked directly via ``tar --help``.
            Linux/GNU tar does; MacOS tar doesn't; Cygwin tar does; Windows 10
            (build 17063+) tar doesn't.
    """
    if skip_if_dir_exists and os.path.isdir(directory):
        log.info("Skipping extraction of {} as directory {} exists",
                 tarfile, directory)
        return
    tar = which_and_require(tar_executable or "tar")
    if tar_supports_force_local is None:
        tar_supports_force_local = tar_supports_force_local_switch(tar)
    log.info("Extracting {} -> {}", tarfile, directory)
    mkdir_p(directory)
    args = [tar, "-x"]  # -x: extract
    if verbose:
        args.append("-v")  # -v: verbose
    if gzipped:
        args.append("-z")  # -z: decompress using gzip
    if tar_supports_force_local:
        args.append("--force-local")  # allows filenames with colons in
    args.extend(["-f", tarfile])  # -f: filename follows
    if chdir_via_python:
        with pushd(directory):
            run_func(args)
    else:
        # chdir via tar
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
    # log.debug("External command Python form: {}", args)
    copy_paste_cmd = subprocess.list2cmdline(args)
    csep = "=" * 79
    esep = "-" * 79
    effective_env = env if env is not None else os.environ
    if debug_show_env:
        log.debug(
            "Environment for the command that follows:\n"
            "{esep}\n"
            "{env}\n"
            "{esep}",
            esep=esep,
            env=make_copy_paste_env(effective_env)
        )
    log.info(
        "Launching external command:\n"
        "{csep}\n"
        "WORKING DIRECTORY: {cwd}\n"
        "PYTHON ARGS: {pyargs!r}\n"
        "COMMAND: {cmd}\n"
        "{csep}",
        csep=csep,
        cwd=cwd,
        cmd=copy_paste_cmd,
        pyargs=args
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
        log.debug("\n{csep}\nFINISHED SUCCESSFULLY: {cmd}\n{csep}",
                  cmd=copy_paste_cmd, csep=csep)
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
            "[PYTHON ARGS] {pyargs}\n"
            "[COMMAND] {cmd}",
            cwd=cwd,
            env=make_copy_paste_env(effective_env),
            cmd=copy_paste_cmd,
            pyargs=args
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
    log.debug("{}", stdout)
    return stdout
