from git import Repo
from shutil import copytree, rmtree
from natsort import natsorted
import subprocess
from pathlib import Path

rmtree("./copy", ignore_errors=True)
copytree(".", "./copy")
raise Exception(str(Path.cwd.absolute().as_posix()))

repo = Repo.init("./copy")
tags = natsorted(repo.tags, key= lambda t: t.name)

for tag in tags:
    repo.git.checkout(tag)
    subprocess.run(f"java -jar widoco.jar -ontFile copy/gerps-datafield.ttl -import copy/gerps-datafield.ttl -outFolder out/{tag.name[1:]} -rewriteAll -getOntologyMetadata -lang de-en -saveConfig out/config -webVowl -noPlaceHolderText", shell=True)
    