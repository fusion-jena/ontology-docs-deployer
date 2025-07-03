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
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class CompetencyQuestion:
    def __init__(self, plain, query):
        self.plain = plain
        self.query = query

    def __repr__(self):
        return f"CompetencyQuestion(plain='{self.plain}', query='{self.query}')"

def create_competency_questions(questions):
    logging.info('Creating competency questions from YAML.')
    return [CompetencyQuestion(q['plain'], q['query']) for q in questions['competency-questions']]


def read_yaml_file(file_path):
    logging.info(f'Reading YAML file: {file_path}')
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            data = yaml.safe_load(file)
            logging.info('YAML file loaded successfully.')
            return data
    except FileNotFoundError:
        logging.error(f"File not found: {file_path}")
        return None
    except yaml.YAMLError as e:
        logging.error(f"Error parsing YAML file: {e}")
        return None

def write_string_to_file(file_path : str, content : str):
    logging.info(f'Writing string to file: {file_path}')
    try:
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(content)
        logging.info(f"String written to {file_path} successfully.")
    except Exception as e:
        logging.error(f"Error writing to {file_path}: {str(e)}")

def move_files(source_dir : str, destination_dir : str):
    logging.info(f'Moving files from {source_dir} to {destination_dir}')
    for item in os.listdir(source_dir):
        shutil.move(os.path.join(source_dir, item), destination_dir)

def create_docs(onto_name : str, ontology_path : str, out_path : str, last_tag : str):
    logging.info(f"Calling Widoco with onto_name={onto_name}, ontology_path={ontology_path}, out_path={out_path}, last_tag={last_tag}")
    subprocess.run(f"java -jar /usr/local/widoco/widoco.jar -ontFile {ontology_path} -import {ontology_path} -outFolder {out_path} -rewriteAll -getOntologyMetadata -lang de-en -saveConfig out/config -webVowl -noPlaceHolderText -uniteSections", shell=True)
    if len(glob(f'{out_path}/doc/*')) > 0:
        try:
            move_files(f'{out_path}/doc', out_path)
            logging.info(f"Moved files from {out_path}/doc to {out_path}")
        except Exception as e:
            logging.warning(f"Could not move files from doc: {e}")

def copy_files_to_out(in_paths : List[str], out_path : str):
    for f in in_paths:
        logging.info(f"Trying to move {f} to {out_path}")
        if (Path(f).is_file()):
            shutil.copy(f, out_path)
            logging.info(f"Copied {f} to {out_path}")

def get_lang_IRI_Table(ontology : Graph, lang : str):
    logging.info(f'Generating IRI table for language: {lang}')
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
    if len(classes) == 0:
        logging.info('No classes found for IRI table.')
        return ''
    
    return markdown_table(classes).set_params(row_sep = 'markdown', quote = False).get_markdown()

def get_data_from_prop(g: Graph, entity : URIRef, property: URIRef):
    logging.info(f'Getting data from property: {property}')
    results = list(g.triples((entity, property, None)))
    if len(results) > 0:
        return str(results[0][2])
    


def rewrite_ontology_metadata(out_path : str, ontology : Graph, repo, curr_tag : str, last_tag : str, cq_result_name : Optional[str]):
    logging.info(f'Rewriting ontology metadata for tag: {curr_tag}, previous tag: {last_tag}')
    g = ontology
    namespace, ontology_entity = get_ontology_entity(g)
    
    # print(ontology.serialize())

    commit_date = repo.head.commit.committed_datetime
    commit_date_str = f'{commit_date.year}-{commit_date.month}-{commit_date.day}'
    
    creator = get_data_from_prop(g, ontology_entity, DCTERMS.creator) 
    title = get_data_from_prop(g, ontology_entity, DCTERMS.title)
    
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
    if creator is not None and title is not None:
        g.remove((ontology_entity, SDO.citation, None))
        g.add((ontology_entity, SDO.citation, Literal(f"{creator}, {title} v{version}")))

    g.serialize(out_path, format="ttl")
    logging.info(f'Ontology metadata written to {out_path}')

def get_ontology_entity(g : Graph):
    logging.info('Getting ontology entity and namespace.')
    onto_entity = None

    for r in g.query("SELECT ?o WHERE { ?o a <http://www.w3.org/2002/07/owl#Ontology> }"):
        ontology_entity = r[0]
        break

    assert (ontology_entity is not None)

    namespace = None

    for r in g.query(f"SELECT ?c WHERE {{ ?c a <http://www.w3.org/2002/07/owl#Class> . FILTER (STRSTARTS(STR(?c), \"{ontology_entity}\")).}}"):
        class_uri = str(r[0])
        namespace = re.search(".*[#\/]", class_uri).group(0)
        break

    if namespace is None:
        logging.error("Could not determine namespace from ontology entity.")
        namespace = str(ontology_entity).rsplit('/', 1)[0] + '/'

    assert (namespace is not None)
    return namespace, ontology_entity

def generate_markdown_from_competency_questions(cqs, output_path, output_filename, example_graph):
    logging.info(f'Generating markdown from competency questions to {output_path}/{output_filename}')
    output_md = "# Kompetenzfragen \n\n"
    os.makedirs(output_path+'/cq_answers')

    for i, cq in enumerate(cqs, start=1):
        query = cq.query
        result = example_graph.query(query)
        
        output_format = ''
        try:
            result.serialize(f"{output_path}/cq_answers/{i}.csv", format='csv')
            output_format = 'csv'
        except Exception:
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
    logging.info(f'Markdown for competency questions written to {output_path}/{output_filename}')


logging.info('Changing working directory to /github/workspace')
root = "/github/workspace"
chdir(root)

logging.info('Removing ./out and ./copy directories if they exist.')
rmtree("./out", ignore_errors=True)
rmtree("./copy", ignore_errors=True)
logging.info('Copying workspace to ./copy')
copytree(root, "./copy")

logging.info('Initializing git repo in ./copy')
repo = Repo.init("./copy")
tags = natsorted([t for t in repo.tags if t.name.startswith('v')], key= lambda t: t.name)

prev_tag = None
def handleCQs(create_competency_questions, read_yaml_file, generate_markdown_from_competency_questions, out_path, ontology_path, example_individuals_path, cq_path, cq_result_name):
    example_graph = Graph()
    
    try:
        logging.info(f'Parsing example individuals file: {example_individuals_path}')
        example_graph.parse(ontology_path)
        example_graph.parse(example_individuals_path)
    except Exception as e:
        logging.error(f"Error parsing example individuals or ontology file: {e}")
        return False

    try:
        logging.info(f'Reading and processing competency questions from {cq_path}')
        cqs = create_competency_questions(read_yaml_file(cq_path))
        logging.info("CQs read successfully.")
        generate_markdown_from_competency_questions(cqs, out_path, cq_result_name, example_graph)
        logging.info("CQs queried and markdown generated.")
        return True
    except Exception as e:
        logging.warning(f"CQs could not be read or processed: {e}")

for tag in tags:
    logging.info(f'Checking out tag: {tag}')
    repo.git.checkout(tag)

    onto_files = [basename(f) for f in glob('copy/ontology/*.ttl')]
    onto_files.sort(key=len)
    onto_name = onto_files[0][:-4]
    logging.info(f'Processing ontology: {onto_name}')
    out_path = f"out/{tag.name[1:]}"
    ontology_path = f'copy/ontology/{onto_name}.ttl'
    example_individuals_path = f'copy/ontology/{onto_name}_individuals.ttl'

    g = Graph()
    logging.info(f'Parsing ontology file: {ontology_path}')
    g.parse(ontology_path)

    write_string_to_file('./en-iri-table.md', get_lang_IRI_Table(g, 'en'))
    write_string_to_file('./de-iri-table.md', get_lang_IRI_Table(g, 'de'))
    
    cq_path = 'copy/docs/competency_questions.yml'
    cq_result_name = 'cq_results.md'

    is_cq_result_set = handleCQs(create_competency_questions, read_yaml_file, generate_markdown_from_competency_questions, out_path, ontology_path, example_individuals_path, cq_path, cq_result_name)
    
    prepared_ontology_path = "prepared_ontology.ttl"
    rewrite_ontology_metadata(prepared_ontology_path, g, repo, tag.name, prev_tag.name if prev_tag is not None else None, cq_result_name if is_cq_result_set else None)
    create_docs(onto_name, prepared_ontology_path, out_path, prev_tag)
    copy_files_to_out([f"copy/ontology/{onto_name}_diagram.svg", "/usr/local/widoco/index.html", './en-iri-table.md', './de-iri-table.md'], out_path)

    remove(prepared_ontology_path)
    logging.info(f'Cleaned up prepared ontology file: {prepared_ontology_path}')

    if tag == tags[-1]:
        logging.info(f'Copying {out_path} to out/')
        copytree(out_path, "out/", dirs_exist_ok=True)
    prev_tag = tag
logging.info('Script finished.')
