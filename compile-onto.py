from git import Repo
from shutil import copytree, rmtree, move, copyfile
from natsort import natsorted
import subprocess
from pathlib import Path
from glob import glob
from os.path import basename
from os import chdir, remove, listdir
from rdflib import *
from rdflib.namespace import OWL, VANN, DCTERMS, SDO
import os
import shutil
from py_markdown_table.markdown_table import markdown_table

def write_string_to_file(file_path, content):
    try:
        with open(file_path, 'w') as file:
            file.write(content)
        print(f"String written to {file_path} successfully.")
    except Exception as e:
        print(f"Error writing to {file_path}: {str(e)}")

def move_files(source_dir, destination_dir):
    """
    Move all files and directories from the source directory to the destination directory.

    Args:
        source_dir (str): The path to the source directory.
        destination_dir (str): The path to the destination directory.
    """
    for item in os.listdir(source_dir):
        shutil.move(os.path.join(source_dir, item), destination_dir)

def create_docs(onto_name : str, ontology_path : str, out_path : str, last_tag):
    print(f"Calling Widoco now! with {onto_name}, {ontology_path}, {out_path}, {last_tag}", flush=True)
    subprocess.run(f"java -jar /usr/local/widoco/widoco.jar -ontFile {ontology_path} -import {ontology_path} -outFolder {out_path} -rewriteAll -getOntologyMetadata -lang de-en -saveConfig out/config -webVowl -noPlaceHolderText -uniteSections", shell=True)
    if last_tag is not None:
        move_files(f'{out_path}/doc', out_path)

def copy_files_to_out(in_paths, out_path):
    for f in in_paths:
        print(f"trying to move {f}")
        if (Path(f).is_file()):
            shutil.copy(f, out_path)
            print(f"Success!")


def get_lang_IRI_Table(ontology : Graph, lang):
    
    namespace, _ = get_ontology_entity(g)
    classes = [{'IRI': str(x[0]), 'Label': str(x[1])} for x in ontology.query(f"""
        SELECT ?s ?l
    WHERE {{
        ?s a ?type .
        FILTER (?type = owl:ObjectProperty || ?type = owl:DatatypeProperty || ?type = rdf:Property || ?owl = owl:Class ) .
        ?s rdfs:label ?l
        FILTER (STRSTARTS(STR(?s), "{namespace}"))
      }}
        """) if x[1].language == lang]
    print(len(classes))
    classes.sort(key= lambda c: c['IRI'])
    return markdown_table(classes).set_params(row_sep = 'markdown', quote = False).get_markdown()

def rewrite_ontology_metadata(out_path, ontology : Graph, repo, curr_tag, last_tag):
    g = ontology
    namespace, ontology_entity = get_ontology_entity(g)
    
    commit_date = repo.head.commit.committed_datetime
    commit_date_str = f'{commit_date.year}-{commit_date.month}-{commit_date.day}'
    creator = str(next(g.triples((ontology_entity, DCTERMS.creator, None)))[2])
    title = str(next(g.triples((ontology_entity, DCTERMS.title, None)))[2])
    
    version = curr_tag[1:]
    prev_version = last_tag[1:] if last_tag is not None else None
    

    # Modified Date
    g.remove((ontology_entity, DCTERMS.modified, None))
    g.add((ontology_entity, DCTERMS.modified, Literal(commit_date_str)))

    # Versioned IRI
    g.remove((ontology_entity, OWL.versionIRI, None))
    g.add((ontology_entity, OWL.versionIRI, URIRef(f"{namespace[:-1]}/{version}/")))

    # Namespace Prefix (ontology abbreviation)
    g.remove((ontology_entity, VANN.preferredNamespacePrefix, None))
    g.add((ontology_entity, VANN.preferredNamespacePrefix, Literal(onto_name)))

    # Ontology Description; mostly misused by us to display the diagram and link to the IRI table (and maybe in the future to the Competency Question Results)
    g.remove((ontology_entity, DCTERMS.description, None))
    g.add((ontology_entity, DCTERMS.description, Literal(f'![Diagram]({onto_name}_diagram.svg)\n\n [IRI-Map](de-iri-table.md)', 'de')))
    g.add((ontology_entity, DCTERMS.description, Literal(f'![Diagram]({onto_name}_diagram.svg)\n\n [IRI-Map](en-iri-table.md)', 'en')))

    # Namespace URI (link to the ontology)
    g.remove((ontology_entity, VANN.preferredNamespaceUri, None))
    g.add((ontology_entity, VANN.preferredNamespaceUri, Literal(namespace)))

    # Prior Version (IRI to previous ontology version)
    g.remove((ontology_entity, OWL.priorVersion, None))
    if prev_version is not None:
        g.add((ontology_entity, OWL.priorVersion, URIRef(f"{namespace[:-1]}/{prev_version}/")))
    
    # Version Info (eg '1.0')
    g.remove((ontology_entity, OWL.versionInfo, None))
    g.add((ontology_entity, OWL.versionInfo, Literal(version)))

    # Citation info (for some reason, widoco does not support langstrings here)
    g.remove((ontology_entity, SDO.citation, None))
    g.add((ontology_entity, SDO.citation, Literal(f"{creator}, {title} v{version}")))

    g.serialize(out_path, format="ttl")

def get_ontology_entity(g : Graph):
    namespace = next(n for n in g.namespaces() if n[0] == '')
    ontology_entity = namespace[1]
    namespace = str(ontology_entity)
    return namespace,ontology_entity

root = "/github/workspace"
chdir(root)

rmtree("./out", ignore_errors=True)
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

    
    in_path = f'copy/ontology/{onto_name}.ttl'
    g = Graph()
    g.parse(in_path)

    write_string_to_file('./en-iri-table.md', get_lang_IRI_Table(g, 'en'))
    write_string_to_file('./de-iri-table.md', get_lang_IRI_Table(g, 'de'))
    prepared_ontology_path = "prepared_ontology.ttl"
    rewrite_ontology_metadata(prepared_ontology_path, g, repo, tag.name, prev_tag.name if prev_tag is not None else None)
    create_docs(onto_name, prepared_ontology_path, out_path, prev_tag)

    copy_files_to_out([f"copy/ontology/{onto_name}_diagram.svg", "/usr/local/widoco/index.html", './en-iri-table.md', './de-iri-table.md'], out_path)

    remove(prepared_ontology_path)


    if tag == tags[-1]:
        copytree(out_path, "out/", dirs_exist_ok=True)
    prev_tag = tag
