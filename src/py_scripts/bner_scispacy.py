import spacy
from scispacy.abbreviation import AbbreviationDetector
from scispacy.linking import EntityLinker

import pandas as pd
import json
import sys
import argparse
from tabulate import tabulate
import pprint

from renku.api import Input, Output, Parameter

pp = pprint.PrettyPrinter(width=150, compact=True)

nlp = None
linker = None

def prepare_spacy_pipeline(bner_model):
    """Load the specified pretrained biomedical pipeline and add stages for abbreviation decoding and for entity linking"""
    global nlp
    global linker
    
    model_fullname = "en_ner_{}_md".format(bner_model)
    nlp = spacy.load(model_fullname)
    nlp.add_pipe("abbreviation_detector")
    nlp.add_pipe("scispacy_linker", config={"resolve_abbreviations": True, "linker_name": "rxnorm"})
    linker = nlp.get_pipe("scispacy_linker")
    print(nlp.pipe_names)
    return
    
    
def scispacy_bner_clinicaltext(txt, debug_flag = False):
    """apply the scispacy pipeline and collect extracted entities for further use"""
    list_entities = []
    list_abbrev = []
    
    doc = nlp(txt)
    for ent in doc.ents:
        #an item of ent._.kb_ents is a tuple e.g. ('C0055856', 1.0)
        list_entities.append({"entity" : ent.text, "label": ent.label_, 
                              "rxnorm_link" : linker.kb.cui_to_entity[ent._.kb_ents[0][0]] if len(ent._.kb_ents) > 0 else "",
                              "char_limits": [ent.start_char, ent.end_char],
                              "token_limits" : [ent.start, ent.end]
                              })
        
    #extract abbreviations
    for abbrev in doc._.abbreviations:
        list_abbrev.append({"abbrev":abbrev.text, "extended": str(abbrev._.long_form)})
        
    dict_result = {"entities": list_entities, "abbrev" : list_abbrev} 
    if (debug_flag is True):
        print(txt)
        print("----------------------------------------------------------")
        pp.pprint(dict_result)

    return dict_result   
    
    
    
def scispacy_bner_vignettes(list_cases):
    """iterate through the vignettes in a list of clinical cases and apply for each question and answer the 
    entities extraction, returns a list of dicts, i.e. one dict with extracted entities for each vignette"""

    debug_flag = True
    list_results = []
    
    for i, vignette in enumerate(list_cases):
        
        txt_question = vignette["question"]
        txt_answer = vignette["answer"]
        
        #preprocess html &lt and &gt that usually appear in medical laboratory  analysis results
        txt_question = txt_question.replace("&lt;","<").replace("&gt;","<")      
        txt_answer = txt_answer.replace("&lt;","<").replace("&gt;","<")
                                                                                                                  
        dict_result_question = scispacy_bner_clinicaltext(txt_question, debug_flag)
        #the following vignettes parts, without debugging prints
        debug_flag = False
        dict_result_answer = scispacy_bner_clinicaltext(txt_answer, debug_flag)
            
        dict_bner = {"question" : txt_question, "answer" : txt_answer , "book_page": vignette["book_page"],
                     "bner_question": dict_result_question["entities"], 
                     "bner_answer": dict_result_answer["entities"], 
                     "abbrev_question": dict_result_question["abbrev"], 
                     "abbrev_answer":  dict_result_answer["abbrev"]
                    }
        list_results.append(dict_bner)

    return list_results
    
    
def main():
    
    #parse arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('--myinput', action='append', nargs=1)
    parser.add_argument('--bnermodel', action='append', nargs=1, choices = ["craft", "jnlpba", "bc5cdr", "bionlp13cg"])
    args = parser.parse_args()
    
    #extract inputs into variables
    file_json = args.myinput[0][0] 
    bner_model = args.bnermodel[0][0]
    file_json_output = file_json.replace(".json", "_" + bner_model + ".json") 

    #register the used model name as parameter in renku
    bner_model_param = Parameter(name="bner_model_name", value=bner_model)
    
    #with open(file_json) as f:
    with open(Input(file_json)) as f:
        list_cases = json.load(f)
                
            
    _ = prepare_spacy_pipeline(bner_model_param)
    
    list_results =  scispacy_bner_vignettes(list_cases)
    
    #dump outputs to json files
    #with open(file_json_output, "w") as fo:
    with open(Output(file_json_output), "w") as fo:
        json.dump(list_results, fo)
   
    
    

if __name__ == '__main__':
    main()