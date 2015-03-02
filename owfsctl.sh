#!/bin/bash
#
# Control 1-wire connected device over owfs (with 5 retries on i/o error)
# $Id$
#
# usage: <path> [<val>]
# <arg> - full owfs path to to particulaer 1-wire device (like /mnt/1wire/3A.A63E07000000/PIO.A)
#
DEV=$1
VAL=$2
#
function rdch() {
  local v=
  local i
  for i in {1..5}
  do
#    echo Reading channel $CHN / file sensed.${RCH[$CHN]}
    v=`cat $1 2>/dev/null` && break
  done
#  echo val=$v
  echo $v
}

if test -z "$VAL";
then
  rdch $DEV
#  echo result=$?
#  echo $?
else
#  echo Writing channel $CHN with $VAL
  if [ "$VAL" = "0" ]; then
  	VAL="0"
  else
    VAL="1"
  fi
  v=$(rdch $DEV)
  if [ x$v = x$VAL ]; then
#    echo Already set $VAL
    echo Ok\($VAL\)
    exit 0
  fi
  for i in {1..3}
  do
      for k in {1..5}
      do
        echo $VAL > $DEV 2>/dev/null && break;
      done
      for k in {1..5}
      do
      v=$(rdch $DEV)
      if [ x$v = x$VAL ]; then
    #    echo Set Ok to $VAL
        echo Done\($VAL\)
        exit 0
      fi
  done
  echo Err\($v\)
  exit 1

fi
