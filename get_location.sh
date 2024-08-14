#!/bin/bash

location=$(termux-location -p passive -r last)
latitude=$(echo $location | jq '.latitude')
longitude=$(echo $location | jq '.longitude')
altitude=$(echo $location | jq '.altitude')

echo "{
  \"latitude\": $latitude,
  \"longitude\": $longitude,
  \"altitude\": $altitude
}"
