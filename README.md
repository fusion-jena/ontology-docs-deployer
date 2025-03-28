# ontology-docs-deployer

Sets and overrides:
- owl:versionIRI (from git tag)
- dct:modified (from last git commit date)
- vann:preferredNamespacePrefix (from ontology file name)
- dct:description (to always contain "![Diagram]({vann:preferredNamespacePrefix}_diagram.svg)", THIS WILL OVERRIDE ANYTHING ELSE YOU PUT INTO dct:description)
- vann:preferredNamespaceUri (from ontology entity IRI)
- owl:priorVersion (from previous git tag)
- owl:versionInfo (from git tag)
- schema:citation (commonly abbreviated SDO apparently) ("Cite this vocabulary as: {dct:creator}, {dct:title} {from tag}"@en and "Zitieren Sie dieses Vokabular als: {dct:creator}, {dct:title} {from tag}"@de)