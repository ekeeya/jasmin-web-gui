FROM openjdk:17-slim as builder

LABEL maintainer="ekeeya@thothcode.tech"

# Copy entrypoint.sh into the container
COPY entrypoint.sh /entrypoint.sh

COPY smppsim.jar /smppsim.jar
COPY conf /conf

# Make entrypoint.sh executable
RUN chmod +x /entrypoint.sh

# Set the entrypoint
ENTRYPOINT ["/entrypoint.sh"]