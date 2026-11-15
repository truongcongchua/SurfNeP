# Image chấm bài: Ubuntu 22.04 giống môi trường của môn học.
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update \
 && apt-get install -y --no-install-recommends gcc libc6-dev make binutils python3 python3-yaml \
 && rm -rf /var/lib/apt/lists/*

COPY runner/ /runner/
RUN useradd -m -u 1000 judge
USER judge
WORKDIR /tmp
ENTRYPOINT ["python3", "/runner/run.py"]
