FROM pengbai/docker-supermario:latest AS game

COPY jquery.min.js /usr/local/tomcat/webapps/ROOT/jquery.min.js
RUN sed -i 's|https://ajax.googleapis.com/ajax/libs/jquery/1.4.2/jquery.min.js|jquery.min.js|g' /usr/local/tomcat/webapps/ROOT/index.html
COPY telemetry.js /usr/local/tomcat/webapps/ROOT/telemetry.js
RUN sed -i 's|</body>|<script src="telemetry.js"></script>\n</body>|' /usr/local/tomcat/webapps/ROOT/index.html

FROM tomcat:9.0-jdk11-openjdk

RUN apt-get update && \
    apt-get install -y --no-install-recommends python3 python3-pip nginx procps && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt /opt/telemetry/requirements.txt
RUN pip3 install --no-cache-dir -r /opt/telemetry/requirements.txt --break-system-packages 2>/dev/null || \
    pip3 install --no-cache-dir -r /opt/telemetry/requirements.txt

RUN rm -rf /usr/local/tomcat/webapps/*
COPY --from=game /usr/local/tomcat/webapps/ROOT /usr/local/tomcat/webapps/ROOT

COPY telemetry_sidecar.py /opt/telemetry/telemetry_sidecar.py
COPY nginx.conf /etc/nginx/nginx.conf
COPY start.sh /opt/start.sh
RUN chmod +x /opt/start.sh

EXPOSE 8080

CMD ["/opt/start.sh"]
