FROM ghcr.io/dgarijo/widoco:master

USER root
RUN apt-get update \
    && apt-get -o Acquire::Retries=5 install -y --no-install-recommends \
       python3 python3-pip git \
    && rm -rf /var/lib/apt/lists/*

RUN git config --global core.autocrlf input
COPY index.html .
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY compile-onto.py .



ENTRYPOINT ["python3", "/usr/local/widoco/compile-onto.py"]
CMD [""]

