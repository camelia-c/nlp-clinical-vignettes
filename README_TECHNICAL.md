# NLP Clinical Vignettes 

#### Author: Camelia Ciolac

NLP for cllnical vignettes, extracting from text various types of biomedical entities, the clinical history, current medication and related drugs interactions.

The final results are in `data/vignettes_reports` both in PDF and in HTML format.  

The notebook "notebooks/Renku_KG.ipynb" is a companion to this README and it contains some insights related to metadata stored about this project, after steps 1-to-9 were all executed.


### GitLab repo for new project

Query project metadata from RENKU Knowledge Graph:

```
wget  -qO-  "https://renkulab.io/knowledge-graph/projects/ciolac_c/nlp-clinical-vignettes"   |  python -m json.tool
```

Clone GitLab repository locally:

```
renku clone https://renkulab.io/gitlab/ciolac_c/nlp-clinical-vignettes

Cloning https://renkulab.io/gitlab/ciolac_c/nlp-clinical-vignettes ...
remote: Counting objects: 100% (15/15), done.
remote: Compressing objects: 100% (11/11), done.
OK


cd nlp-clinical-vignettes

± |master ✓| → ls
Dockerfile  README.md  data  environment.yml  notebooks  requirements.txt
```

# Datasets

**First dataset - Book PDF**

```
renku dataset create book_clinical_cases \
  -t "Interesting Clinical Vignettes: 101 Ice Breakers for Medical Rounds" \
  -d "Texas Tech University Health Sciences Center, https://www.ttuhsc.edu/clinical-research/vignettes.aspx" \
  -k "clinical cases,clinical vignettes,book,pdf"

Use the name "book_clinical_cases" to refer to this dataset.
OK
 
 
renku dataset add book_clinical_cases https://www.ttuhsc.edu/clinical-research/documents/JMD-Cases-of-Interest.pdf

Info: Adding these files to Git LFS:                                                                                                                                    
        data/book_clinical_cases/JMD-Cases-of-Interest.pdf
To disable this message in the future, run:
        renku config set show_lfs_message False
OK

```

**Second dataset - DrugBank vocabulary**

```
renku dataset create drugbank_vocab \
   -t "DrugBank Vocabulary" \
   -d "DrugBank Open Data, https://go.drugbank.com/releases/latest#open-data" \
   -k "drugbank,medication,csv"

Use the name "drugbank_vocab" to refer to this dataset.
OK


renku dataset add drugbank_vocab https://go.drugbank.com/releases/5-1-8/downloads/all-drugbank-vocabulary

Info: Adding these files to Git LFS:                                                                                                                                             
        data/drugbank_vocab/drugbank_all_drugbank_vocabulary.csv.zip
To disable this message in the future, run:
        renku config set show_lfs_message False
OK


```


**Overview of the datasets and their files**

```
renku dataset ls
ID                                    NAME                 TITLE                                                                VERSION
------------------------------------  -------------------  -------------------------------------------------------------------  ---------
6bdd2e04-9c88-4415-9de6-bc7b21e2be33  drugbank_vocab       DrugBank Vocabulary
f71677c9-ea04-48a7-892d-fd8b85fffb73  book_clinical_cases  Interesting Clinical Vignettes: 101 Ice Breakers for Medical Rounds

renku dataset ls-files
DATASET NAME         ADDED                  SIZE  PATH                                                          LFS
-------------------  -------------------  ------  ------------------------------------------------------------  -----
book_clinical_cases  2021-07-13 08:39:44  1.2 MB  data/book_clinical_cases/JMD-Cases-of-Interest.pdf            *
drugbank_vocab       2021-07-13 08:42:07  773 KB  data/drugbank_vocab/drugbank_all_drugbank_vocabulary.csv.zip  *
```

Metadata about datasets can be read from repository files (note: these are not ids listed in the table of datasets above):  

```
ls .renku/datasets
4b7d7b8a-f536-4d62-8bdd-136d5872a034  567569cb-0545-4d3d-98ad-2e15784d6e80

cat .renku/datasets/4b7d7b8a-f536-4d62-8bdd-136d5872a034/metadata.yml 

cat .renku/datasets/567569cb-0545-4d3d-98ad-2e15784d6e80/metadata.yml 

```

Also, metadata can be queried from the Renku Knowledge Graph.   
For this, first we need to commit changes and push to remote repository:  

```
± |master ↑6 U:1 ✗| → renku status
Error: The repository is dirty. Please use the "git" command to clean it.

On branch master
Your branch is ahead of 'origin/master' by 6 commits.
  (use "git push" to publish your local commits)

Changes not staged for commit:
  (use "git add <file>..." to update what will be committed)
  (use "git checkout -- <file>..." to discard changes in working directory)

        modified:   README.md
...


renku save -m "added project datasets"
```

Now perform:     

```
wget  -qO-  "https://renkulab.io/knowledge-graph/projects/ciolac_c/nlp-clinical-vignettes/datasets"   |  python -m json.tool
```

**Temporary files**

A txt file containing  the pages numbers (one per line) of the clinical vignettes to be extracted from the PDF book for the current analysis.

E.g. 
```
mkdir -p data/tmp_files
  
cat << EOF > data/tmp_files/pages_selection.txt
14
24
26
60
76
114
116
120
140
160
208
9999
EOF

renku save -m "added file of selected pages"
```

# Workflow

### Step 1

Use Apache Tika to extract individual text pages from the PDF book and create JSON file with the clinical vignettes questions and answers on selected pages.

```
cat << EOF > requirements.txt
tika==1.24
EOF

pip install -r requirements.txt

mkdir -p src/py_scripts

touch src/py_scripts/extract_book_pages.py

```

Prepare a folder where outputs wil be stored and a folder where errors will be stored:

```
mkdir -p data/outputs

mkdir -p data/errors

renku save
```

Now, we run the Python script as a workflow step with metadata: 

```
renku run \
    --name step1_pdf2txt \
    --description "use Tika (Java server) to extract text from selected PDF book pages and output JSON file of these" \
    --keyword "tika, pdf" \
    --no-output-detection \
    --output data/outputs/vignettes_selection1.json \
     python src/py_scripts/extract_book_pages.py \
        --myinput data/book_clinical_cases/JMD-Cases-of-Interest.pdf data/tmp_files/pages_selection.txt \
        --myoutput data/outputs/vignettes_selection1.json \
        --errors data/errors/errors_selection1.json
```

This command has 2 parts:
* ```renku run ... python``` 
    - sets metadata of this stage (name, description, keyword)
    - specifies explicitly to consider as output only the file in data/output
    - desactivates auto-detection of outputs, so that the file in data/error is not registered as output of this step
    - the automatic inputs detection is still active
* ```python ...```
    - the common execution of a python script 
    - named arguments that will be parsed with argparse inside the script 
    - one input belongs to a dataset, the other input is a txt file 
    - note that the "--input" and "--output" are renku-specific args and they don't get passed to the script, so we need to use "--myinput" and "--myoutput" instead
    
So far, we can see the data lineage with:

```
± |master ✓| → renku log
*    600f1920 data/outputs/vignettes_selection1.json
|\
| \
| |\
+-+---*  5dab203f .renku/workflow/8710de739c144d02a80ca83d8f663502_python.yaml
| | |/
| * |  fddc3dbb data/book_clinical_cases/JMD-Cases-of-Interest.pdf
| | |           (part of data/book_clinical_cases directory)
| * |  fddc3dbb data/book_clinical_cases
| | |           (part of data directory)
| @ |  fddc3dbb (latest -> 5dab203f) data
|  /
| | @  50659b8b requirements.txt
* |  50659b8b src/py_scripts/extract_book_pages.py
| |           (part of src/py_scripts directory)
| | @  50659b8b README.md
* |  50659b8b src/py_scripts
| |           (part of src directory)
@ |  50659b8b src
 /
*  c7a07efb data/tmp_files/pages_selection.txt
|           (part of data/tmp_files directory)
| @  c7a07efb (latest -> 50659b8b) README.md
*  c7a07efb data/tmp_files
|           (part of data directory)
@  c7a07efb (latest -> 5dab203f) data
```

We can also inspect the YAML file:

```
cat .renku/workflow/8710de739c144d02a80ca83d8f663502_python.yaml
```



### Step 2

We unzip and preprocess the DrugBank vocabulary from the second dataset of this project.  
A Pandas dataframe is used for data manipulation and the result is serialized as JSON.  

```
echo "pandas==1.0.3" >> requirements.txt

pip install -r requirements.txt

touch src/py_scripts/preprocess_drugbank_vocab.py

renku run \
    --name step2_vocabjson \
    --description "use Pandas to make a simple dictionary from the zipped csv of DrugBank vocabulary" \
    --keyword "pandas, zipped csv" \
    python src/py_scripts/preprocess_drugbank_vocab.py \
        --myinput data/drugbank_vocab/drugbank_all_drugbank_vocabulary.csv.zip \
        --myoutput data/tmp_files/drugbank_vocab.json 

```

We can now inspect:

```
renku log data/tmp_files/drugbank_vocab.json 
*    f4e1b76e data/tmp_files/drugbank_vocab.json
|\
+---*  f9858111 .renku/workflow/d2b3b40ae03d40dc802c0619cda216f3_python.yaml
| |/
| *  0477996f data/drugbank_vocab/drugbank_all_drugbank_vocabulary.csv.zip
| |           (part of data/drugbank_vocab directory)
| *  0477996f data/drugbank_vocab
| |           (part of data directory)
| @  0477996f (latest -> f4e1b76e) data
| @  d4c89e17 README.md
| @  d4c89e17 requirements.txt
*  d4c89e17 src/py_scripts/preprocess_drugbank_vocab.py
|           (part of src/py_scripts directory)
*  d4c89e17 src/py_scripts
|           (part of src directory)
@  d4c89e17 src
```

### Step 3

Extract medication from the clinical vignettes using Spacy Matcher, simultaneously performing entity linking with the DrugBank.   
First, install Python packages:

```
echo "scispacy==0.4.0" >> requirements.txt
pip install -r requirements.txt

#spacy gets automatically installed (as dependency of scispacy)
pip show spacy

Name: spacy
Version: 3.0.6
Summary: Industrial-strength Natural Language Processing (NLP) in Python
Home-page: https://spacy.io
Author: Explosion
Author-email: contact@explosion.ai
License: MIT
Location: /usr/local/lib/python3.8/site-packages
Requires: wasabi, tqdm, catalogue, cymem, pathy, blis, requests, packaging, srsly, jinja2, numpy, thinc, murmurhash, spacy-legacy, setuptools, preshed, typer, pydantic


#download Spacy large English language model 
python -m spacy download en_core_web_lg


python -m spacy validate

✔ Loaded compatibility table

================= Installed pipeline packages (spaCy v3.0.6) =================
ℹ spaCy installation: /usr/local/lib/python3.8/site-packages/spacy

NAME                   SPACY            VERSION                            
en_core_web_lg         >=3.0.0,<3.1.0   3.0.0   ✔

```

Now implement the functionality and run stage:

```
touch src/py_scripts/bner_drugbank.py

renku run \
    --name step3_drugbankbner \
    --description "use a Spacy matcher based on DrugBank vocabulary to extract medication entities from text, setting the ids from DrugBank KB" \
    --keyword "spacy,matcher,drugbank" \
    python src/py_scripts/bner_drugbank.py \
        --myinput data/tmp_files/drugbank_vocab.json  data/outputs/vignettes_selection1.json \
        --myoutput data/outputs/medication_bner_selection1.json 
        
```

Inspect lineage of resulted file of this stage:

```
renku log data/outputs/medication_bner_selection1.json 
```

### Step 4

Enrich the vignette with information about drug-drug interactions queried with SPARQL from Bio2RDF Virtuoso server (https://drugbank.bio2rdf.org/sparql).  
For the each drug in the current medication taken by the pacient of each clinical vignette, list the known interactions with other drugs.  

Note: because of some SSL Certificate issues with the Virtuoso server, namely:  
```
HTTPSConnectionPool(host='drugbank.bio2rdf.org', port=443): Max retries exceeded with url: /sparql (Caused by SSLError(SSLCertVerificationError("hostname 'drugbank.bio2rdf.org' doesn't match either of 'bio2rdf.org', 'openlifedata.org', 'search.openlifedata.org', 'sparql.openlifedata.org', 'virtuoso.openlifedata.org'")))

```  
we use requests library and not the SPARQLWrapper in Python.

```
touch src/py_scripts/drugdrug_interactions_drugbank.py

renku run \
    --name step4_rdf2bio \
    --description "send requests to RDF2bio Virtuoso server with SPARQL queries to detect interactions between drugs that form the medication of each clinical case" \
    --keyword "sparql,drugbank,rdf2bio" \
     python src/py_scripts/drugdrug_interactions_drugbank.py \
        --myinput data/outputs/medication_bner_selection1.json  \
        --myoutput data/outputs/drugdrug_interactions_selection1.json 
        
```

### Step 5

Inference with pretrained SciSpacy models and entity linking to RXNORM.

But first, install the models:

```
echo "https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.4.0/en_ner_craft_md-0.4.0.tar.gz" >> requirements.txt
echo "https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.4.0/en_ner_jnlpba_md-0.4.0.tar.gz" >> requirements.txt
echo "https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.4.0/en_ner_bc5cdr_md-0.4.0.tar.gz" >> requirements.txt
echo "https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.4.0/en_ner_bionlp13cg_md-0.4.0.tar.gz" >> requirements.txt
 
pip install -r requirements.txt
```

Note that SciSpacy pretrained models currently extract entities of the following types (source: https://allenai.github.io/scispacy/):

<table>
    <tr>
        <td> model </td>
        <td> entities types </td>
    </tr>
    <tr>
        <td>en_ner_craft_md </td>
        <td>GGP, SO, TAXON, CHEBI, GO, CL</td>
    </tr>
    <tr>
        <td>en_ner_jnlpba_md </td>
        <td>DNA, CELL_TYPE, CELL_LINE, RNA, PROTEIN</td>
    </tr>
    <tr>
        <td>en_ner_bc5cdr_md</td>
        <td>DISEASE, CHEMICAL</td>
    </tr>
    <tr>
        <td>en_ner_bionlp13cg_md</td>
        <td>AMINO_ACID, ANATOMICAL_SYSTEM, CANCER, CELL, CELLULAR_COMPONENT, DEVELOPING_ANATOMICAL_STRUCTURE, <br/>
            GENE_OR_GENE_PRODUCT, IMMATERIAL_ANATOMICAL_ENTITY, MULTI-TISSUE_STRUCTURE, ORGAN, ORGANISM, <br/>
            ORGANISM_SUBDIVISION, ORGANISM_SUBSTANCE, PATHOLOGICAL_FORMATION, SIMPLE_CHEMICAL, TISSUE</td>
    </tr>
</table>

We shall showcase only with models bc5cdr and bionlp13cg.  
This time we disable automatic inputs and outputs detection on the run command and instead use the renku-python package to programmatically record these.

Now we can perform:
```
touch src/py_scripts/bner_scispacy.py

renku run \
    --name step5a_scispacy \
    --description "use SciSpacy to extract entities with the NER  pretrained on biomedical corpus and link the drugs entities to RXNORM KB" \
    --keyword "scispacy,bner,rxnorm" \
    --no-input-detection \
    --no-output-detection \
    python src/py_scripts/bner_scispacy.py \
        --myinput data/outputs/vignettes_selection1.json  \
        --bnermodel bc5cdr

renku run \
    --name step5b_scispacy \
    --description "use SciSpacy to extract entities with the NER  pretrained on biomedical corpus and link the drugs entities to RXNORM KB" \
    --keyword "scispacy,bner,rxnorm" \
    --no-input-detection \
    --no-output-detection \
    python src/py_scripts/bner_scispacy.py \
        --myinput data/outputs/vignettes_selection1.json  \
        --bnermodel bionlp13cg

```

### Step 6 

Consolidate entities results across pipelines applied so far.  

```
echo "intervaltree==3.1.0" >> requirements.txt
echo "pyjq==2.5.2" >> requirements.txt

pip install -r requirements.txt

touch src/py_scripts/consolidate_results.py

renku run \
    --name step6_consolidate \
    --description "with the multiple pipelines applied so far, which annotated different entities, we consolidate them and save a binary Spacy DocBin" \
    --keyword "spacy,docbin" \
    python src/py_scripts/consolidate_results.py  \
      --myinput data/outputs/vignettes_selection1_bc5cdr.json  data/outputs/vignettes_selection1_bionlp13cg.json  data/outputs/medication_bner_selection1.json \
      --myoutput data/outputs/consolidated_bner_selection1.bin


```

The result of this consolidation allows us to structure dataframes of token-level and span-level biomedical information, e.g.:  

```
             token  IS_BODY_ORGAN  IS_DISEASE  IS_MEDICATION                                           list_ents
12  nausea          0              1           0              ((12, 13, bc5cdr:DISEASE),)                                                                              
14  vomiting        0              1           0              ((14, 15, bc5cdr:DISEASE),)                                                                              
20  arrhythmias     0              1           0              ((20, 21, bc5cdr:DISEASE),)                                                                              
22  xanthopsia      0              1           0              ((22, 23, bc5cdr:DISEASE), (22, 23, bionlp13cg:CANCER))                                                  
40  chronic         0              1           0              ((40, 45, bc5cdr:DISEASE),)                                                                              
41                  0              1           0              ((40, 45, bc5cdr:DISEASE),)                                                                              
42  obstructive     0              1           0              ((40, 45, bc5cdr:DISEASE),)                                                                              
43  pulmonary       1              0           0              ((43, 44, bionlp13cg:ORGAN), (40, 45, bc5cdr:DISEASE))                                                   
44  disease         0              1           0              ((40, 45, bc5cdr:DISEASE),)                                                                              
46  chronic         0              1           0              ((46, 49, bc5cdr:DISEASE),)                                                                              
47  renal           1              0           0              ((46, 49, bc5cdr:DISEASE), (47, 48, bionlp13cg:ORGAN))                                                   
48  insufficiency   0              1           0              ((46, 49, bc5cdr:DISEASE),)                                                                              
51  heart           1              0           0              ((51, 52, bionlp13cg:ORGAN), (51, 53, bc5cdr:DISEASE))                                                   
52  failure         0              1           0              ((51, 53, bc5cdr:DISEASE),)                                                                              
60  clarithromycin  0              0           1              ((60, 61, drugbank:MEDICATION_DRUGBANK), (60, 61, bc5cdr:CHEMICAL), (60, 61, bionlp13cg:SIMPLE_CHEMICAL))
62  digoxin         0              0           1              ((62, 63, bionlp13cg:SIMPLE_CHEMICAL), (62, 63, drugbank:MEDICATION_DRUGBANK), (62, 63, bc5cdr:CHEMICAL))
70  lobar           0              1           0              ((70, 71, bionlp13cg:MULTI_TISSUE_STRUCTURE), (70, 72, bc5cdr:DISEASE))                                  
71  pneumonia       0              1           0              ((70, 72, bc5cdr:DISEASE),)                                                                              
73  heart           1              0           0              ((73, 75, bc5cdr:DISEASE), (73, 74, bionlp13cg:ORGAN))                                                   
74  failure         0              1           0              ((73, 75, bc5cdr:DISEASE),)                                                                              
79  digoxin         0              0           1              ((79, 80, drugbank:MEDICATION_DRUGBANK), (79, 80, bc5cdr:CHEMICAL))                                      
================================================================================================================================================
                                      span  tok_start  tok_end                              label  IS_MEDICATION                    ANNOTATION
16  woman                                   5          6        bionlp13cg:ORGANISM                0              [bionlp13cg:ORGANISM]          
3   nausea                                  12         13       bc5cdr:DISEASE                     0              [bc5cdr:DISEASE]               
4   vomiting                                14         15       bc5cdr:DISEASE                     0              [bc5cdr:DISEASE]               
5   arrhythmias                             20         21       bc5cdr:DISEASE                     0              [bc5cdr:DISEASE]               
17  xanthopsia                              22         23       bionlp13cg:CANCER                  0              [bc5cdr:DISEASE]               
6   xanthopsia                              22         23       bc5cdr:DISEASE                     0              [bc5cdr:DISEASE]               
7   chronic  obstructive pulmonary disease  40         45       bc5cdr:DISEASE                     0              [bc5cdr:DISEASE]               
18  pulmonary                               43         44       bionlp13cg:ORGAN                   0              []                             
8   chronic renal insufficiency             46         49       bc5cdr:DISEASE                     0              [bc5cdr:DISEASE]               
19  renal                                   47         48       bionlp13cg:ORGAN                   0              []                             
20  heart                                   51         52       bionlp13cg:ORGAN                   0              []                             
9   heart failure                           51         53       bc5cdr:DISEASE                     0              [bc5cdr:DISEASE]               
21  clarithromycin                          60         61       bionlp13cg:SIMPLE_CHEMICAL         1              [drugbank:MEDICATION_DRUGBANK] 
0   clarithromycin                          60         61       drugbank:MEDICATION_DRUGBANK       1              [drugbank:MEDICATION_DRUGBANK] 
10  clarithromycin                          60         61       bc5cdr:CHEMICAL                    1              [drugbank:MEDICATION_DRUGBANK] 
22  digoxin                                 62         63       bionlp13cg:SIMPLE_CHEMICAL         1              [drugbank:MEDICATION_DRUGBANK] 
11  digoxin                                 62         63       bc5cdr:CHEMICAL                    1              [drugbank:MEDICATION_DRUGBANK] 
1   digoxin                                 62         63       drugbank:MEDICATION_DRUGBANK       1              [drugbank:MEDICATION_DRUGBANK] 
12  lobar pneumonia                         70         72       bc5cdr:DISEASE                     0              [bc5cdr:DISEASE]               
23  lobar                                   70         71       bionlp13cg:MULTI_TISSUE_STRUCTURE  0              []                             
24  heart                                   73         74       bionlp13cg:ORGAN                   0              []                             
13  heart failure                           73         75       bc5cdr:DISEASE                     0              [bc5cdr:DISEASE]               
14  digoxin                                 79         80       bc5cdr:CHEMICAL                    1              [drugbank:MEDICATION_DRUGBANK] 
2   digoxin                                 79         80       drugbank:MEDICATION_DRUGBANK       1              [drugbank:MEDICATION_DRUGBANK] 
25  serum                                   80         81       bionlp13cg:ORGANISM_SUBSTANCE      0              [bionlp13cg:ORGANISM_SUBSTANCE]
26  [0.5-2 ng/ml].                          87         96       bionlp13cg:SIMPLE_CHEMICAL         0              [bc5cdr:CHEMICAL]              
15  0.5-2 ng/ml].                           88         96       bc5cdr:CHEMICAL                    0              [bc5cdr:CHEMICAL]              
================================================================================================================================================
```


### Step 7 

Building upon the consolidated entities, we define some rules for the Spacy Dependency Matcher and use MedSpacy to interpret the entities in context.  
For example, it's not enough to extract diseases names as entities, we also need to interpret if they are specified as medical history, family medical history or even if they're negated.  
Similarly, it's useful - if the text contains this information - to draw relationships between medication taken and the health issues for which it is taken.  
Basically in this stage we put together a structured profile of the patient described in the clinical vignette.

```
echo "git+https://github.com/camelia-c/medspacy.git@spacy-v3" >> requirements.txt
echo "deplacy==1.9.1" >> requirements.txt

pip install -r requirements.txt

touch src/py_scripts/entities_in_context.py


renku run \
    --name step7_structure \
    --description "we extract relations between medication and disease entities using dependency matcher and contextualize health issues as history/family past with MedSpacy" \
    --keyword "medspacy,dependency matcher, docbin" \
    python src/py_scripts/entities_in_context.py  \
      --myinput data/outputs/consolidated_bner_selection1.bin \
      --myoutput data/outputs/structured_bner_selection1.bin



```

### Step 8

Make a summary of all information extracted and generate a PDF for each clinical vignette, useful for the end-users.  
We generate a separate PDF file for each vignette, so the outputs will be set programmatically in `".renku/tmp/outputs.txt"`

```
echo "pdfkit==0.6.1" >> requirements.txt

pip install -r requirements.txt

touch src/py_scripts/create_result_pdf.py

mkdir -p data/vignettes_reports



renku run \
    --name step8_report \
    --description "generate a pdf file for each clinical vignette, in which report structured information and visualize entities highlighted in text" \
    --keyword "html,pdfkit,docbin" \
    python src/py_scripts/create_result_pdf.py  \
      --myinput1_docbin data/outputs/structured_bner_selection1.bin  \
      --myinput2_ddi  data/outputs/drugdrug_interactions_selection1.json 

```

### Step 9

A parameterized notebook (executed using Papermill) allows the interactive exploration of results stored in the Spacy DocBin outputed at step 7 above.

```
echo "papermill==2.3.3" >> requirements.txt
echo "pyfiglet==0.7" >> requirements.txt

pip install -r requirements.txt

which papermill
###/usr/local/bin/papermill


touch notebooks/ParameterizedNotebook.ipynb

rm -f notebooks/ParametrizedNotebook.ran.ipynb 


renku run \
    --name step9_spacy_notebook \
    --description "parameterized notebook to be executed with papermill for a specified book page and sentence in focus, visualizing dependency graph, tokens extensions, entities" \
    --keyword "papermill,spacy" \
    papermill notebooks/ParametrizedNotebook.ipynb \
          notebooks/ParametrizedNotebook.pag14_sent2.ipynb \
          -p input_path data/outputs/structured_bner_selection1.bin \
          -p selected_page 14 \
          -p sentence_in_focus 2
          
          
```


### Step 10 

Notebook to query the Renku Knowledge Graph after we concluded steps 1-to-9.

```
echo "columnize==0.3.10" >> requirements.txt
echo "pyyaml==5.4.1" >> requirements.txt

pip install -r requirements.txt

touch notebooks/Renku_KG.ipynb
```




## Appendix  

This is an explanation in relation to consolidation stage (step 6) of the workflow.   
Exercise online at https://jqplay.org/    

   
   
```
### Suppose we have a toy json of :
{
  "a": [
    { "bp": 10,  "txt": "aaa"},
    { "bp": 20, "txt": "bbb" }
  ],
  "c": [
    { "bp": 10,  "txt": "ccc" },
    { "bp": 20, "txt": "ddd" }
  ]
}


### PYJQ expression "[.  | to_entries[] |  .key as $k | .value[] += {"model" : $k} ]"  converts it to:

[{
  "key": "a",
  "value": [
    { "bp": 10,  "txt": "aaa",  "model": "a"},
    { "bp": 20,  "txt": "bbb",  "model": "a"}
  ]
}
{
  "key": "c",
  "value": [
    { "bp": 10,  "txt": "ccc",  "model": "c" },
    { "bp": 20,  "txt": "ddd",  "model": "c"  }
  ]
}]


### which we further refine as: "[.  | to_entries[] |  .key as $k | .value[] += {"model" : $k}] | .[].value[]" to obtain:

{ "bp": 10,  "txt": "aaa",  "model": "a"},
{ "bp": 20,  "txt": "bbb",  "model": "a"},
{ "bp": 10,  "txt": "ccc",  "model": "c" },
{ "bp": 20,  "txt": "ddd",  "model": "c"  }

###followedd by selection of items with  bp = 10:
### "[.  | to_entries[] |  .key as $k | .value[] += {"model" : $k}] | .[].value[] | select (.bp == 10) "

{ "bp": 10,  "txt": "aaa",  "model": "a"},
{ "bp": 10,  "txt": "ccc",  "model": "c" },

```
