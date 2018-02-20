import os
import hashlib
import re

from collections import defaultdict

# This matches a newline, a space, tab, return character OR a null value: between the | and )
_whitespace = re.compile('^([\n \t\r]|)+$')


# Used with checksum functions
def _iter_read(filename: str, chunk_size=65536) -> bytes:
    with open(filename, 'rb') as file:
        for chunk in iter(lambda: file.read(chunk_size), b''):
            yield chunk


def access_date(filename: str) -> str:
    access_date = os.path.getmtime(filename)
    return str(access_date)


def modification_date(filename: str) -> str:
    modification_time = os.path.getmtime(filename)
    return str(modification_time)


def file_name(filename: str) -> str:
    file_basename = os.path.basename(filename)
    return str(file_basename)


def disk_size(filename: str) -> str:
    byte_usage = os.path.getsize(filename)
    return str(byte_usage)


def md5_sum(filename, chunk_size=65536) -> str:
    checksumer = hashlib.md5()
    for chunk in _iter_read(filename, chunk_size):
        checksumer.update(chunk)
    file_hash = checksumer.hexdigest()
    return str(file_hash)


def sha256_sum(filename, chunk_size=65536) -> str:
    checksumer = hashlib.sha256()
    for chunk in _iter_read(filename, chunk_size):
        checksumer.update(chunk)
    file_hash = checksumer.hexdigest()
    return str(file_hash)


def partial_md5_sum(filename, chunk_size=65536, chunks_read=200) -> str:
    checksumer = hashlib.md5()
    with open(filename, 'rb') as file:
        for null in range(0, chunks_read):
            chunk = file.read(chunk_size)
            if chunk == b'':
                break
            checksumer.update(chunk)
    return checksumer.hexdigest()


def direct_compare(filename) -> bytes:
    with open(filename, 'rb') as file:
        data = file.read()
    return data


def first_filter(func, paths: iter):
    grouped_duplicates = defaultdict(list)
    for path in paths:
        if os.path.isfile(path):
            item_hash = func(path)
            if len(item_hash) < 10 and _whitespace.match(str(item_hash)):
                # Just a newline means no output
                continue
            grouped_duplicates[item_hash].append(path)
    for duplicate in grouped_duplicates.values():
        yield duplicate


def duplicate_filter(func, duplicates: iter):
    '''
    Takes list of duplicates, compares their checksum and returns a source value,
    and duplicates identified with it as a dictionary
    :func object Takes function and applies to iterable of duplicates
    :duplicates List of duplicates
    :return: dictionary
    '''
    for duplicate_list in duplicates:
        filtered_duplicates = list()
        if len(duplicate_list) > 1:
            first, *others = duplicate_list
            filtered_duplicates.append(first)
            source_hash = func(first)
            for item in others:
                item_hash = func(item)
                if len(item_hash) < 10 and _whitespace.match(str(item_hash)):
                    # Just a newline means no output
                    continue
                if item_hash == source_hash:
                    filtered_duplicates.append(item)
        yield filtered_duplicates


if __name__ == '__main__':
    print(md5_sum("tests/file_properties/hash"))
    print(partial_md5_sum("tests/file_properties/hash"))
    print(sha256_sum("tests/file_properties/hash"))

    print(disk_size("tests/file_properties/5120_byte"))
    print(modification_date("tests/file_properties/5120_byte"))
