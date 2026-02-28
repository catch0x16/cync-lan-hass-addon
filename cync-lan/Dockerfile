ARG BUILD_FROM=baudneo/cync-lan:latest
FROM ${BUILD_FROM}

# Install jq for /data/options.json parsing (no bashio on non-HA-base image)
# Install fastapi + uvicorn for companion export server on port 23778
RUN apt-get update \
 && DEBIAN_FRONTEND=noninteractive apt-get install -yq --no-install-recommends jq \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/* \
 && pip install --no-cache-dir fastapi 'uvicorn[standard]'

COPY run.sh /run.sh
RUN chmod a+x /run.sh
COPY exporter.py /exporter.py

# Clear upstream entrypoint/cmd; run.sh is the sole entry point
ENTRYPOINT []
CMD ["/run.sh"]
