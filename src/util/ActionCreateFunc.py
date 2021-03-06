import datetime
import logging
import os
import pprint
import shutil
from functools import partial

from util.Templates import ActionAppendCreateFunc
from util.Templates import EscapedBraceExpansion
from util.Templates import invoke_shell
from util.Templates import sanitize_object

log = logging.getLogger(__name__)


def print_results(filtered_group, *, basic_formatting=False, labeled_filters):
    log.info(' -> '.join(' '.join(sanitize_object(filter_output).splitlines())
                         for filter_output in labeled_filters.values()))
    if basic_formatting is True:
        for grp in filtered_group:
            yield grp + '\n'
    else:
        first_filename, *group = filtered_group
        yield first_filename + '\n'
        if len(group) > 0:
            for filename in group:
                padding = len(filename) + 4
                yield filename.rjust(padding) + '\n'


class ActionAppendExecShell(ActionAppendCreateFunc):
    def _process(self, template):
        command_template_format = EscapedBraceExpansion(template)

        shell_command = partial(self._group_invoke_shell, command=command_template_format)
        return shell_command

    @staticmethod
    def _group_invoke_shell(filtered_group, command, labeled_filters, **kwargs):
        for file in filtered_group:
            output = invoke_shell(file, command=command, labeled_filters=labeled_filters, **kwargs)
            output = sanitize_object(output)
            yield output


def remove_files(filtered_group: iter, labeled_filters, **kwargs):
    files_to_remove = filtered_group[1:]
    if len(files_to_remove) > 0:
        warning_message = "Are you sure you wish to remove and hard link the following duplicate files?"
        print(warning_message)
        pprint.pprint(files_to_remove)
        warning_response = input("Y/N ").upper()

        if warning_response and warning_response != 'Y':
            print('Exiting...')
            exit(1)

        for filename in files_to_remove:
            try:
                log.info("Removing {file}".format(file=sanitize_object(filename)))
                os.remove(filename)
            except FileNotFoundError:
                log.warning("{} Not Found".format(sanitize_object(filename)))
        return None
    else:
        return None


def hardlink_files(filtered_group: iter, labeled_filters, **kwargs):
    source_file, *files_to_link = filtered_group
    if len(files_to_link) > 0:
        warning_message = "Are you sure you wish to remove and hard link the following duplicate files?"
        print(warning_message)
        pprint.pprint(files_to_link)
        warning_response = input("Y/N ").upper()

        if warning_response and warning_response != 'Y':
            print('Exiting...')
            exit(1)

    for filename in files_to_link:
        try:
            log.info("Linking {source_file} -> {filename}".format(
                source_file=sanitize_object(source_file),
                filename=sanitize_object(filename)))
            os.remove(filename)
            os.link(source_file, filename)
        except FileNotFoundError:
            log.warning("{} Not Found".format(sanitize_object(filename)))
    return None


class ActionAppendMerge(ActionAppendCreateFunc):
    @classmethod
    def overwrite_flags(cls):
        flags = {
            "COUNT": cls._count,
            "IGNORE": cls._ignore,
            "ERROR": cls._error,

            "LARGER": partial(cls._condition, condition='LARGER'),
            "SMALLER": partial(cls._condition, condition='SMALLER'),
            "NEWER": partial(cls._condition, condition='NEWER'),
            "OLDER": partial(cls._condition, condition='OLDER'),
            }
        return flags

    def _process(self, template):
        mergedir_flag = template

        if ":" in mergedir_flag:
            mergedir_flag = mergedir_flag.split(":", 1)
            if len(mergedir_flag) == 2:
                merge_dir, overwrite_flag = mergedir_flag
        else:
            merge_dir = mergedir_flag
            overwrite_flag = None

        if overwrite_flag is not None:
            try:
                overwrite_method = self.overwrite_flags()[overwrite_flag.upper()]
            except KeyError as e:
                log.error('{} is not a valid key'.format(e))
                exit(1)
        else:
            overwrite_method = self._count

        if os.path.exists(merge_dir):
            log.error("{} already exists".format(sanitize_object(merge_dir)))
            exit(1)
        else:
            os.makedirs(merge_dir)

        callable_ = partial(self._abstract_call,
                            merge_dir=merge_dir,
                            overwrite_method=overwrite_method)
        return callable_

    @staticmethod
    def _abstract_call(filtered_group, *, merge_dir, overwrite_method, labeled_filters):
        filter_dir = os.path.join(merge_dir, *labeled_filters.values())
        os.makedirs(filter_dir)
        output = overwrite_method(filter_dir, filter_group=filtered_group)
        return output

    @staticmethod
    def _count(filter_dir, filter_group):
        # This keeps the left padding of 0's
        def incr_count(count):
            return str(int(count) + 1).zfill(len(count))

        def create_file_path(dir_, filename, count=None, fileext=None):
            if count is not None:
                filename = '_'.join([filename, count])
            if fileext is not None:
                filename = ''.join([filename + fileext])
            dest_dir_file = os.path.join(dir_, filename)
            return dest_dir_file

        for file in filter_group:
            filename = os.path.split(file)[1]
            filename_split = os.path.splitext(filename)

            dest_dir_file = os.path.join(filter_dir, filename)
            if os.path.exists(dest_dir_file):
                count = '0000'
                dest_dir = filter_dir
                dest_dir_file = create_file_path(dest_dir, filename)
                while os.path.exists(dest_dir_file):
                    count = incr_count(count)
                    if filename_split[1] == '':
                        dest_file = os.path.join(filename_split[0] + "_{}".format(count))
                    else:
                        dest_file = os.path.join(filename_split[0] + "_{}".format(count) + filename_split[1])
                    dest_dir_file = os.path.join(dest_dir, dest_file)
                log.info('Incrementing {} to {}'.format(sanitize_object(filename),
                                                        sanitize_object(dest_file)))
                shutil.copy(file, dest_dir_file)
                yield dest_dir_file + '\n'
            else:
                dest_dir_file = os.path.join(filter_dir, filename)
                shutil.copy(file, dest_dir_file)
                yield dest_dir_file + '\n'

    @staticmethod
    def _ignore(filter_dir, filter_group):

        for file in filter_group:
            filename = os.path.split(file)[1]
            dest_file = os.path.join(filter_dir, filename)
            if os.path.exists(dest_file):
                msg = "{} Exists, Ignoring {}".format(
                    sanitize_object(dest_file),
                    sanitize_object(file))
                log.info(msg)
                continue
            else:
                dest_dir_file = os.path.join(filter_dir, filename)
                shutil.copy(file, dest_dir_file)
                yield dest_dir_file + '\n'

    @staticmethod
    def _error(filter_dir, filter_group):
        for file in filter_group:
            filename = os.path.split(file)[1]
            dest_dir_file = os.path.join(filter_dir, filename)
            if os.path.exists(dest_dir_file):
                log.error('{} already exists, exiting'.format(sanitize_object(dest_dir_file)))
                exit(1)
            else:
                dest_dir_file = os.path.join(filter_dir, filename)
                shutil.copy(file, dest_dir_file)
                yield dest_dir_file + '\n'

    @staticmethod
    def _condition(filter_dir, filter_group, *, condition=None):
        assert condition is not None

        def modification_date(filename: str) -> str:
            modification_time = os.path.getmtime(filename)
            modified_datetime = datetime.datetime.fromtimestamp(modification_time)
            return str(modified_datetime)

        def disk_size(filename: str) -> str:
            byte_usage = os.path.getsize(filename)
            return str(byte_usage)

        conditions = {
            'LARGER' : lambda file1, file2: disk_size(file1) > disk_size(file2),
            'SMALLER': lambda file1, file2: disk_size(file1) < disk_size(file2),
            'NEWER'  : lambda file1, file2: modification_date(file1) < modification_date(file2),
            'OLDER'  : lambda file1, file2: modification_date(file1) > modification_date(file2),
        }
        condition = conditions[condition.upper()]

        for file in filter_group:
            filename = os.path.split(file)[1]
            dest_dir_file = os.path.join(filter_dir, filename)
            if os.path.exists(dest_dir_file):
                if condition(file, dest_dir_file):
                    log.info("{} overwriting {}".format(sanitize_object(file),
                                                        sanitize_object(dest_dir_file)))
                    shutil.copy(file, dest_dir_file)
                    yield dest_dir_file + '\n'
            else:
                dest_dir_file = os.path.join(filter_dir, filename)
                shutil.copy(file, dest_dir_file)
                yield dest_dir_file + '\n'


