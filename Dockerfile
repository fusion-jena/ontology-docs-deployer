FROM ghcr.io/dgarijo/widoco:master

USER root
RUN apt-get update \
    && apt-get -o Acquire::Retries=5 install -y --no-install-recommends \
       python3 python3-pip python3-venv git \
    && rm -rf /var/lib/apt/lists/*

RUN git config --global core.autocrlf input
COPY index.html .
COPY requirements.txt .

RUN python3 -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir -r requirements.txt

COPY compile-onto.py .

ENTRYPOINT ["/opt/venv/bin/python", "/usr/local/widoco/compile-onto.py"]
CMD [""]