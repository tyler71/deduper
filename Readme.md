# **groupby**

*groupby* is a dedicated tool for grouping filenames by their properties.

## Features
* Simple to use: `groupy` will return grouped results in current directory
* Predefined filters or use your own
* Regular Expression filter
* Supports similar GNU Parallel notation
* Execute commands on each grouped file
* Ignore or prefer specific directories or files
* Ignores (unless specified)
  * Hidden directories
  * Empty files
  * Symbolic links

## Syntax
```buildoutcfg
usage: groupby.py [-h]
                  [-f {partial_md5,md5,sha256,modified,accessed,size,filename,file}]
                  [-E FILTERS] [-s FILTERS] [-x GROUP_ACTION] [-m merge_dir]
                  [--exec-remove] [--exec-link] [--include INCLUDE]
                  [--exclude EXCLUDE] [--dir-include DIR_INCLUDE]
                  [--dir-exclude DIR_EXCLUDE] [--dir-hidden] [-r]
                  [-t THRESHOLD] [--basic-formatting] [--max-depth MAX_DEPTH]
                  [--empty-file] [--follow-symbolic] [-v]
                  [directory [directory ...]]

positional arguments:
  directory

optional arguments:
  -h, --help            show this help message and exit
  -f {partial_md5,md5,sha256,modified,accessed,size,filename,file}, --filter {partial_md5,md5,sha256,modified,accessed,size,filename,file}
                        Filenames represented as {}: --shell "du {} | cut -f1"
  -E FILTERS, --filter-regex FILTERS
  -s FILTERS, --filter-shell FILTERS
  -x GROUP_ACTION, --exec-shell GROUP_ACTION
                        Filenames represented as {}, filters as {f1}, {fn}...:
                        --exec-group "echo {} {f1}"
  -m merge_dir, --exec-merge merge_dir
                        Includes 4 options including COUNT, IGNORE, ERROR and
                        CONDITION
  --exec-remove
  --exec-link
  --include INCLUDE
  --exclude EXCLUDE
  --dir-include DIR_INCLUDE
  --dir-exclude DIR_EXCLUDE
  --dir-hidden
  -r, --recursive
  -g SIZE, --group-size SIZE
                        Minimum number of files in each group
  --basic-formatting
  --max-depth MAX_DEPTH
  --empty-file          Allow comparision of empty files
  --follow-symbolic     Allow following of symbolic links for compare
  -v, --verbosity
```

## Brace Expansion
*groupby* supports execution of commands on grouped files.
To assist with this, brace expansion of the following syntax is observed:
```buildoutcfg
# filename
{}   -> /foo/bar/file.ogg
 
# Filename with extension removed
{.}  -> /foo/bar/file

# Basename of file
{/}  -> file.ogg

# Directory of file
{//} -> /foo/bar

# Basename of file with extension removed
{/.} -> file

# File extension
{..} -> .ogg

# Filter output
{fn} -> output
```
With the exceptions of `{..}` and `{fn}`, this brace expansion is a similar syntax to [GNU Parallel](https://www.gnu.org/software/parallel/)

## Filters
*groupby* supports three kinds of filters
* builtin
* shell
* regex

Filters are completed in order, left to right as specified on each file discovered.
### Builtin Filters
*groupby* comes with several builtin filters including
* **md5**:  complete full md5 checksum
* **sha256**: complete full sha256 checksum
* **partial_md5**: md5 checksum of the first 12mb of a file
* **modified**: returns the modified date
* **accessed**: returns the accessed date
* **size**: returns the size in bytes
* **filename**: returns the filename
* **file**: returns the byte data

### Shell Filters
Shell filters, invoked with `-s`/`--filter-shell` require the use of brace expansion to know which file to act on.
For example, ```du -b {}``` will translate to ```du -b foobar.mkv```
Be aware of the output of shell commands. They often include the relative path and filename
in the output. *Output should be sanitized to only include the output of the command* through
tools such as cut or grep. For example
```buildoutcfg
du -b {} -> du -b foobar.mkv -> 476027 foobar.mkv
du -b {} -> du -b foobar.mkv | cut -f1 -> 476027
grep -oE '[0-9]+' {} -> grep -oE '[0-9]+' foobar.mkv -> 476027
```
See Brace Expansion for more information

### Regular Expression Filters (regex)
[Python based regular expressions](https://docs.python.org/3/library/re.html) 
may be invoked with `-E`/`--filter-regex`

Filenames often carry unique information about a file, such as
* resolution for videos
* bit-rate for audio
* versions of software

This information can be used to group the files.

```buildoutcfg
# foo/foo2_1080p.mkv
# foo/bar_720p.mkv
# foo/foo4_720p.mkv
# foo/foo6_480p.mkv

groupby --filter-regex '\d{3,4}p' foo/
# '\d{3,4}p' == Match 3 or 4 digits and then a character of 'p'
# Output
-> foo/foo6_480p.mkv
->
-> foo/foo4_720p.mkv
->     foo/bar_720p.mkv
->
-> foo/foo2_1080p.mkv
```
The regex match may also be used as notation for custom shell commmands

```buildoutcfg
groupby --filter-regex '\d+p' foo -x "mkdir -p {f1}/{/}"
# Commands executed
-> mkdir -p 480p/foo6_480p.mkv
-> mkdir -p 720p/foo4_720p.mkv
-> mkdir -p 720p/bar_720p.mkv
-> mkdir -p 1080p/foo2_1080p.mkv
```

## Group Execution
The results are grouped by their filters and can be acted on.
Only the last action specified will be used.
There are 2 types of group execution
* **builtin**: Executes the builtin on the grouped files
* **shell**: Executes the shell command on each grouped file

### Builtin
*groupby* has 3 built in action on grouped files
* **Link**: for each group, hardlink the first file to all the others in the group
* **Remove**: for each group, remove all but the first file
* **Merge**: Merge directories into the merge directory

#### Link
For each group, the first file is used as the source. The other files in the group
are removed. Then a hard link from source -> removed files location occurs.
This is useful for minimzing disk space usage when the files are the same, and won't
be changed. For example, with RAW image formats where the editing is completed by a configuration file

#### Remove
For each group, the first file is kept while additional files are removed.

#### Merge
Take all directories and merge into the given directory. For example,

`groupby --exec-merge testdir foo1 foo2`
will merge *foo1* and *foo2* into *testdir*.

The testdir structure is generated by filter output.
For example:

-f size with output of 5 3 10 will create 3 directories of testdir/5 testdir/3 testdir/10
and place the files with disk size of 5 3 and 10 into the respective directory.
In other words, `merge_directory/output_of_fn`
Each additional filter will create a new subdirectory.


Merge also has 4 different methods for handling existing file conflicts.
If unspecified, defaults to COUNT
* COUNT
* IGNORE
* ERROR
* CONDITION

##### Count
Syntax: `--exec-merge testdir:COUNT`

Add a increment count. `foo.mp4` -> `foo_0001.mp4`
##### Ignore
Syntax: `--exec-merge testdir:IGNORE`

Ignore existing files
##### Error
Syntax: `--exec-merge testdir:ERROR`

Raise a error and kill the program

##### Condition
Syntax: `--exec-merge testdir:CONDITION:OPTION`

Condition provides 4 options to allow precise control of overwriting
* NEWER
* OLDER
* LARGER
* SMALLER

Each test is completed target file against the already copied file.
The result is only the CONDITION of files are copied over.
For example,
```
groupby -f size --exec-merge testdir:CONDITION:SMALLER
```
Will result in only the smaller of conflicting files to exist
### Shell
When using `-x`/`--exec-shell`, an additional brace expansion is available under the notation of 
`{fn}`, representing the output of that filter for that group.

```buildoutcfg
# Move all files with the same size into their own directory
$ groupby -r -f size -x "mkdir -p {f1}; mv {} {f1}/{/}
# Commands executed
 ->  mkdir -p 122254
 ->  mv /foo/bar/file.ogg 122254/file.ogg

# Group all pictures into year and month
groupby.py -t2 -r \                             
    -s "exiftool -p '\$DateTimeOriginal' {} | cut -d\: -f1" \                   
    -s "exiftool -p '\$DateTimeOriginal' {} | cut -d\: -f2" \                   
    -x "echo mkdir -p {f1}/{f2}; echo mv {} {f1}/{f2}/{/}"  \                   
    foo/bar
# Commands executed
 -> mkdir -p 2015/04
 -> mv foo/bar/image1.png 2015/04/image1.png
...
```


