# Pin Python and the matching Chrome for Testing browser/driver release.
FROM python:3.14.8-slim

USER root
ARG VCS_REF=local
ARG CFT_VERSION=154.0.8037.92
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_REVISION=${VCS_REF} \
    HOME=/home/app \
    XDG_RUNTIME_DIR=/tmp/runtime-app \
    SE_OFFLINE=true \
    SE_CHROMEDRIVER=/usr/bin/chromedriver

# Install desktop and Chrome runtime libraries explicitly: slim has no GUI stack.
# Keep download tools temporary and browser archives out of the final layer.
RUN test "$(dpkg --print-architecture)" = amd64 \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates fonts-liberation \
        libasound2t64 libatk-bridge2.0-0 libatk1.0-0 libatspi2.0-0 \
        libcairo2 libcups2t64 libdbus-1-3 libdrm2 libgbm1 \
        libglib2.0-0t64 libnspr4 libnss3 libpango-1.0-0 \
        libtk8.6 libx11-6 libxcb1 libxcomposite1 libxdamage1 \
        libxext6 libxfixes3 libxkbcommon0 libxrandr2 \
        novnc openbox scrot xauth x11vnc xvfb \
    && apt-get install -y --no-install-recommends curl unzip \
    && mkdir -p /opt/posting-novnc \
    && cp -aL /usr/share/novnc/core /usr/share/novnc/vendor /opt/posting-novnc/ \
    && mkdir -p /opt/chrome-for-testing \
    && curl -fSsL --retry 3 -o /tmp/chrome.zip "https://storage.googleapis.com/chrome-for-testing-public/${CFT_VERSION}/linux64/chrome-linux64.zip" \
    && curl -fSsL --retry 3 -o /tmp/chromedriver.zip "https://storage.googleapis.com/chrome-for-testing-public/${CFT_VERSION}/linux64/chromedriver-linux64.zip" \
    && unzip -q /tmp/chrome.zip -d /opt/chrome-for-testing \
    && unzip -q /tmp/chromedriver.zip -d /opt/chrome-for-testing \
    && chmod 755 /opt/chrome-for-testing/chrome-linux64/chrome /opt/chrome-for-testing/chromedriver-linux64/chromedriver \
    && ln -sf /opt/chrome-for-testing/chrome-linux64/chrome /usr/bin/chromium \
    && ln -sf /opt/chrome-for-testing/chromedriver-linux64/chromedriver /usr/bin/chromedriver \
    && ldd /usr/bin/chromium > /tmp/chrome-libraries \
    && ldd /usr/bin/chromedriver > /tmp/driver-libraries \
    && cat /tmp/chrome-libraries /tmp/driver-libraries \
    && ! grep -q 'not found' /tmp/chrome-libraries /tmp/driver-libraries \
    && test "$(chromium --version | awk '{print $NF}')" = "$CFT_VERSION" \
    && test "$(chromedriver --version | cut -d ' ' -f 2)" = "$CFT_VERSION" \
    && rm -f /tmp/chrome.zip /tmp/chromedriver.zip /tmp/chrome-libraries /tmp/driver-libraries \
    && apt-get purge -y --auto-remove curl unzip \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /srv/app
COPY requirements.lock ./
RUN pip install --no-cache-dir -r requirements.lock \
    && python -c "from pathlib import Path; from seleniumbase import Driver, drivers; import tkinter; slot = Path(drivers.__file__).parent / 'chromedriver'; slot.unlink(missing_ok=True); slot.symlink_to('/usr/bin/chromedriver'); assert slot.samefile('/usr/bin/chromedriver')"
COPY app ./app

RUN groupadd --system app && useradd --system --gid app --create-home app \
    && mkdir -p /data "$XDG_RUNTIME_DIR" \
    && touch "$HOME/.Xauthority" \
    && chown -R app:app /data "$HOME" "$XDG_RUNTIME_DIR"
USER app

EXPOSE 8000
ENTRYPOINT []
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]
