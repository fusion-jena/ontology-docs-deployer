from typing import List, Optional
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
import yaml
from rdflib.plugin import PluginException
import re

class CompetencyQuestion:
    def __init__(self, plain, query):
        self.plain = plain
        self.query = query

    def __repr__(self):
        return f"CompetencyQuestion(plain='{self.plain}', query='{self.query}')"

def create_competency_questions(questions):
    return [CompetencyQuestion(q['plain'], q['query']) for q in questions['competency-questions']]


def read_yaml_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            data = yaml.safe_load(file)
            return data
    except FileNotFoundError:
        print("File not found.")
        return None
    except yaml.YAMLError as e:
        print("Error parsing YAML file: ", e)
        return None

def write_string_to_file(file_path : str, content : str):
    try:
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(content)
        print(f"String written to {file_path} successfully.")
    except Exception as e:
        print(f"Error writing to {file_path}: {str(e)}")

def move_files(source_dir : str, destination_dir : str):
    """
    Move all files and directories from the source directory to the destination directory.

    Args:
        source_dir (str): The path to the source directory.
        destination_dir (str): The path to the destination directory.
    """
    for item in os.listdir(source_dir):
        shutil.move(os.path.join(source_dir, item), destination_dir)

def create_docs(onto_name : str, ontology_path : str, out_path : str, last_tag : str):
    print(f"Calling Widoco now! with {onto_name}, {ontology_path}, {out_path}, {last_tag}", flush=True)
    subprocess.run(f"java -jar /usr/local/widoco/widoco.jar -ontFile {ontology_path} -import {ontology_path} -outFolder {out_path} -rewriteAll -getOntologyMetadata -lang de-en -saveConfig out/config -webVowl -noPlaceHolderText -uniteSections", shell=True)
    if last_tag is not None:
        move_files(f'{out_path}/doc', out_path)

def copy_files_to_out(in_paths : List[str], out_path : str):
    for f in in_paths:
        print(f"trying to move {f}")
        if (Path(f).is_file()):
            shutil.copy(f, out_path)
            print(f"Success!")


def get_lang_IRI_Table(ontology : Graph, lang : str):
    
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
    
    classes.sort(key= lambda c: c['IRI'])
    return markdown_table(classes).set_params(row_sep = 'markdown', quote = False).get_markdown()

def rewrite_ontology_metadata(out_path : str, ontology : Graph, repo, curr_tag : str, last_tag : str, cq_result_name : Optional[str]):
    g = ontology
    namespace, ontology_entity = get_ontology_entity(g)
    
    # print(ontology.serialize())

    commit_date = repo.head.commit.committed_datetime
    commit_date_str = f'{commit_date.year}-{commit_date.month}-{commit_date.day}'
    print(list(g.triples((None, DCTERMS.creator, None))))
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
    de_description = f'![Diagram]({onto_name}_diagram.svg)\n\n [IRI-Map](de-iri-table.md)'
    en_description = f'![Diagram]({onto_name}_diagram.svg)\n\n [IRI-Map](en-iri-table.md)'
    if cq_result_name:
        de_description += f'\n\n[Competency-Questions]({cq_result_name})'
        en_description += f'\n\n[Competency-Questions]({cq_result_name})'
    g.add((ontology_entity, DCTERMS.description, Literal(de_description, 'de')))
    g.add((ontology_entity, DCTERMS.description, Literal(en_description, 'en')))

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

    onto_entity = None

    for r in g.query("SELECT ?o WHERE { ?o a <http://www.w3.org/2002/07/owl#Ontology> }"):
        ontology_entity = r[0]
        break

    assert(ontology_entity is not None)

    namespace = None

    for r in g.query(f"SELECT ?c WHERE {{ ?c a <http://www.w3.org/2002/07/owl#Class> . FILTER (STRSTARTS(STR(?c), \"{ontology_entity}\")).}}"):
        class_uri = str(r[0])
        namespace = re.search(".*[#\/]", class_uri).group(0)
        break

    assert (namespace is not None)
    
    return namespace, ontology_entity

def generate_markdown_from_competency_questions(cqs, output_path, output_filename):
    output_md = "# Kompetenzfragen \n\n"

    for i, cq in enumerate(cqs, start=1):
        query = cq.query
        result = example_graph.query(query)
        
        output_format = ''
        try:
            result.serialize(f"{output_path}/cq_answers/{i}.csv", format='csv')
            output_format = 'csv'
        except PluginException:
            result.serialize(f"{output_path}/cq_answers/{i}.xml", format='xml')
            output_format = 'xml'

        output_md += f'''## {i}. Kompetenzfrage
{cq.plain}

```SPARQL
{cq.query}
```

[Antwort](./cq_answers/{i}.{output_format})
'''

    write_string_to_file(f'{output_path}/{output_filename}', output_md)


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
    
    ontology_path = f'copy/ontology/{onto_name}.ttl'
    example_individuals_path = f'copy/ontology/{onto_name}_individuals.ttl'

    g = Graph()
    g.parse(ontology_path)

    example_graph = Graph()
    example_graph.parse(ontology_path)
    example_graph.parse(example_individuals_path)

    write_string_to_file('./en-iri-table.md', get_lang_IRI_Table(g, 'en'))
    write_string_to_file('./de-iri-table.md', get_lang_IRI_Table(g, 'de'))
    
    is_cq_result_set = False
    cq_path = 'copy/ontology/docs/competency_questions.yml'
    cq_result_name = 'cq_results.md'
    try:
        cqs = create_competency_questions(read_yaml_file(cq_path))
        print("CQs read")
        generate_markdown_from_competency_questions(cqs, out_path, cq_result_name)
        print("CQs queried")
        is_cq_result_set = True
    except:
        print("CQs could not be read")
    
    prepared_ontology_path = "prepared_ontology.ttl"
    rewrite_ontology_metadata(prepared_ontology_path, g, repo, tag.name, prev_tag.name if prev_tag is not None else None, cq_result_name if is_cq_result_set else None)
    create_docs(onto_name, prepared_ontology_path, out_path, prev_tag)
    copy_files_to_out([f"copy/ontology/{onto_name}_diagram.svg", "/usr/local/widoco/index.html", './en-iri-table.md', './de-iri-table.md'], out_path)

    remove(prepared_ontology_path)


    if tag == tags[-1]:
        copytree(out_path, "out/", dirs_exist_ok=True)
    prev_tag = tag
