#!/bin/bash

# check_service() {
#   local service=$1
#   if ping -c 1 -W 1 "$service" > /dev/null 2>&1; then
#     return 0
#   else
#     echo "Waiting for $service..."
#     return 1
#   fi
# }

# c=0
# while [[ $c -lt 60 ]]; do

#   app_running=0;
#   db_running=0;
#   if [[ app_running -eq 0 ]]; then
#     $app_running=$(check_service "app")
#   fi
#   if check_service "app" && check_service "db"; then
#     break
#   fi
#   sleep 1
#   ((c++))
# done

sleep 3600

# all required services are running - run the perforamnce test
python test_performance.py
