import spacy
from spacy.tokens import Doc, Token, Span, SpanGroup, DocBin
from intervaltree import Interval, IntervalTree
import pyjq
import pandas as pd
import json
import sys
import argparse
import pprint

pd.options.display.max_colwidth = 0 
pd.options.display.max_columns = None
pd.set_option('display.width', 1000)
pp = pprint.PrettyPrinter(width=150, compact=True)

nlp = None
dict_models_results = {}
list_spacy_docs = []
models_priority = ["drugbank", "bc5cdr", "bionlp13cg"]

#register token-level and span-level extensions in Spacy
try:
    Token.set_extension("bner", default = []) 
    Token.set_extension("IS_BODY_ORGAN", default = 0)
    Token.set_extension("IS_MEDICATION", default = 0)
    Token.set_extension("IS_DISEASE", default = 0)
    
    Span.set_extension("IS_MEDICATION", default = 0)
    Span.set_extension("MEDICATION_DETAILS", default = {})
    
    Doc.set_extension("BOOK_PAGE", default = -1)
except:
    pass


def prepare_spacy_pipeline():
    """Load English language model"""
    global nlp    
    nlp = spacy.load("en_core_web_lg", disable = ["ner"])
    
    return


def prefix_from_filename(input_file):
    """Return a string related to model name , to be furthe used for better provenance registration of consolidated labels"""
    prefix = ""
    
    if str(input_file).find("medication_bner_") != -1:
        prefix = "drugbank"
    elif str(input_file).find("_bc5cdr") != -1:
        prefix = "bc5cdr"
    elif str(input_file).find("_bionlp13cg") != -1:
        prefix = "bionlp13cg"
        
    return prefix



def load_bner_onto_tokens_extension(question, book_page):
    """Execute a PYJQ query to extract from each model's results the dict related to input book_page. 
     Collect labels in span groups at Spacy doc level and set appropriate extensions values on tokens"""
    doc = nlp(question)
    doc._.BOOK_PAGE = book_page
    doc.spans["bner_spans"] = []
    itree = IntervalTree()

    #we use pyjq to make a selection over a nested json with the aim to retain from each model the dict associated with the book_page
    ## se appendix 2 in readme
    expr =  '[.  | to_entries[] |  .key as $k | .value[] += {"model" : $k}] | .[].value[] | select (.book_page == '+ str(book_page) +')'
    
    results = pyjq.all(expr, dict_models_results)
    
    #we now start consolidation of entities registered at question level
    for prefix in models_priority:
        model_result = [el for el in results if el["model"] == prefix][0]
        bner_q = model_result["bner_question"]

        for ent in bner_q:
            #print(ent)
            #print("------------------------------------------------------------------------------------------")
            prefixed_label = "{}:{}".format(prefix, ent["label"])

            #create a span by char not by token ids because tokenization may differ between models
            span = doc.char_span(ent["char_limits"][0], ent["char_limits"][1], alignment_mode = "expand", label = prefixed_label)
            #if it's medication related, add supplementary details
            if ("drugbank_id" in ent) and (ent["drugbank_id"] != ""):
                span._.IS_MEDICATION = 1
                span._.MEDICATION_DETAILS["drugbank_id"] = ent["drugbank_id"]
            elif ("rxnorm_link" in ent) and (ent["rxnorm_link"] != ""):
                span._.IS_MEDICATION = 1
                span._.MEDICATION_DETAILS["rxnorm_link"] = ent["rxnorm_link"]

            #store this span in a span group for this model name
            doc.spans["bner_spans"].append(span)

            #check if it doesn't overlap alread inserted intervals in itree
            flag_overlaps = itree.overlaps(span.start,span.end)
            if (flag_overlaps is False):
                doc.ents += (span,)

            #store also in the interval tree
            itree[span.start : span.end] = prefixed_label           
       
    
    #now, for each token, query the itree to get all entities it belongs to
    for tok in doc:
        #entries in the response from the interval tree are triplets (istart,istop,data)
        list_ents_of_token =  itree[tok.i]
        list_ents_of_token_onlydata = [el[2] for el in list_ents_of_token]
        tok._.bner.extend(list_ents_of_token)
        
        #promote some labels to be usable in spacy matchers later on 
        if "bionlp13cg:ORGAN" in list_ents_of_token_onlydata:
            tok._.IS_BODY_ORGAN = 1
        elif "bc5cdr:DISEASE" in list_ents_of_token_onlydata:
            tok._.IS_DISEASE = 1
        elif "drugbank:MEDICATION_DRUGBANK" in list_ents_of_token_onlydata:
            tok._.IS_MEDICATION = 1
    
    return doc
    
    

def process_input_files(list_input_files):
    """for each file containing bner results, call processing to consolidate info onto a single spacy document of the text"""
    global dict_models_results
    global list_spacy_docs
        
    for input_file in list_input_files:
        prefix = prefix_from_filename(input_file)
        
        with open(input_file) as f:
            list_cases = json.load(f)
            dict_models_results[prefix] = list_cases
            
    
    #extract list of questions from all vignettes and create a mapping page -> vignette question
    dict_questions = {}
    for prefix, list_cases in dict_models_results.items():
        for vignette in list_cases:
            dict_questions[vignette["book_page"]] = vignette["question"]
    
    
    for book_page,question in dict_questions.items():
        doc_q = load_bner_onto_tokens_extension(question, book_page)
        list_spacy_docs.append(doc_q)
        
    return        
            

    
def print_debug(doc):
    
    list_info_tokens = [{"token" : tok.text,
                         "IS_BODY_ORGAN" : tok._.IS_BODY_ORGAN ,
                         "IS_DISEASE" : tok._.IS_DISEASE,
                         "IS_MEDICATION" : tok._.IS_MEDICATION,
                         "list_ents" : tok._.bner} 
                        for tok in doc]
    df_tokens = pd.DataFrame(list_info_tokens)
    df_tokens_filtered = df_tokens[df_tokens["IS_BODY_ORGAN"] + df_tokens["IS_DISEASE"] + df_tokens["IS_MEDICATION"] >0]
    print(df_tokens_filtered)
    
    print("================================================" *3)
    list_info_spans = [{"span" : span.text,
                        "tok_start" : span.start,
                        "tok_end" : span.end,
                        "label" : span.label_,
                        "IS_MEDICATION" : span._.IS_MEDICATION,
                        #"MEDICATION_DETAILS" : span._.MEDICATION_DETAILS,
                        "ANNOTATION" : [el.label_ for el in list(span.ents)]
                       }
                       for span in doc.spans["bner_spans"]]

    df_spans = pd.DataFrame(list_info_spans)
    df_spans.sort_values(by="tok_start", inplace = True)
    print(df_spans)
    print("================================================" *3)
    
    return


def main():

    #parse arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('--myinput', action='append', nargs="+")  #one or more files expected
    parser.add_argument('--myoutput', action='append', nargs=1)
    args = parser.parse_args()
    
    #extract inputs into variables
    list_input_files = [el for el in args.myinput[0]]
    target_file = args.myoutput[0][0]
            
    _ = prepare_spacy_pipeline()

    _ = process_input_files(list_input_files)
    
    doc_bin = DocBin(store_user_data = True)
    #serialize the list of Spacy docs 
    for doc in list_spacy_docs:
        doc_bin.add(doc)
        
    doc_bin.to_disk(target_file)
    
    #verify read
    doc_bin2 = DocBin().from_disk(target_file)
    print_debug(list(doc_bin2.get_docs(nlp.vocab))[0])
    
    
    
if __name__ == '__main__':
    main()
