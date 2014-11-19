#!/usr/bin/env python
# Desiderata Author: Eben Olson <eben.olson@gmail.com>
# MtHasher Author: Peter Wu <peter@lekensteyn.nl>
# Licensed under the MIT license <http://opensource.org/licenses/MIT>

import hashlib
import logging
from colorlog import ColoredFormatter
import plac
import sys, os
from fs import zipfs

formatter = ColoredFormatter(
        "%(log_color)s%(levelname)-8s%(reset)s %(white)s%(message)s",
        datefmt=None,
        reset=True,
        log_colors={
                'DEBUG':    'cyan',
                'INFO':     'green',
                'WARNING':  'yellow',
                'ERROR':    'red',
                'CRITICAL': 'red',
        }
)

stream = logging.StreamHandler()
stream.setFormatter(formatter)

logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.addHandler(stream)

def read_blocks(filename):
    with open(filename, 'rb') as f:
        while True:
            data = f.read(2**20)
            if not data:
                break
            yield data

algos = ('md5', 'sha1', 'sha512')

class Hasher(object):
    '''Calculate multiple hash digests for a piece of data.'''
    def __init__(self, algos):
        self.algos = algos
        self._hashes = {}
        for algo in self.algos:
            self._hashes[algo] = getattr(hashlib, algo)()
    def update(self, data):
        for h in self._hashes.values():
            h.update(data)
    def hexdigests(self):
        '''Yields the algorithm and the calculated hex digest.'''
        for algo in self.algos:
            digest = self._hashes[algo].hexdigest()
            yield algo, digest

def calculate_hash(filename):
    hasher = Hasher(algos)
    # Try to read the file and update the hash states
    for data in read_blocks(filename):
        hasher.update(data)

    return u''.join((u'{0} {1}\n'.format(algo, digest) for algo, digest in hasher.hexdigests()))

def check_structure(rootdir, hashfile):
    logger.info('Checking directory structure')
    with zipfs.ZipFS(hashfile, 'r') as hashfs:
        for root, dirs, files in os.walk(rootdir):
            for name in files:
                filename = os.path.join(root,name)
                logger.debug(filename)
                if not hashfs.isfile(filename):
                    logger.warn('Hash missing: {0}'.format(filename))

        for filename in hashfs.walkfiles(rootdir):
            logger.debug(filename)
            if not os.path.isfile(filename):
                logger.error('File not found: {0}'.format(filename))
    logger.info('Check complete')   

def verify_hashes(rootdir, hashfile):
    logger.info('Verifying all hashes')

    with zipfs.ZipFS(hashfile, 'r') as hashfs:
        for filename in hashfs.walkfiles(rootdir):
            logger.debug(filename)
            if not os.path.isfile(filename):
                logger.error('File not found: {0}'.format(filename))
            elif hashfs.open(filename).read() != calculate_hash(filename):
                logger.error('Hash verification error: {0}'.format(filename))
    logger.info('Verification complete')   

def record_hashes(rootdir, hashfile):
    logger.info('Recording all hashes')   
    if os.path.exists(hashfile):
        logger.error("Output file already exists!")
        return

    with zipfs.ZipFS(hashfile, 'w') as hashfs:
        hashfs.makedir(rootdir)
        for root, dirs, files in os.walk(rootdir):
            for dir in dirs:
                hashfs.makedir(os.path.join(root, dir))
            for name in files:
                filename = os.path.join(root,name)
                logger.debug(filename)
                with hashfs.open(filename,'w') as hashfile:
                    hashfile.write(calculate_hash(filename))
        hashfs.close()
    logger.info('Recording complete')   

@plac.annotations(
    record=('Record hashes for all files', 'flag', 'r'), 
    check=('Check directory for missing or added files', 'flag', 'c'), 
    verify=('Verify hashes for all files', 'flag', 'v'),
    target='Target directory',    
    )
def main(record, check, verify, target, outfile='hashes.zip'):
    if record:
        record_hashes(target, outfile)
    if check:
        check_structure(target, outfile)
    if verify:
        verify_hashes(target, outfile)

if __name__ == '__main__':
    plac.call(main)