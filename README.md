Desiderata
=====================

Description
-------------------
Desiderata (Latin: "desired things") is a simple script to generate a catalog of file hashes, and to verify that those hashes are correct.

Motivation
-------------------
Most people have digital assets such as photographs or writing which are both irreplacable and of great personal value. However, while digital storage continues to improve in both price and capacity, reliability remains an issue. Data can be lost to accidental deletion, hardware failure, or [bit rot](http://en.wikipedia.org/wiki/Data_degradation). 

Proper backup procedures can guard against catastrophic loss, and integrity-checking filesystems like [ZFS](http://en.wikipedia.org/wiki/ZFS) offer strong protection against slow corruption. However, unless you are familiar with filesystem programming, you will to some degree have to take it on faith that `zpool scrub` is getting the job done.

Desiderata is intended to provide a "security blanket" for your most valuable files. When run, the script walks a target directory and records a hash of each file. You can then re-run it periodically to verify that none of the files have gone missing or been altered. When you add new files, just record an updated catalog.

Usage
-------------------
Don't use it. To fulfill its purpose, Desiderata needs to be trusted, and the best way to accomplish that is for the user to implement it themselves. At the very least you should read through the source and convince yourself it's doing what it claims. 

If you are familiar with a language besides Python, pull requests of your version would be greatly appreciated.

However, if you just want to run it:

usage: desiderata.py [-h] [-r] [-c] [-v] [-d] target [outfile]

positional arguments:
  target        Target directory
  outfile       [hashes.zip]

optional arguments:
  -h, --help    show this help message and exit
  -r, --record  Record hashes for all files
  -c, --check   Check directory for missing or added files
  -v, --verify  Verify hashes for all files
  -d, --debug   Show all log output
