import spacy
from spacy.matcher import Matcher
from spacy.tokens import Doc, Token, Span, SpanGroup


import pandas as pd
import json
import sys
import argparse
from tabulate import tabulate

nlp = None
matcher = None

#register span-level extensions in Spacy
try:
    Span.set_extension('drugbank_id', default="") 
except:
    pass


def prepare_spacy_pipeline(df_drugbank):
    """Load English language model and insert rules into the matcher for each medication name
    (lowercased for case insensitive matches)"""
    global nlp
    global matcher
    
    nlp = spacy.load("en_core_web_lg")
    matcher = Matcher(nlp.vocab)
    
    for i,row in df_drugbank.iterrows():
        medication_name = str(row["Common name"])
        medication_lowercase = medication_name.lower() 
        #simple pattern (see https://spacy.io/usage/rule-based-matching#adding-patterns-attributes)
        pattern = [{"LOWER": medication_lowercase}]
        matcher.add(medication_name, [pattern])
        
    return
    
    

def deterministic_bner_clinicaltext(df_drugbank, txt, debug_flag = False):
    """for the clinical text apply the Spacy Matcher to locate the spans
    that belong to the DrugBank vocabulary. Apply a filtering to retain only longest matches. 
    For each span record the DrugBank ID"""
    
    list_matches = []
    
    if debug_flag is True:
        print("example clinical text:")
        print(txt)
        print('----------------------------------------------------')

    #for the question pat of the vignette
    doc = nlp(txt)
    matches = matcher(doc)
    
    for match_id, start, end in matches:
        #decode the matched rule
        rule_name_matched = nlp.vocab.strings[match_id]  
        #the contiguous document span 
        span = doc[start:end] 
        #lookup the DrugBank ID
        drugbank_id = df_drugbank[df_drugbank["Common name"] == rule_name_matched]["DrugBank ID"].values[0]
        #set this info in the span-level extension
        span._.drugbank_id = drugbank_id
        list_matches.append(span)
     
    
    #filter the matches to retain only longest ones and discard subparts 
    #e.g. if "tok1" and "tok1 tok2" were matchd overlapping with rules r1 and r2 respectively, then r2 is retained
    list_longest_matches = spacy.util.filter_spans(list_matches)
    
    if debug_flag is True:
        print("example identified medication:")
        print(tabulate([(span.start, span.end, span.text, span._.drugbank_id) for span in list_longest_matches], 
                       tablefmt="fancy_grid",
                       headers=["start_token", "end_token", "text", "drugbank_id"]))
    
    #use dict comprehension
    list_medication = [{"entity" : span.text, "label": "MEDICATION_DRUGBANK", "drugbank_id" : span._.drugbank_id,
                        "char_limits": [span.start_char, span.end_char],
                        "token_limits" : [span.start, span.end]
                      } for span in list_longest_matches]
    
    return list_medication



def deterministic_bner_vignettes(df_drugbank, list_cases):
    """iterate through the vignettes in a list of clinical cases and apply for each question and answer the 
    medication entities extraction, returns a list of dicts, i.e. one dict with extracted medication entities for each vignette"""

    debug_flag = True
    list_results = []
    
    for i, vignette in enumerate(list_cases):
        
        txt_question = vignette["question"]
        txt_answer = vignette["answer"]
        
        #preprocess html &lt and &gt that usually appear in medical laboratory  analysis results
        txt_question = txt_question.replace("&lt;","<").replace("&gt;","<")      
        txt_answer = txt_answer.replace("&lt;","<").replace("&gt;","<")
                                                                                                                  
        list_medication_question = deterministic_bner_clinicaltext(df_drugbank, txt_question, debug_flag)
        #the following vignettes parts, without debugging prints
        debug_flag = False
        list_medication_answer = deterministic_bner_clinicaltext(df_drugbank, txt_answer, debug_flag)
            
        dict_bner = {"question" : txt_question, "answer" : txt_answer , "book_page": vignette["book_page"],
                    "bner_question": list_medication_question, "bner_answer": list_medication_answer
                    }
        list_results.append(dict_bner)

    return list_results



def main():
    
    #parse arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('--myinput', action='append', nargs=2,  metavar=('drugbank_json','pages_json'))
    parser.add_argument('--myoutput', action='append', nargs=1)
    args = parser.parse_args()
    
    #extract inputs into variables
    drugbank_json = args.myinput[0][0]
    pages_json = args.myinput[0][1] 
    target_file = args.myoutput[0][0]
    
    df_drugbank = pd.read_json(drugbank_json, orient = "records")
    print("example input medication vocabulary:")
    print(df_drugbank.head())
    print('----------------------------------------------------')
    
    with open(pages_json) as f:
        list_cases = json.load(f)
        
    _ = prepare_spacy_pipeline(df_drugbank)
    
    list_results = deterministic_bner_vignettes(df_drugbank, list_cases)
    
    #dump outputs to json files
    with open(target_file, "w") as fo:
        json.dump(list_results, fo)
        
        
if __name__ == '__main__':
    main()
