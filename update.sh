#!/bin/bash

git fetch origin
LOCALUPDATES=$(git log origin/update..HEAD --oneline)

if ! [ -z "$LOCALUPDATES" ]
then
    exit 3
fi
INCOMINGUPDATES=$(git log HEAD..origin/update --oneline)
if [ -z "$INCOMINGUPDATES" ]
then
    exit 4
fi

git pull
exit 0