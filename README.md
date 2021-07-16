# NLP Clinical Vignettes 

#### Author: Camelia Ciolac

In this project:

1. I developed a cognitive service workflow to transform raw text of clinical vignettes into structured medical data  

Starting from raw text in a PDF file, the result is a content-rich PDF (in folder data/vignettes-reports) with:  

- medical entities highlighted over text,   
- health issues categorized into current or historic or absent or family-related   
- medication summary, including its purpose (in relation to which disease) as well as pointers to DrugBank and RxNorm knowledge bases  
- alerts about drug-drug interactions between the medication mentioned in the medical case  

This project thus joins the set of cognitive services applying NLP to clinical data, like Amazon Comprehend Medical, IBM Watson Annotator for Clinical Data, Azure Text Analytics for Health, etc. 

In this implementation I used:  

- pretrained BNER models from SciSpacy
- Matcher and DependencyMatcher of Spacy with custom patterns concerning medication and diseases
- MedSpacy for matching custom rules involving disease entities

Moreover, technologies of Tika, PDFKit, PyJQ, SPARQL were employed.   



2. The RENKU platform was successfully employed to record both the artifacts of the project and how these resulted from the workflow stages.  

The README\_TECHNICAL.md details all steps performed and, together with the notebook Renku\_KG.ipynb, it highlights the many benefits of using the RENKU platform for data science.  

Projects with a complex graph of processing stages benefit from this platform as it allows elegant provenance analysis through its lineage functionality.  
Along with MLOps, the platform also provides access to its Knowledge Graph, thus enabling data science projects to be organized semantically and their metadata to be governed for synergies.




**I want to acknowledge the data sources**, without which this project wouldn't have had the same contents: 

* The DrugBank Open Data ( https://go.drugbank.com/releases/latest#open-data ) 
* The Bio2RDF Virtuoso server ( https://drugbank.bio2rdf.org/sparql? ) provided me the opportunity to discover drug-drug interactions by writing SPARQL queries. 
* The book "Interesting Clinical Vignettes: 101 Ice Breakers for Medical Rounds"  by the team at Texas Tech University Health Sciences Center ( https://www.ttuhsc.edu/clinical-research/vignettes.aspx )  from which I extracted the clinical vignettes



