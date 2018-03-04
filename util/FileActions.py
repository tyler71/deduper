import os

from util.Templates import ActionTemplate


def remove_files(filenames: iter) -> list:
    removed_files = list()
    for filename in filenames:
        print("Removing {file}".format(file=filename))
        try:
            os.remove(filename)
            removed_files.append(filename)
        except FileNotFoundError:
            print("Not Found")
    return removed_files


def hardlink_files(source_files: iter, group_files: iter) -> list:
    linked_files = list()
    for source_file, filename in zip(source_files, group_files):
        print("Linking {source_file} -> {filename}".format(source_file=source_file, filename=filename))
        try:
            os.remove(filename)
            os.link(source_file, filename)
            linked_files.append((source_file, filename))
        except FileNotFoundError:
            print("Not Found")
    return linked_files

class ActionMerge(ActionTemplate):
    def _process(self, template):
        self.overwrite_flags = {
            "COUNT": self._count,
            "IGNORE": self._ignore,
            "ERROR": self._error,
            "CONDITION": self._condition,
        }
        if ":" in template:
            self.template = template.split(":")
        else:
            self.merge_dir = template
        if len(template) == 2:
            self.merge_dir, self.overwrite_flag = template
        elif len(template) == 3:
            self.merge_dir, self.overwrite_flag, self.condition = template

        return self._abstract_call


    def _abstract_call(self, condition=None, *, merge_dir, overwrite_flag, filter_group, hashes):
        overwrite = self.overwrite_flags[overwrite_flag]
        if overwrite_flag.upper() == 'CONDITION':
            assert condition is not None

        self.filter_dir = os.path.join(merge_dir, *hashes)
        if not os.path.exists(merge_dir):
            os.makedirs(merge_dir)
        if len(os.listdir(merge_dir)) == 0:
            os.makedirs(self.filter_dir)
        overwrite(condition, filter_group=filter_group)



    def _count(self, filter_group, * filter_dir):
        for file in filter_group:
            filename = os.path.splitext(file)[1]
            count = 0000
            if os.path.exists():
                pass


    def _ignore(self, filter_group):
        pass

    def _error(self, filter_group):
        pass

    def _condition(self, filter_group, *, condition):
        pass
