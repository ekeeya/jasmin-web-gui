FROM eclipse-temurin:17-jdk

LABEL maintainer="ekeeya@thothcode.tech"

WORKDIR /

COPY entrypoint.sh /entrypoint.sh
COPY smppsim.jar /smppsim.jar
COPY conf /conf
# Manifest Class-Path expects these beside the jar (java -jar resolves relative to jar dir)
COPY lib /lib

RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
