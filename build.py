#!/usr/bin/env python
"""Setup the Python environment to run the web and app scripts."""

from typing import List
import pathlib
import os
import sys
import subprocess
import warnings

PYTHON_BINARY: str = "python3"


def main(args: List[str]) -> None:
    if len(args) > 1:
        warnings.warn(
            f"The setup script doesn't take extra arguments. "
            f"Given arguments: `{args[1:]}` will be ignored.",
            UserWarning,
        )

    # the directory the script is running in
    script_dir = pathlib.Path(__file__).parent
    env = dict(os.environ)

    # install latest setuptools: need to do this because setuptools < 60.0.0
    #                            uses deprecated distutils module.
    install_pre: List[str] = [
        PYTHON_BINARY,
        "-m",
        "pip",
        "install",
        "-U",
        "pip",
        "setuptools",
        "wheel",
    ]
    ret = subprocess.call(install_pre, env=env, cwd=script_dir)
    if ret != 0:
        print(
            "Setup failed! Check if you have a valid Python 3 binary "
            "on path. It is recommended to run this script in a "
            "virtual environment; if you are using a system-wide Python "
            f"installation, make sure that `{PYTHON_BINARY}` refers to the Python 3 "
            f"binary (run `{PYTHON_BINARY} --version` and check if it outputs "
            '"Python 3.x.x") and `pip` has been installed (check if '
            f"`{PYTHON_BINARY} -m pip` succeeds)."
        )
        sys.exit(1)

    # install dependencies
    install_deps: List[str] = [
        PYTHON_BINARY,
        "-m",
        "pip",
        "install",
        "-r",
        "requirements.txt",
    ]
    ret = subprocess.call(install_deps, env=env, cwd=script_dir)
    if ret == 0:
        print(
            "Setup completed successfully! Now you are ready to run the "
            "app and web. Run `python3 web.py` and "
            "`python3 app.py` to start the app and web."
        )
    else:
        print("Setup failed!")
        sys.exit(1)


if __name__ == "__main__":
    main(sys.argv)
