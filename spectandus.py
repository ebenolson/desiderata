#!/usr/bin/env python
# Author: Eben Olson <eben.olson@gmail.com>
# Licensed under the MIT license <http://opensource.org/licenses/MIT>

import logging
from colorlog import ColoredFormatter
import plac
import sys
import json
from fs import zipfs
from collections import defaultdict

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


def convert_index(reference, outfile):
    logger.info(u'Converting ZipFS directory index {} to hashmap'.format(reference))

    hashes = defaultdict(list)
    count = 0
    encoding = sys.getfilesystemencoding()
    with zipfs.ZipFS(reference, 'r', encoding=encoding) as hashfs:
        for logfilename in hashfs.walkfiles('/'):
            filehash = hashfs.open(logfilename).read()
            hashes[filehash].append(logfilename)
            count += 1
    logger.info(u'{} files with {} unique hashes found in index'.format(count, len(hashes)))
    logger.info(u'Writing results to {}'.format(outfile))
    json.dump(hashes, open(outfile, 'w'), indent=4)


def list_duplicates(reference, outfile):
    logger.info(u'Searching for duplicated files in {}'.format(reference))
    hashes = json.load(open(reference))
    duplicates = {}
    for filehash, files in hashes.items():
        if len(files) > 1:
            duplicates[filehash] = files
    logger.info(u'{} hashes with multiple files found out of {} in reference'.format(len(duplicates), len(hashes)))
    logger.info(u'Writing results to {}'.format(outfile))
    json.dump(duplicates, open(outfile, 'w'), indent=4)


def list_unmatched(reference, target, outfile):
    logger.info(u'Searching for files in {} not in reference {}'.format(target, reference))
    reference = json.load(open(reference))
    target = json.load(open(target))

    unmatched = {}
    logger.info(u'Reference has {} hashes, target has {}'.format(len(reference), len(target)))
    for filehash, files in target.items():
        if filehash not in reference:
            unmatched[filehash] = files
    if len(unmatched):
        logger.warn(u'{} hashes were not matched in reference'.format(len(unmatched)))
    else:
        logger.info(u'All hashes in target were found in reference')
    logger.info(u'Writing results to {}'.format(outfile))
    json.dump(unmatched, open(outfile, 'w'), indent=4)



@plac.annotations(
    convert=('List all files in reference (zipfile) as json hashmap', 'flag', 'c'),
    dupcheck=('Show all hashes in reference (json) with multiple files', 'flag', 'm'),
    newcheck=('Show all hashes in target (json) not in reference (json)', 'option', 'n'),
    debug=('Show all log output', 'flag', 'd'),
    reference='Reference index',
    )
def main(convert, dupcheck, newcheck, debug, reference, outfile='result.json'):
    if debug:
        logger.setLevel(logging.DEBUG)
    if convert:
        convert_index(reference, outfile)
    if dupcheck:
        list_duplicates(reference, outfile)
    if newcheck:
        list_unmatched(reference, newcheck, outfile)

if __name__ == '__main__':
    plac.call(main)
