#!/usr/bin/env python3

import argparse
import functools
import itertools
import logging
import os
import sys

from util.ArgumentParsing import parser_logic
from util.DirectorySearch import directory_search
from util.FileActions import hardlink_files, remove_files
from util.FileProperties import DuplicateFilters
from util.Logging import log_levels

import util.FileProperties


def main():
    assert sys.version_info >= (3, 6), "Requires Python3.6 or greater"

    available_filters = util.FileProperties.list_filters()

    def negation(func):
        def wrapper(*args, **kwargs):
            return not func(*args, **kwargs)
        return wrapper
    conditions = {
        "is_file": os.path.isfile,
        "not_symbolic_link": negation(os.path.islink),
        "not_empty": lambda filename: os.path.getsize(filename) > 0,
    }

    parser = argparse.ArgumentParser()
    parser = parser_logic(parser)
    args = parser.parse_args()

    if args.follow_symbolic is True:
        conditions.pop("not_symbolic_link")
    if args.empty_file is True:
        conditions.pop("not_empty")

    if args.verbosity:
        logging.basicConfig(level=log_levels.get(args.verbosity, 3),
                            stream=sys.stderr,
                            format='[%(levelname)s] %(message)s')
    else:
        logging.disable(logging.CRITICAL)

    # Choose only last duplicate action
    if args.duplicate_action:
        duplicate_action = args.duplicate_action[-1]
    else:
        duplicate_action = None

    args.threshold = args.threshold if args.threshold > 1 else 1

    # Default filtering methods
    args.filters = args.filters if args.filters else ["size", "md5"]

    # Get all file paths
    # Usage of set to remove duplicate directory entries
    paths = (path for directory in set(args.directories)
             for path in directory_search(directory,
                                          recursive=args.recursive,
                                          follow_hidden=args.follow_hidden,
                                          max_depth=args.max_depth,
                                          include=args.include,
                                          exclude=args.exclude,
                                          dir_include=args.dir_include,
                                          dir_exclude=args.dir_exclude,
                                          )
             )

    # Get first (blocking) filter method, group other filter methods
    filter_methods = (available_filters[filter_method]
                      if type(filter_method) is str
                      else filter_method
                      for filter_method in args.filters)
    filtered_duplicates = DuplicateFilters(filters=filter_methods, filenames=paths, conditions=conditions.values())

    def dup_action_link(duplicates):
        for duplicate_result in duplicates:
            if len(duplicate_result) >= args.threshold:
                first, *others = duplicate_result
                hardlink_files(itertools.repeat(first), others)

    def dup_action_remove(duplicates):
        for duplicate_result in duplicates:
            if len(duplicate_result) >= args.threshold:
                remove_files(duplicate_result[1:])

    # Take the first file in a group as the source,
    # and remove and then hard link the source file to each target path
    if duplicate_action == "link":
        filtered_duplicates = list(filtered_duplicates)
        dup_action_link(filtered_duplicates)

    # Removes all but the first first identified in the group
    elif duplicate_action == "remove":
        dup_action_remove(filtered_duplicates)

    # Custom shell action supplied by --exec-group
    # Uses references to tracked filters in filter_hashes as {f1} {fn}
    # Uses parallel brace expansion, {}, {.}, {/}, {//}, {/.}
    # Also includes expansion of {..}, just includes filename extension
    elif type(duplicate_action) is functools.partial:
        for index, results in enumerate(filtered_duplicates):
            if len(results) >= args.threshold:
                # Take each filters output and label f1: 1st_output, fn: n_output...
                # Strip filter_output because of embedded newline
                labeled_filters = {f"f{filter_number + 1}": filter_output.strip()
                                   for filter_number, filter_output in enumerate(filtered_duplicates.filter_hashes[index])}
                for result in results:
                    # Executes the command given and returns its output if available
                    command_string = duplicate_action(result, **labeled_filters)
                    print(command_string, end='')  # Shell commands already have newline
    else:
        if args.interactive is True:
            # If interactive, it will list the grouped files and then need to act on it.
            # Because output is through a generator, generate all results and store them
            filtered_duplicates = tuple(filtered_duplicates)

        # Print all groups.
        for index, result in enumerate(filtered_duplicates):
            if len(result) >= args.threshold:
                if args.basic_formatting:
                    logging.info(' -> '.join(filtered_duplicates.filter_hashes[index]))
                    print('\n'.join((str(dup)) for dup in result), end='\n')
                else:
                    source_file, *duplicates = result
                    logging.info(' -> '.join(filtered_duplicates.filter_hashes[index]))
                    print(source_file)
                    if duplicates:
                        print('\n'.join((str(dup).rjust(len(dup) + 4) for dup in duplicates)), end='\n\n')
                    else:
                        print('')

        # A messy implementation to a interactive dialog
        if args.interactive is True:
            action_on_duplicated = None
            try:
                while action_on_duplicated not in {"1", "2", "3", "exit" "link", "remove"}:
                    action_on_duplicated = str(input("Select action: \n1) link \n2) remove\n3) exit\n"))
                if action_on_duplicated in {"3", "exit"}:
                    raise KeyboardInterrupt
            except KeyboardInterrupt:
                exit("\nExiting...")

            interactive_actions = {
                "1": dup_action_link,
                "link": dup_action_link,
                "2": dup_action_remove,
                "remove": dup_action_remove,
            }
            action_on_duplicated = action_on_duplicated.lower()
            interactive_actions[action_on_duplicated](filtered_duplicates)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("")
        exit(1)
