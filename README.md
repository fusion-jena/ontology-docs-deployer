# Ontology Docs Deployer

Automated documentation generator for OWL ontologies using [Widoco](https://github.com/dgarijo/Widoco). Generates versioned documentation with diagrams, IRI tables, and competency question results.

## Features

- **Version Management**: Automatically processes all git tags (v*) and generates documentation for each version
  - Patch versions are automatically dropped (e.g., if both v1.0.0 and v1.0.1 exist, only v1.0.1 is documented)
- **Metadata Enrichment**: Injects version info, modification dates, namespace details, and citation metadata into ontologies
- **IRI Tables**: Generates bilingual (DE/EN) markdown tables of all classes and properties
- **Competency Questions**: Executes SPARQL queries against example data and documents results
- **Multi-language**: Supports German and English documentation

## Metadata Overrides

The tool automatically sets these ontology properties from git metadata:

- `owl:versionIRI` → from git tag
- `owl:versionInfo` → from git tag (without 'v' prefix)
- `owl:priorVersion` → from previous git tag
- `dct:modified` → from commit date
- `vann:preferredNamespacePrefix` → from ontology filename
- `vann:preferredNamespaceUri` → from ontology entity IRI
- `dct:description` → diagram + IRI table links + competency questions link
- `schema:citation` → formatted citation with creator, title, and version

## Usage

Run as a Docker container in a workspace containing:
- `ontology/{name}.ttl` (main ontology file)
- `ontology/{name}_individuals.ttl` (optional example individuals for competency questions)
- `ontology/{name}_diagram.svg` (optional diagram)
- `docs/competency_questions.yml` (optional)

See [Widoco's metadata guide](https://github.com/dgarijo/Widoco/blob/master/doc/metadataGuide/guide.md) for supported properties.
