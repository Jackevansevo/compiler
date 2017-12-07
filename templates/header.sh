#!/usr/bin/env bash
tempfile=$(mktemp)
tail $0 -n +7 > $tempfile
spim load $tempfile | tail -n +6
rm -f $tempfile
exit
