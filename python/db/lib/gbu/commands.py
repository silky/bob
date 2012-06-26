#!/usr/bin/env python
# vim: set fileencoding=utf-8 :
# @author: Manuel Guenther <Manuel.Guenther@idiap.ch> 
# @date:   Fri May 11 17:20:46 CEST 2012
#
# Copyright (C) 2011-2012 Idiap Research Institute, Martigny, Switzerland
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""Commands this database can respond to.
"""

import os
import sys
import tempfile, shutil


def dumplist(args):
  """Dumps lists of files based on your criteria"""

  from .query import Database
  db = Database()

  r = db.files(
      directory=args.directory,
      extension=args.extension,
      groups=args.groups,
      subworld=args.subworld,
      protocol=args.protocol,
      purposes=args.purposes)

  output = sys.stdout
  if args.selftest:
    from ..utils import null
    output = null()

  for id, f in r.items():
    output.write('%s\n' % (f,))


def checkfiles(args):
  """Checks existence of files based on your criteria"""

  from .query import Database
  db = Database()

  r = db.files(
      directory=args.directory,
      extension=args.extension,
      groups=args.groups,
      subworld=args.subworld,
      protocol=args.protocol,
      purposes=args.purposes)

  # go through all files, check if they are available on the filesystem
  good = {}
  bad = {}
  for id, f in r.items():
    if os.path.exists(f): good[id] = f
    else: bad[id] = f

  # report
  output = sys.stdout
  if args.selftest:
    from ..utils import null
    output = null()

  if bad:
    for id, f in bad.items():
      output.write('Cannot find file "%s"\n' % (f,))
    output.write('%d files (out of %d) were not found at "%s"\n' % \
        (len(bad), len(r), args.directory))


def copy_image_files(args):
  """This function scans the given input directory for the images
  required by this database and creates a new directory with the
  required sub-directory structure, by copying or linking the images"""
  
  if os.path.exists(args.new_image_directory):
    print "Directory", args.new_image_directory, "already exists, please choose another one."
    return
  # collect the files in the given directory
  from .create import collect_files
  print "Collecting image files from directory", args.original_image_directory
  filelist, dirlist = collect_files(args.original_image_directory, args.original_image_extension, args.sub_directory)

  print "Done. Found", len(filelist), "image files."
  # get the files of the database
  from .query import Database
  db = Database()
  db_files = db.files(extension = '.jpg')
  
  # create a temporary structure for faster access
  temp_dict = {}
  for file in db_files.itervalues():
    temp_dict[os.path.splitext(os.path.basename(file))[0]] = file

  command = os.symlink if args.soft_link else shutil.copy
  print "Copying (or linking) files to directory", args.new_image_directory
  # now, iterate through the detected files
  for index in range(len(filelist)):
    file_wo_extension = os.path.splitext(filelist[index])[0]
    if file_wo_extension in temp_dict:
      # get the files
      old_file = os.path.join(args.original_image_directory, dirlist[index], filelist[index])
      new_file = os.path.join(args.new_image_directory, temp_dict[file_wo_extension])
      new_dir = os.path.dirname(new_file)
      if not os.path.exists(new_dir):
        os.makedirs(new_dir)
      
      # copy or link
      assert not os.path.exists(new_file)
      command(old_file, new_file)


def create_eye_files(args):
  """Creates the eye position files for the GBU database 
  (using the eye positions stored in the database), 
  so that GBU shares the same structure as other databases."""  

  # report
  output = sys.stdout
  if args.selftest:
    from ..utils import null
    output = null()
    args.directory = tempfile.mkdtemp(prefix='bob_db_gbu_')
  
  from .query import Database
  db = Database()
  
  # retrieve all files
  objects = db.objects(directory=args.directory, extension=args.extension)
  for object in objects.itervalues():
    filename = object[0]
    if not os.path.exists(os.path.dirname(filename)):
      os.makedirs(os.path.dirname(filename))
    eyes = object[2]
    f = open(filename, 'w')
    # write eyes in the common order: left eye, right eye
    f.writelines(str(eyes[2]) + ' ' + str(eyes[3]) + ' ' + str(eyes[0]) + ' ' + str(eyes[1]) + '\n')
    f.close()
    
  
  if args.selftest:
    # check that all files really exist
    args.selftest = False
    args.groups = None
    args.subworld = None
    args.protocol = None
    args.purposes = None
    checkfiles(args)
    shutil.rmtree(args.directory)


def add_commands(parser):
  """Adds my subset of options and arguments to the top-level parser. For
  details on syntax, please consult:

  http://docs.python.org/dev/library/argparse.html

  The strategy assumed here is that each command will have its own set of
  options that are relevant to that command. So, we just scan such commands and
  attach the options from those.
  """
  
  from . import dbname
  from ..utils import location, standard_commands
  from . import __doc__ as dbdoc
  from argparse import RawDescriptionHelpFormatter, SUPPRESS

  # creates a top-level parser for this database
  myname = dbname()
  top_level = parser.add_parser(myname,
      formatter_class=RawDescriptionHelpFormatter,
      help="GBU database", description=dbdoc)
  top_level.set_defaults(dbname=myname)
  top_level.set_defaults(location=location(myname))

  # declare it has subparsers for each of the supported commands
  subparsers = top_level.add_subparsers(title="subcommands")

  # attach standard commands
  standard_commands(subparsers)

  # get the "create" action from a submodule
  from .create import add_command as create_command
  create_command(subparsers)

  # get the "dumplist" action from a submodule
  dump_list_parser = subparsers.add_parser('dumplist', help=dumplist.__doc__)

  dump_list_parser.add_argument('-d', '--directory', help="if given, this path will be prepended to every entry returned (defaults to '%(default)s')")
  dump_list_parser.add_argument('-e', '--extension', help="if given, this extension will be appended to every entry returned (defaults to '%(default)s')")
  dump_list_parser.add_argument('-g', '--groups', help="if given, this value will limit the output files to those belonging to a particular group. (defaults to '%(default)s')", choices=('world', 'dev', ''))
  dump_list_parser.add_argument('-s', '--subworld', help="if given, limits the dump to a particular subset of the data that corresponds to the given protocol (defaults to '%(default)s')", choices=('x1', 'x2', 'x4', 'x8', ''))
  dump_list_parser.add_argument('-p', '--protocol', help="if given, limits the dump to a particular subset of the data that corresponds to the given protocol (defaults to '%(default)s')", choices=('Good', 'Bad', 'Ugly', ''))
  dump_list_parser.add_argument('-u', '--purposes', help="if given, this value will limit the output files to those designed for the given purposes. (defaults to '%(default)s')", choices=('enrol', 'probe', ''))
  dump_list_parser.add_argument('--self-test', dest="selftest", action='store_true', help=SUPPRESS)

  dump_list_parser.set_defaults(func=dumplist) #action

  # get the "checkfiles" action from a submodule
  check_files_parser = subparsers.add_parser('checkfiles', help=checkfiles.__doc__)

  check_files_parser.add_argument('-d', '--directory', help="if given, this path will be prepended to every entry returned (defaults to '%(default)s')")
  check_files_parser.add_argument('-e', '--extension', help="if given, this extension will be appended to every entry returned (defaults to '%(default)s')")
  check_files_parser.add_argument('-g', '--groups', help="if given, this value will limit the output files to those belonging to a particular group. (defaults to '%(default)s')", choices=('world', 'dev', ''))
  check_files_parser.add_argument('-s', '--subworld', help="if given, limits the dump to a particular subset of the data that corresponds to the given protocol (defaults to '%(default)s')", choices=('x1', 'x2', 'x4', 'x8', ''))
  check_files_parser.add_argument('-p', '--protocol', help="if given, limits the dump to a particular subset of the data that corresponds to the given protocol (defaults to '%(default)s')", choices=('Good', 'Bad', 'Ugly', ''))
  check_files_parser.add_argument('-u', '--purposes', help="if given, this value will limit the output files to those designed for the given purposes. (defaults to '%(default)s')", choices=('enrol', 'probe', ''))
  check_files_parser.add_argument('--self-test', dest="selftest", action='store_true', help=SUPPRESS)

  check_files_parser.set_defaults(func=checkfiles) #action

  # get the "copy-image-files" action from a submodule
  copy_image_files_parser = subparsers.add_parser('copy-image-files', help=copy_image_files.__doc__)

  copy_image_files_parser.add_argument('-d', '--original-image-directory', metavar='DIR', required=True, help="Specify the image directory containing the MBGC-V1 images.")
  copy_image_files_parser.add_argument('-e', '--original-image-extension', metavar='EXT', default = '.jpg', help="The extension of the images in the database (defaults to '%(default)s')")
  copy_image_files_parser.add_argument('-n', '--new-image-directory', metavar='DIR', required=True, help="Specify the image directory where the images should be copied to.")
  copy_image_files_parser.add_argument('-s', '--sub-directory', metavar='DIR', help="To speed up the search process you might define a sub-directory that is scanned, e.g., 'Original'.")
  copy_image_files_parser.add_argument('-l', '--soft-link', action='store_true', help="If selected, the images will be linked rather than copied.")

  copy_image_files_parser.set_defaults(func=copy_image_files) #action

  # get the "create-eye-files" action from a submodule
  create_eye_files_parser = subparsers.add_parser('create-eye-files', help=create_eye_files.__doc__)

  create_eye_files_parser.add_argument('-d', '--directory', required=True, help="The eye position files will be stored in this directory")
  create_eye_files_parser.add_argument('-e', '--extension', default = '.pos', help="if given, this extension will be appended to every entry returned (defaults to '%(default)s')")
  create_eye_files_parser.add_argument('--self-test', dest="selftest", action='store_true', help=SUPPRESS)

  create_eye_files_parser.set_defaults(func=create_eye_files) #action