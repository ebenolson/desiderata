#!/usr/bin/env python
# Desiderata Author: Eben Olson <eben.olson@gmail.com>
# MtHasher Author: Peter Wu <peter@lekensteyn.nl>
# Licensed under the MIT license <http://opensource.org/licenses/MIT>

import hashlib
import logging
from colorlog import ColoredFormatter
import plac
import sys
import os
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

    count = 0
    encoding = sys.getfilesystemencoding()
    with zipfs.ZipFS(hashfile, 'r', encoding=encoding) as hashfs:
        for root, dirs, files in os.walk(rootdir):
            for name in files:
                count += 1
                filename = unicode(os.path.join(root,name), encoding=encoding)
                logfilename = ''.join(filename.split(rootdir)[1:])
                logger.debug(filename)
                if not hashfs.isfile(logfilename):
                    logger.warn(u'Hash missing: {0}'.format(filename))

        for logfilename in hashfs.walkfiles('/'):
            filename = os.path.join(rootdir, logfilename[1:])
            logger.debug(filename)
            if not os.path.isfile(filename):
                logger.error(u'File not found: {0}'.format(filename))
    logger.info(u'Check complete, located {} files'.format(count))


def verify_hashes(rootdir, hashfile):
    logger.info('Verifying all hashes')

    count = 0

    encoding = sys.getfilesystemencoding()
    with zipfs.ZipFS(hashfile, 'r', encoding=encoding) as hashfs:
        for logfilename in hashfs.walkfiles('/'):
            count += 1
            filename = os.path.join(rootdir, logfilename[1:])
            logger.debug(filename)
            if not os.path.isfile(filename):
                logger.error(u'File not found: {0}'.format(filename))
            elif hashfs.open(logfilename).read() != calculate_hash(filename):
                logger.error(u'Hash verification error: {0}'.format(filename))
    logger.info(u'Verification complete, {} files checked'.format(count))


def record_hashes(rootdir, hashfile):
    logger.info('Recording all hashes')
    if os.path.exists(hashfile):
        logger.error(u'Output file already exists!')
        return

    count = 0
    encoding = sys.getfilesystemencoding()
    with zipfs.ZipFS(hashfile, 'w', encoding=encoding) as hashfs:
        hashfs.makedir(rootdir)
        for root, dirs, files in os.walk(rootdir):
            for dir in dirs:
                if os.path.islink(os.path.join(root, dir)):
                    continue
                hashfs.makedir(os.path.join(root, dir))
            for name in files:
                count += 1
                filename = unicode(os.path.join(root, name), encoding=encoding)
                if os.path.islink(filename):
                    continue
                logfilename = ''.join(filename.split(rootdir)[1:])
                logger.debug('{}: {}'.format(filename, logfilename))
                with hashfs.open(logfilename, 'w') as hashfile:
                    hashfile.write(calculate_hash(filename))
        hashfs.close()
    logger.info(u'Recording complete, hashed {} files'.format(count))


@plac.annotations(
    record=('Record hashes for all files', 'flag', 'r'),
    check=('Check directory for missing or added files', 'flag', 'c'),
    verify=('Verify hashes for all files', 'flag', 'v'),
    debug=('Show all log output', 'flag', 'd'),
    target='Target directory',
    )
def main(record, check, verify, debug, target, outfile='hashes.zip'):
    if debug:
        logger.setLevel(logging.DEBUG)
    if record:
        record_hashes(target, outfile)
    if check:
        check_structure(target, outfile)
    if verify:
        verify_hashes(target, outfile)

if __name__ == '__main__':
    plac.call(main)
