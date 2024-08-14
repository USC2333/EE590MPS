#!/bin/bash

termux-wake-lock

while true; do
  ./upload_to_thingsboard.sh
  sleep 5  # in sec
done
