# Image chấm bài: Ubuntu 22.04 giống môi trường của môn học.
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update \
 && apt-get install -y --no-install-recommends gcc libc6-dev make binutils python3 python3-yaml \
 && rm -rf /var/lib/apt/lists/*

COPY runner/ /runner/
# Runner chạy bằng root (chỉ giữ vài capability, xem judge.py); bài nộp chạy bằng user `sandbox` (uid 1000).
# /judge (0700, chỉ root vào được) chứa đề, test, đáp án và bài nộp gốc — bài nộp không đọc được, cũng không
# mở được stdout của runner (/proc/<pid>/fd của root) để giả mạo kết quả.
RUN useradd -m -u 1000 sandbox && mkdir -m 0700 /judge
WORKDIR /tmp
ENTRYPOINT ["python3", "/runner/run.py"]
