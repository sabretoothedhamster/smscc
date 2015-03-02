#!/bin/bash
#
# Control 4-channel DS2408-based module from http://radioseti.ru/index.php?route=product/product&path=62_67&product_id=140
# $Id$
#
# usage: <path> <channel> [<val>]
# <arg> - owfs path to to particulaer DS2408 device (like /mnt/1wire/29.090B0E000000)
#
DEV=$1
CHN=$2
VAL=$3
#
# DS2408 read/write channels mapping
# channel to owfs 'sensed' I/O bit
RCH[1]=1
RCH[2]=6
RCH[3]=7
RCH[4]=0
# channel to owfs 'PIO' I/O bit
WCH[1]=2
WCH[2]=3
WCH[3]=4
WCH[4]=5

function rdch() {
  local v=
  local i
  for i in {1..5}
  do
#    echo Reading channel $CHN / file sensed.${RCH[$CHN]}
    v=`cat $1/sensed.${RCH[$2]} 2>/dev/null` && break
  done
#  echo val=$v
  echo $v
}

if test -z "$VAL";
then
  rdch $DEV $CHN
#  echo result=$?
#  echo $?
else
#  echo Writing channel $CHN with $VAL
  if [ "$VAL" = "0" ]; then
  	VAL="0"
  else
    VAL="1"
  fi
  v=$(rdch $DEV $CHN)
  if [ x$v = x$VAL ]; then
#    echo Already set $VAL
    echo Ok\($VAL\)
    exit 0
  fi
  for i in {1..3}
  do
      for k in {1..5}
      do
    #    echo Update channel $CHN / file PIO.${WCH[$CHN]} with 0
        echo 0 > $DEV/PIO.${WCH[$CHN]} 2>/dev/null && break;
      done
      for k in {1..5}
      do
    #    echo Update  channel $CHN / file PIO.${WCH[$CHN]} with 1
        echo 1 > $DEV/PIO.${WCH[$CHN]} 2>/dev/null && break;
      done
      v=$(rdch $DEV $CHN)
      if [ x$v = x$VAL ]; then
    #    echo Set Ok to $VAL
        echo Done\($VAL\)
        exit 0
      fi
  done
  echo Err\($v\)
  exit 1

fi
