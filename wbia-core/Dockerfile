FROM python:3.10-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    python3-dev \
    libopencv-dev \
    cmake \
    git \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    "numpy>=1.24" \
    "opencv-contrib-python-headless>=4.8.0" \
    "pydantic>=2.0" \
    "wbia-pyflann>=4.0.4"

ARG PYHESAFF_REPO=https://github.com/WildMeOrg/wbia-tpl-pyhesaff.git
RUN git clone --depth 1 $PYHESAFF_REPO /tmp/wbia-tpl-pyhesaff && \
    cd /tmp/wbia-tpl-pyhesaff && \
    pip install --no-cache-dir -r requirements/build.txt && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir . && \
    rm -rf /tmp/wbia-tpl-pyhesaff

WORKDIR /app

COPY . /app/wbia-core
RUN pip install --no-cache-dir --no-deps -e /app/wbia-core

COPY tests/replay/testdata/fixtures /tmp/fixtures
COPY tests/replay/parity_test.py /app/parity_test.py

WORKDIR /app
CMD ["python", "parity_test.py"]
