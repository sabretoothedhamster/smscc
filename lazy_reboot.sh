#!/bin/bash
if test -z $1; then
	$0 1 &
	exit 0;
else
	echo Reboot countdown...
	sleep 30
	reboot -f
	echo reboot done
fi

