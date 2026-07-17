FROM eclipse-temurin:17-jdk

LABEL maintainer="ekeeya@thothcode.tech"

WORKDIR /

COPY entrypoint.sh /entrypoint.sh
COPY smppsim.jar /smppsim.jar
COPY conf /conf
# Manifest Class-Path expects these beside the jar (java -jar resolves relative to jar dir)
COPY lib /lib
# Web UI for MO injection (inject_mo.htm) — DOCROOT=www in smppsim.props
COPY www /www

RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
