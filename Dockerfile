FROM ghcr.io/dgarijo/widoco:v1.4.25


USER root
run apt-get update
COPY requirements.txt .
COPY compile-onto.py .
RUN apt install -y python3 python3-pip git
RUN pip install -r requirements.txt
USER widoco



ENTRYPOINT "python3" "/usr/local/widoco/compile-onto.py"
CMD ""

