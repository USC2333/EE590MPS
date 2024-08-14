#!/bin/bash

ACCESS_TOKEN="gqalO5BxuX2Pu7wPKHOy"
THINGSBOARD_URL="http://frontgate.tplinkdns.com:8080/api/v1/$ACCESS_TOKEN/telemetry"

location=$(./get_location.sh)

curl -v -X POST -d "$location" -H "Content-Type: application/json" $THINGSBOARD_URL
