FROM ghcr.io/dgarijo/widoco:v1.4.25


USER root
RUN apt-get update
RUN apt install -y python3 python3-pip git
RUN git config --global core.autocrlf input
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY compile-onto.py .



ENTRYPOINT ["python3", "/usr/local/widoco/compile-onto.py"]
CMD [""]

