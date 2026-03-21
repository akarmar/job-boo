FROM ubuntu:24.04

RUN apt-get update && apt-get install -y --no-install-recommends \
    bash git coreutils less tree \
    && rm -rf /var/lib/apt/lists/*

# Non-root user (security best practice)
RUN useradd -m -s /bin/bash demouser

COPY . /opt/job-boo
COPY demo/demo.sh /usr/local/bin/demo
RUN chmod +x /usr/local/bin/demo

USER demouser
WORKDIR /opt/job-boo

ENTRYPOINT ["demo"]
