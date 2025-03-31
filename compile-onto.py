from git import Repo
from shutil import copytree, rmtree, move, copyfile
from natsort import natsorted
import subprocess
from pathlib import Path
from glob import glob
from os.path import basename
from os import chdir, remove
from rdflib import *
from rdflib.namespace import OWL, VANN, DCTERMS, SDO

def create_docs(onto_name : str, ontology_path : str, out_path : str):
    subprocess.run(f"java -jar /usr/local/widoco/widoco.jar -ontFile {ontology_path} -import {ontology_path} -outFolder {out_path} -rewriteAll -getOntologyMetadata -lang de-en -saveConfig out/config -webVowl -noPlaceHolderText -uniteSections", shell=True)

    diagram_path = f"copy/ontology/{onto_name}_diagram.svg"
    copyfile("/usr/local/widoco/default_index.html", f"{out_path}/index.html")
    if Path(diagram_path).is_file():
        copyfile(diagram_path, f"{out_path}/{onto_name}_diagram.svg")

def rewrite_ontology_metadata(prepared_ontology_path, onto_name, repo, curr_tag, last_tag):
    g = Graph()
    g.parse(f'copy/ontology/{onto_name}.ttl')
    default_namespace = next(n for n in g.namespaces() if n[0] == '')
    ontology_entity = default_namespace[1]

    g.remove((ontology_entity, OWL.versionIRI, None))
    g.remove((ontology_entity, DCTERMS.modified, None))
    g.remove((ontology_entity, VANN.preferredNamespacePrefix, None))
    g.remove((ontology_entity, DCTERMS.description, None))
    g.remove((ontology_entity, VANN.preferredNamespaceUri, None))
    g.remove((ontology_entity, OWL.priorVersion, None))
    g.remove((ontology_entity, OWL.versionInfo, None))
    g.remove((ontology_entity, SDO.citation, None))

    version = curr_tag[1:]
    prev_version = last_tag[1:] if last_tag is not None else None
    namespace = str(ontology_entity)


    commit_date = repo.head.commit.committed_datetime
    commit_date_str = f'{commit_date.year}-{commit_date.month}-{commit_date.day}'
    creator = str(next(g.triples((ontology_entity, DCTERMS.creator, None)))[2])
    title = str(next(g.triples((ontology_entity, DCTERMS.title, None)))[2])


    g.add((ontology_entity, DCTERMS.modified, Literal(commit_date_str)))
    g.add((ontology_entity, VANN.preferredNamespacePrefix, Literal(onto_name)))
    g.add((ontology_entity, VANN.preferredNamespaceUri, Literal(namespace)))
    g.add((ontology_entity, OWL.versionInfo, Literal(version)))
    g.add((ontology_entity, DCTERMS.description, Literal(f'![Diagram]({onto_name}_diagram.svg)')))
    if prev_version is not None:
        g.add((ontology_entity, OWL.priorVersion, Literal(f"{namespace}/{prev_version}/")))

    g.add((ontology_entity, OWL.versionIRI, Literal(f"{namespace}/{version}/")))
    g.add((ontology_entity, SDO.citation, Literal(f"Cite this vocabulary as: {creator}, {title} v{version}", lang="en")))
    g.add((ontology_entity, SDO.citation, Literal(f"Zitieren sie dieses Vokabular als: {creator}, {title} v{version}", lang="de")))

    g.serialize(prepared_ontology_path, format="ttl")


root = "/github/workspace"
chdir(root)

rmtree("./copy", ignore_errors=True)
copytree(root, "./copy")

repo = Repo.init("./copy")
tags = natsorted([t for t in repo.tags if t.name.startswith('v')], key= lambda t: t.name)

prev_tag = None
for tag in tags:
    repo.git.checkout(tag)

    onto_files = [basename(f) for f in glob('copy/ontology/*.ttl')]
    onto_files.sort(key=len)
    onto_name = onto_files[0][:-4]
    
    out_path = f"out/{tag.name[1:]}"

    prepared_ontology_path = "prepared_ontology.ttl"
    rewrite_ontology_metadata(prepared_ontology_path, onto_name, repo, tag.name, prev_tag.name if prev_tag is not None else None)
    create_docs(onto_name, prepared_ontology_path, out_path)


    remove(prepared_ontology_path)


    if tag == tags[-1]:
        copytree(out_path, "out/", dirs_exist_ok=True)
    prev_tag = tag
