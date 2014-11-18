#!/usr/bin/env python
# Desiderate Author: Eben Olson <eben.olson@gmail.com>
# MtHasher Author: Peter Wu <peter@lekensteyn.nl>
# Licensed under the MIT license <http://opensource.org/licenses/MIT>

from __future__ import print_function
import hashlib
import sys
import os
from os.path import join, getsize
from fs import zipfs

from threading import Thread
try:
    from queue import Queue
except:
    # Python 2 compatibility
    from Queue import Queue

def read_blocks(filename):
    if filename == '-':
        f = sys.stdin
        # Python 3 compat: read binary instead of unicode
        if hasattr(f, 'buffer'):
            f = f.buffer
    else:
        f = open(filename, 'rb')
    try:
        megabyte = 2 ** 20
        while True:
            data = f.read(megabyte)
            if not data:
                break
            yield data
    finally:
        f.close()

class Hasher(object):
    '''Calculate multiple hash digests for a piece of data.'''
    def __init__(self, algos):
        self.algos = algos
        self._hashes = {}
        for algo in self.algos:
            self._hashes[algo] = getattr(hashlib, algo)()

    def update(self, data):
        for h in self._hashes:
            h.update(data)

    def hexdigests(self):
        '''Yields the algorithm and the calculated hex digest.'''
        for algo in self.algos:
            digest = self._hashes[algo].hexdigest()
            yield algo, digest

class MtHasher(Hasher):
    # Queue size. Memory usage is this times block size (1M)
    QUEUE_SIZE = 10
    def __init__(self, algos):
        super(MtHasher, self).__init__(algos)
        self._queues = {}
        self._threads = {}
        for algo in algos:
            t = Thread(target=self._queue_updater, args=(algo,), name=algo)
            self._queues[algo] = Queue(MtHasher.QUEUE_SIZE)
            self._threads[algo] = t
            t.start()

    def _queue_updater(self, algo):
        q = self._queues[algo]
        h = self._hashes[algo]
        while True:
            data = q.get()
            # Treat an empty value as terminator
            if not data:
                break
            h.update(data)

    def update(self, data):
        if data:
            for q in self._queues.values():
                q.put(data)

    def hexdigests(self):
        # Wait until all calculations are done and yield the results in meantime
        for algo in self.algos:
            q = self._queues[algo]
            q.put(b'') # Terminate
            self._threads[algo].join()
            assert q.empty()
        return super(MtHasher, self).hexdigests()

algos = ('md5', 'sha1', 'sha512')

def print_usage():
    pass

def calculate_hash(filename):
    hasher = MtHasher(algos)
    # Try to read the file and update the hash states
    for data in read_blocks(filename):
        hasher.update(data)

    return u''.join((u'{0} {1}\n'.format(algo, digest) for algo, digest in hasher.hexdigests()))

def check_structure(rootdir, hashfile):
    print('Checking structure')
    with zipfs.ZipFS(hashfile, 'r') as hashfs:
        for root, dirs, files in os.walk(rootdir):
            for name in files:
                filename = join(root,name)
                if not hashfs.isfile(filename):
                    print('Hash missing: {0}'.format(filename))

        for filename in hashfs.walkfiles(rootdir):
            if not os.path.isfile(filename):
                print('File not found: {0}'.format(filename))

def verify_hashes(rootdir, hashfile):
    print('Verifying all hashes')

    with zipfs.ZipFS(hashfile, 'r') as hashfs:
        for filename in hashfs.walkfiles():
            print(filename)
    return
            #if hashfs.open(filename).read() != calculate_hash(filename):
                #print('Hash verification error: {0}'.format(filename))

def record_hashes(rootdir, hashfile):
    if os.path.exists(hashfile):
        print("Output file already exists!")
        raise IOError

    with zipfs.ZipFS(hashfile, 'w') as hashfs:
        hashfs.makedir(rootdir)
        for root, dirs, files in os.walk(rootdir):
            for dir in dirs:
                print(root, dir)
                hashfs.makedir(join(root, dir))

            for name in files:
                filename = join(root,name)
                print(filename)
                hasher = MtHasher(algos)
                # Try to read the file and update the hash states
                try:
                    for data in read_blocks(filename):
                        hasher.update(data)
                except OSError as e:
                    print('digest: {0}: {1}'.format(filename, e.strerror))
                    continue

                with hashfs.open(filename,'w') as hashfile:
                    hashfile.write(calculate_hash(filename))

def main(*argv):
    filenames = []

    if any(help_arg in argv for help_arg in ('-h', '--help')):
        print_usage()
        return 1

    for arg in argv:
        if arg.startswith('-') and arg != '-':
            algo = arg.lstrip('-')  # Strip leading '-'
            if algo in supported_algos:
                # Preserve ordering, ignore duplicates
                if not algo in algos:
                    algos.append(algo)
            else:
                print('Unsupported algo:', algo, file=sys.stderr)
        else:
            filenames.append(arg)

    if not algos:
        print('Missing digest!', file=sys.stderr)
        print_usage()
        return 1

    # Assume stdin if no file is given
    record_hashes(filenames[0], filenames[1])
    check_structure(filenames[0], filenames[1])
    verify_hashes(filenames[0], filenames[1])

if __name__ == '__main__':
    sys.exit(main(*sys.argv[1:]))