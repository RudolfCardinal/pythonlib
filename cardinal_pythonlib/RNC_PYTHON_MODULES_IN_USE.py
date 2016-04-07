#!/usr/bin/python
#
# Script to install a bunch of Python modules
#
# Author: Rudolf Cardinal
# Copyright (C) 2012-2015 Rudolf Cardinal.
# License: http://www.apache.org/licenses/LICENSE-2.0
#
# Run with e.g.:
#
# rm RNC_PYTHON_MODULES_IN_USE.py
# wget http://egret.psychol.cam.ac.uk/pythonlib/RNC_PYTHON_MODULES_IN_USE.py
# chmod u+x RNC_PYTHON_MODULES_IN_USE.py
# ./RNC_PYTHON_MODULES_IN_USE.py

NEED_PIP = "sudo apt-get install python-pip && "

MODULES = {
    "argparse": "",
    "atexit": "",
    "base64": "",
    "bcrypt": "sudo apt-get install python-bcrypt",
    "binascii": "",
    "bs64": "sudo apt-get install python-bs4",
    "cgi": "",
    "cgitb": "",
    "codecs": "",
    "collections": "",
    "ConfigParser": "",
    "Cookie": "",
    # ... thought it was nonstandard but it's on the Python standard library;
    # see Python site and "dpkg -S /usr/lib/python2.7/Cookie.py" or similar
    "cStringIO": "",
    "csv": "",
    "datetime": "",
    "dateutil": "sudo apt-get install python-dateutil",
    "docx": "sudo pip install docx",
    "email": "",
    "errno": "",
    "getpass": "",
    "gzip": "",
    "hashlib": "",
    "io": "",
    "logging": "",
    "M2Crypto": "sudo apt-get install python-m2crypto",
    "math": "",
    "matplotlib": "sudo apt-get install python-matplotlib",
    "mmap": "",
    "MySQLdb": "sudo apt-get install python-mysqldb",
    "numpy": "sudo apt-get install python-numpy",
    "optparse": "",
    "os": "",
    "pdfminer": "sudo pip install pdfminer",
    "pypyodbc": "",  # non-standard ***; better for iffy Windows setups
    # "pyodbc": "sudo apt-get install python-pyodbc",
    # ... NEEDS SPECIFIC COMPILER SUPPORT UNDER WINDOWS (use pypyodbc instead)
    "pyPdf": "sudo apt-get install python-pypdf",
    "pyth": "sudo apt-get install python-pyth",
    "pytz": "sudo apt-get install python-tz",
    "re": "",
    "regex": "sudo apt-get install python-regex",
    "scipy": "sudo apt-get install python-scipy",
    "sgmllib": "",  # non-standard ***
    "shlex": "",
    "shutil": "",
    "smtplib": "",
    "socket": "",
    "sortedcontainers": "sudo pip install sortedcontainers",
    # "sqlalchemy": NEED_PIP + "sudo pip install SQLAlchemy",
    # ... don't use apt-get (old version)
    "string": "",
    "StringIO": "",
    "subprocess": "",
    "sys": "",
    "tempfile": "",
    "time": "",
    "threading": "",
    "tkFileDialog": "",  # non-standard? ***
    "Tkinter": "",  # non-standard? ***
    "tokenize": "",
    "urlimport": NEED_PIP + "sudo pip install urlimport",
    "urllib": "",
    "win32console": "",  # non-standard ***
    "xhtml2pdf": NEED_PIP + "sudo pip install xhtml2pdf",
    # ... xhtml2pdf REPLACES python-pisa
    "xlrd": "sudo apt-get install python-xlrd",
    "xlwt": "sudo apt-get install python-xlwt",
    "xml": "",
    "zipfile": "",
}


def import_or_install(package, command):
    # http://stackoverflow.com/questions/6677424
    # http://docs.python.org/2/library/functions.html#__import__
    # http://stackoverflow.com/questions/1057843
    # http://stackoverflow.com/questions/89228

    import subprocess
    try:
        __import__(package, globals=globals())
    except:
        subprocess.call(command, shell=True)


def main():
    for package, command in MODULES.iteritems():
        import_or_install(package, command)


if __name__ == "__main__":
    main()
