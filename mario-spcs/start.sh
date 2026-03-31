#!/bin/bash
sed -i 's/port="8080"/port="8888"/' /usr/local/tomcat/conf/server.xml
nginx
python3 /opt/telemetry/telemetry_sidecar.py &
catalina.sh run
