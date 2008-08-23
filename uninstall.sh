#!/bin/bash

# Copyright 2008 Robby Workman <rworkman@slackware.com>, Northport, AL, USA
# Copyright 2008 Alan Hicks <alan@slackware.com>, Lizella, GA, USA
# All rights reserved.
#
# Redistribution and use of this script, with or without modification, is
# permitted provided that the following conditions are met:
#
# 1. Redistributions of this script must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#
# THIS SOFTWARE IS PROVIDED BY THE AUTHOR ''AS IS'' AND ANY EXPRESS OR IMPLIED
# WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO
# EVENT SHALL THE AUTHOR BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS;
# OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
# WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR
# OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF
# ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

CWD=$(pwd)

INSTALL_LOG=${INSTALL_LOG:-"$CWD/install.log"}
UNINSTALL_LOG=${UNINSTALL_LOG:-"$CWD/uninstall.log"}

DIR_LIST=$(mktemp)
FILE_LIST=$(mktemp)

trap "do_cleanup ; exit 0" EXIT;
trap "do_cleanup ; exit 1" SIGINT SIGTERM;

error_nolog() {
  echo "There does not appear to be an installation log present, most"
  echo "likely because you did not install Wicd from this directory."
  do_cleanup
  exit 1
}

do_success() {
  echo "You have successfully uninstalled Wicd."
  echo "Configuration files added after installation were NOT removed."
  exit 0
}
   
get_contents() {
  while read LINE ; do
    if [ -d "$LINE" ]; then
      # $LINE is a directory
      echo "$LINE" >> "$DIR_LIST"
    else 
      # $LINE is a file or symlink or the like
      echo "$LINE" >> "$FILE_LIST"
    fi
    # Now handle parent directories
    RECURSE=true
    while [ "$RECURSE" = "true" ]; do
      LINE="$(dirname $LINE)"
      if [ ! "$LINE" = "/" ]; then
        echo "$LINE" >> "$DIR_LIST"
      else
        RECURSE=false
      fi
    done
  done < $INSTALL_LOG
}

do_uninstall() {
  cat $FILE_LIST | xargs rm -f &> $UNINSTALL_LOG
  cat $DIR_LIST | sort -ur | xargs rmdir &> $UNINSTALL_LOG
}

do_cleanup() {
  rm -f $FILE_LIST $DIR_LIST 2>/dev/null
}

[ -e $INSTALL_LOG ] || error_nolog
get_contents
do_uninstall
do_cleanup
do_success

