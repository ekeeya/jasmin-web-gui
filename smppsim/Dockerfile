FROM openjdk:17-slim as builder

LABEL maintainer="ekeeya@thothcode.tech"

# Copy entrypoint.sh into the container
COPY entrypoint.sh /entrypoint.sh

# Make entrypoint.sh executable
RUN chmod +x /entrypoint.sh

# Set the entrypoint
ENTRYPOINT ["/entrypoint.sh"]