import os
import pathlib


def directory_search(directory: str, *,
                     recursive=True, max_depth=None, dir_hidden=None,
                     include=None, exclude=None,
                     dir_include=None, dir_exclude=None
                     ) -> tuple:
    orig_directory = os.path.expanduser(directory)
    orig_directory_hidden = hidden_in_dir(directory)

    directory_depth = 0
    for directory, subdir, files in os.walk(orig_directory):

        # Skip hidden directories if specified
        if all((
                dir_hidden is not True,
                orig_directory_hidden is not True,
                hidden_in_dir(directory))
                ):
            continue

        # Check for included and excluded directories
        # If directory matches, skip it
        if dir_include or dir_exclude:
            if not dir_include_exclude(directory, include=dir_include, exclude=dir_exclude):
                continue
        if include or exclude:
            for directory, file in file_include_exclude(files,
                                                        directory=directory,
                                                        include=include,
                                                        exclude=exclude
                                                        ):
                yield os.path.join(directory, file)
        else:
            for file in files:
                yield os.path.join(directory, file)

        # Break after 1st iteration to prevent recursiveness
        # If max-depth is specified, break after specified number
        if recursive is False:
            break
        elif max_depth is int and max_depth > 0:
            directory_depth += 1
            if directory_depth == max_depth:
                break


def dir_include_exclude(directory, *, include=None, exclude=None):
    if include or exclude:
        if include is not None:
            include_check = [True if item in directory else False for item in include]
            if all(include_check):
                return True
            else:
                return False
        if exclude is not None:
            exclude_check = [True if item in directory else False for item in exclude]
            if not all(exclude_check) and len(exclude_check) > 0:
                return True
            else:
                return False
    else:
        return True


def file_include_exclude(files, *, directory, include, exclude):
    if include:
        included_filenames = {file for glob_match in include
                              for file in files
                              if pathlib.PurePath(file).match(glob_match)}
    else:
        included_filenames = set()
    if exclude:
        excluded_filenames = {file for glob_match in exclude
                              for file in files
                              if pathlib.PurePath(file).match(glob_match)}
    else:
        excluded_filenames = set()

    for file in files:
        if file in included_filenames:
            yield (directory, file)
        elif file not in excluded_filenames and len(excluded_filenames) > 0:
            yield (directory, file)


def hidden_in_dir(directory):
    # Windows portion
    # https://stackoverflow.com/a/14063074
    split_directory = os.path.normpath(directory).split(os.sep)
    if os.name == 'nt':
        import win32api, win32con
        # Tests if a hidden windows directory
        for fragment_dir in split_directory:
            attribute = win32api.GetFileAttributes(fragment_dir)
            if attribute and (win32con.FILE_ATTRIBUTE_HIDDEN or win32con.FILE_ATTRIBUTE_SYSTEM):
                return True
        return False
    else:
        for fragment_dir in split_directory:
            if all((
                fragment_dir.startswith('.'),
                not fragment_dir == '.',
                not fragment_dir.startswith('..'),
            )):
                return True
        return False


if __name__ == '__main__':
    pass
