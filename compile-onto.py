from git import Repo
from shutil import copytree, rmtree, move
from natsort import natsorted
import subprocess
from pathlib import Path
from glob import glob
from os.path import basename


onto_files = [basename(f) for f in glob('/github/workspace/ontology/*.ttl')]
onto_files.sort(key=len)
onto_name = onto_files[0][:-4]


rmtree("./copy", ignore_errors=True)
copytree("/github/workspace", "./copy")

repo = Repo.init("./copy")
tags = natsorted([t for t in repo.tags if t.name.startswith('v')], key= lambda t: t.name)

for tag in tags:
    repo.git.checkout(tag)
    subprocess.run(f"java -jar /usr/local/widoco/widoco.jar -ontFile copy/ontology/{onto_name}.ttl -import copy/ontology/{onto_name}.ttl -outFolder out/{tag.name[1:]} -rewriteAll -getOntologyMetadata -lang de-en -saveConfig out/config -webVowl -noPlaceHolderText -htaccess", shell=True)
    if tag == tags[-1]:
        copytree(f"out/{tag.name[1:]}", "out/", dirs_exist_ok=True)