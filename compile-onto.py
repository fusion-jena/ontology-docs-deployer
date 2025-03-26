from git import Repo
from shutil import copytree, rmtree, move, copyfile
from natsort import natsorted
import subprocess
from pathlib import Path
from glob import glob
from os.path import basename
from os import chdir

def create_docs(onto_name : str, out_path : str):
    subprocess.run(f"java -jar /usr/local/widoco/widoco.jar -ontFile copy/ontology/{onto_name}.ttl -import copy/ontology/{onto_name}.ttl -outFolder {out_path} -rewriteAll -getOntologyMetadata -lang de-en -saveConfig out/config -webVowl -noPlaceHolderText -uniteSections", shell=True)
    diagram_path = f"copy/ontology/{onto_name}_diagram.svg"
    copyfile("/usr/local/widoco/default_index.html", f"{out_path}/index.html")
    if Path(diagram_path).is_file():
        copyfile(diagram_path, f"out/{onto_name}_diagram.svg")

root = "/github/workspace"
chdir(root)




rmtree("./copy", ignore_errors=True)
copytree(root, "./copy")

repo = Repo.init("./copy")
tags = natsorted([t for t in repo.tags if t.name.startswith('v')], key= lambda t: t.name)

for tag in tags:
    repo.git.checkout(tag)
    out_path = f"copy/{tag.name[1:]}"
    
    onto_files = [basename(f) for f in glob(root + 'copy/ontology/*.ttl')]
    onto_files.sort(key=len)
    onto_name = onto_files[0][:-4]
    
    create_docs(onto_name, out_path)
    if tag == tags[-1]:
        copytree(out_path, "out/", dirs_exist_ok=True)
