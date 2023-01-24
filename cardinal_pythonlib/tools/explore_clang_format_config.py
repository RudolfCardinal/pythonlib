#!/usr/bin/env python3
# cardinal_pythonlib/tools/explore_clang_format_config.py

"""
===============================================================================

    Original code copyright (C) 2009-2022 Rudolf Cardinal (rudolf@pobox.com).

    This file is part of cardinal_pythonlib.

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        https://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.

===============================================================================

**Test clang-format options.**

"""

# =============================================================================
# Imports
# =============================================================================

import argparse
import os.path
import shutil
import logging
import subprocess
import tempfile
import time
from typing import List

from cardinal_pythonlib.fileops import concatenate, FileWatcher

log = logging.getLogger(__name__)


# =============================================================================
# Helper functions/classes
# =============================================================================


def monitor_diff(filenames: List[str], meld_exe: str) -> subprocess.Popen:
    """
    Fire up Meld in the background for a 3-way comparison.
    Meld automatically offers to reload if a file is changed.
    """
    assert 2 <= len(filenames) <= 3
    log.info(f"Launching Meld for {filenames}")
    return subprocess.Popen([meld_exe] + filenames)


def clang_format(
    config: str, src: str, dest: str, dir: str, clang_format_exe: str
) -> None:
    """
    Rungs clang-format, formatting a source file to a destination file using a
    YAML config.
    """
    # Curiously, clang-format will only allow config files to be called
    # ".clang-format" in the current directory. Its syntax help makes you think
    # you can specify "-style=PATH_TO_CONFIG", but no; you have to use
    # "-style=file" literally, and have the config file correctly named in the
    # current directory.
    # https://stackoverflow.com/questions/46373858/how-do-i-specify-a-clang-format-file  # noqa
    fixed_config_filename = ".clang-format"
    fixed_config_path = os.path.join(dir, fixed_config_filename)

    shutil.copy(src, dest)
    shutil.copy(config, fixed_config_path)
    os.chdir(dir)
    subprocess.check_call(
        [
            clang_format_exe,
            "-style=file",  # read ./.clang-format; see above
            "-i",  # edit in place
            dest,
        ]
    )


# =============================================================================
# Main code
# =============================================================================


def explore_clang_format(
    config_filename: str,
    source_filenames: List[str],
    clang_format_exe: str,
    meld_exe: str,
    sleep_time_s: int = 1,
) -> None:
    """
    Launch Meld to compare before-and-after C++ code.
    Watch for changes in the config file and rebuild the processed C++ if so.
    """
    config_filename = os.path.abspath(config_filename)
    source_filenames = [os.path.abspath(f) for f in source_filenames]
    assert len(source_filenames) >= 1
    with tempfile.TemporaryDirectory() as tempdir:
        os.chdir(tempdir)  # necessary for the fixed config file name!
        # Filenames
        working_src = os.path.join(
            tempdir, ".".join(os.path.basename(f) for f in source_filenames)
        )
        previous_config = os.path.join(tempdir, "previous_config.yaml")
        current_cpp = os.path.join(tempdir, "with_current_config.cpp")
        last_cpp = os.path.join(tempdir, "with_previous_config.cpp")

        # Create working source
        concatenate(source_filenames, working_src, filesep=os.linesep * 2)

        # First "previous" config is the same as the current config
        shutil.copy(config_filename, previous_config)

        # Start up
        clang_format(
            config=config_filename,
            src=working_src,
            dest=current_cpp,
            dir=tempdir,
            clang_format_exe=clang_format_exe,
        )
        clang_format(
            config=previous_config,
            src=working_src,
            dest=last_cpp,
            dir=tempdir,
            clang_format_exe=clang_format_exe,
        )

        # Watch for change
        log.info(f"Config = {config_filename}")
        log.info(f"Source = {source_filenames}")
        _ = monitor_diff([working_src, current_cpp, last_cpp], meld_exe)
        watcher = FileWatcher([config_filename] + source_filenames)
        log.info("Watching config/source files; press Ctrl-C to abort")
        while True:
            time.sleep(sleep_time_s)
            changed_filenames = watcher.changed()
            if changed_filenames:
                concatenate(source_filenames, working_src)
                clang_format(
                    config=config_filename,
                    src=working_src,
                    dest=current_cpp,
                    dir=tempdir,
                    clang_format_exe=clang_format_exe,
                )
                clang_format(
                    config=previous_config,
                    src=working_src,
                    dest=last_cpp,
                    dir=tempdir,
                    clang_format_exe=clang_format_exe,
                )
                if config_filename in changed_filenames:
                    shutil.copy(config_filename, previous_config)


# =============================================================================
# Command-line entry point
# =============================================================================


def main() -> None:
    """
    Command-line entry point.
    """
    parser = argparse.ArgumentParser(
        description="Follow changes in a clang-format config file. "
        "Apply them to a specimen C++ file (re-applying them when the config "
        "file changes) and watch the effects via Meld. For help on options, "
        "see https://clang.llvm.org/docs/ClangFormatStyleOptions.html",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "config",
        help=(
            "YAML clang-format config file. Create one with e.g.: "
            "clang-format --style=WebKit --dump-config > myconfig.yaml"
        ),
    )
    parser.add_argument(
        "source",
        nargs="+",
        help=(
            "C++ source (.cpp, .h) file(s) to play with (if you specify "
            "several, they will be concatenated)"
        ),
    )
    parser.add_argument(
        "--clangformat",
        help=(
            "clang-format executable (see https://apt.llvm.org/ and "
            "consider: 'sudo apt install clang-format-14')"
        ),
        default=shutil.which("clang-format"),
    )
    parser.add_argument(
        "--meld",
        help="meld executable (consider: 'sudo apt install meld')",
        default=shutil.which("meld"),
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.DEBUG)
    log.debug(f"clang-format executable: {args.clangformat}")
    assert args.clangformat, "clang-format executable not specified or found"
    log.debug(f"meld executable: {args.meld}")
    assert args.meld, "meld executable not specified or found"
    explore_clang_format(
        config_filename=args.config,
        source_filenames=args.source,
        clang_format_exe=args.clangformat,
        meld_exe=args.meld,
    )


if __name__ == "__main__":
    main()
