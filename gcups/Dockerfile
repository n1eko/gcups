FROM docker.io/library/ubuntu:24.04

LABEL org.opencontainers.image.source="https://github.com/n1eko/gcups" \
      org.opencontainers.image.description="Green Cell UPS app (GC UPS), headless, with its web UI on port 8080. The bundled app is proprietary Green Cell software."

# Single source of truth for the gcups version (CI reads it from here).
ARG GCUPS_VERSION=1.1.10
LABEL org.opencontainers.image.version="${GCUPS_VERSION}"
ENV GCUPS_HOME=/opt/gcups

# tini as PID 1, plus the shared libraries the Electron binary links against.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates tini wget \
        libasound2t64 libatk-bridge2.0-0t64 libcups2t64 libdrm2 libgbm1 libgtk-3-0t64 \
        libnss3 libxcomposite1 libxdamage1 libxkbcommon0 libxrandr2 \
    && rm -rf /var/lib/apt/lists/*

# Official installer, as documented by Green Cell. install.sh writes udev rules
# and reloads udev, which isn't running in a build container, so udevadm is
# stubbed for the duration of the install.
RUN cd "$(dirname "$GCUPS_HOME")" \
    && wget -qO gcups.tar.gz "https://gcups-static.greencell.global/linux/x86_64/gcups-${GCUPS_VERSION}.tar.gz" \
    && tar -xzf gcups.tar.gz \
    && rm gcups.tar.gz \
    && mv "gcups-${GCUPS_VERSION}" "$GCUPS_HOME" \
    && mkdir -p /etc/udev/rules.d \
    && printf '#!/bin/sh\nexit 0\n' > /usr/local/bin/udevadm && chmod +x /usr/local/bin/udevadm \
    && "$GCUPS_HOME/install.sh" \
    && rm /usr/local/bin/udevadm

# The app's service context hardcodes uid/gid 777 for its worker process and
# keeps its state under these fixed paths.
RUN groupadd -g 777 gcups \
    && useradd -u 777 -g gcups -M -d /var/lib/gcups -s /usr/sbin/nologin gcups \
    && install -d -o gcups -g gcups /var/lib/gcups /var/cache/gcups /var/log/gcups /run/gcups

COPY --chmod=755 entrypoint.sh /opt/gcups-container/entrypoint.sh
COPY --chmod=644 configure-api.js /opt/gcups-container/configure-api.js

ENV GCUPS_HTTP_PORT=8080 \
    GCUPS_PASSWORD=gcups123

EXPOSE 8080
VOLUME ["/var/lib/gcups"]

USER gcups
ENTRYPOINT ["/usr/bin/tini", "-g", "--", "/opt/gcups-container/entrypoint.sh"]
