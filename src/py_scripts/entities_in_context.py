import spacy
from spacy.tokens import Doc, Token, Span, SpanGroup, DocBin
from spacy.language import Language
from medspacy.context import ConTextComponent, ConTextRule
from medspacy import get_extensions
from spacy.matcher import DependencyMatcher
import deplacy
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
contexter = None
depmatcher = None


#register token-level and span-level extensions in Spacy
try:
    #to deserialize docbin we need to set these again
    Token.set_extension("bner", default = []) 
    Token.set_extension("IS_BODY_ORGAN", default = 0)
    Token.set_extension("IS_MEDICATION", default = 0)
    Token.set_extension("IS_DISEASE", default = 0)
    
    Span.set_extension("IS_MEDICATION", default = 0)
    Span.set_extension("MEDICATION_DETAILS", default = {})
    
    Doc.set_extension("BOOK_PAGE", default = -1)
    
    #to be assigned by medspacy context 
    Span.set_extension("is_family_history", default=0)
    Span.set_extension("is_history", default=0)    
    Span.set_extension("never_family_history", default=0)
    Span.set_extension("never_history", default=0)
    
    #to be set based on dep matcher, on medication ents that have relations to the diseases they are taken for
    Span.set_extension("PURPOSE", default="")

except:
    pass

#--------------------------------------------------------------------

def custom_medspacy_context_component(nlp, name):
    """configure custom rules for medspacy"""
    #medspacy rules - some examples of custom rules (multiple other may be added)
    context_rules = [
        ConTextRule("history of", "HISTORY", direction="FORWARD", allowed_types={"bc5cdr:DISEASE"}),
        ConTextRule("family history of", "FAMILY_HISTORY", direction="FORWARD", allowed_types={"bc5cdr:DISEASE"}),
        ConTextRule("runs in his family", "FAMILY_HISTORY", direction="BACKWARD", allowed_types={"bc5cdr:DISEASE"},
                    pattern=[{"LEMMA": "run"},  {"LOWER": "in"},
                             {"LOWER": { "IN" : ["his","her","their"]}},   {"LEMMA": "family"}
                   ]),
        ConTextRule("in her family", "FAMILY_HISTORY", direction="BACKWARD", allowed_types={"bc5cdr:DISEASE"}),
        
        ConTextRule("no prior history of", "NO_HISTORY", direction="FORWARD", allowed_types={"bc5cdr:DISEASE"},
                   pattern=[{"LOWER": "no"}, {"LOWER" : "prior", "OP" : "?"},
                            {"LOWER": { "IN" : ["history", "past"]} }, {"LOWER" : "of"} ]),
        
        ConTextRule("denies history of", "NO_HISTORY", direction="FORWARD", allowed_types={"bc5cdr:DISEASE"}),
        ConTextRule("never suffered from", "NO_HISTORY", direction="FORWARD", allowed_types={"bc5cdr:DISEASE"}),
        ConTextRule("never had", "NO_HISTORY", direction="FORWARD", allowed_types={"bc5cdr:DISEASE"}),
        ConTextRule("no family history of", "NO_FAMILY_HISTORY", direction="FORWARD", allowed_types={"bc5cdr:DISEASE"}),
        
    ]
    
    custom_attrs = {
        'HISTORY': {'is_history': 1},
        'FAMILY_HISTORY': {'is_family_history': 1, 'is_history': 0},
        'NO_HISTORY' : { "never_history" : 1},
        'NO_FAMILY_HISTORY' : {'never_family_history': 1}
    }
    
    context = ConTextComponent(nlp, 
                               rules = "other", rule_list = context_rules, 
                               add_attrs=custom_attrs )
    return context


Language.factory("custom_medspacy_context", func = custom_medspacy_context_component)

        

#--------------------------------------------------------------------------

def prepare_depmatcher():
    """Configure patterns for the dependency matcher"""
    global depmatcher
    depmatcher = DependencyMatcher(nlp.vocab, validate = True)

    #see docs at https://spacy.io/usage/rule-based-matching#dependencymatcher
    #see also https://spacy.io/usage/rule-based-matching

    #examples of patterns to extract "medication for disease" (the list may be extended with additional patterns) 
    #note: we can't have modifiers in this case --> to specify optional we need 2 rules one with and one without that part
    
    #pattern 1 - e.g. his medication includes M for D / his medication includes M 25 mg for D
    #note: in "M for cholesterol", cholestero is not disease but chemical 
    pattern_1 = [
        # anchor token: verb ( takes [....] for, includes [...] for)
        {"RIGHT_ID": "the_verb",
         "RIGHT_ATTRS": {"POS": "VERB"} 
        },
        # verb -> medication
        {
          "LEFT_ID": "the_verb",
          "REL_OP": ">",
          "RIGHT_ID": "medication",
          "RIGHT_ATTRS": {"ENT_TYPE": "drugbank:MEDICATION_DRUGBANK"}
        },
        # the_verb -> for
        {
          "LEFT_ID": "the_verb",
          "REL_OP": ">",
          "RIGHT_ID": "for_",
          "RIGHT_ATTRS": { "POS": "ADP"}
        },
        #for -> disease
        {
          "LEFT_ID": "for_",
          "REL_OP": ">",
          "RIGHT_ID": "disease",
          "RIGHT_ATTRS": {"ENT_TYPE": {"IN": ["bc5cdr:DISEASE",  "drugbank:MEDICATION_DRUGBANK"]}}
        }
    ]
    
    #same as above (with one additional punctuation/space) but written using extensions instead of ENT_TYPE
    pattern_1s = [
        # anchor token: verb ( takes [....] for, includes [...] for)
        {"RIGHT_ID": "the_verb",
         "RIGHT_ATTRS": {"POS": "VERB"} 
        },
        # verb -> medication
        {
          "LEFT_ID": "the_verb",
          "REL_OP": ">",
          "RIGHT_ID": "medication",
          "RIGHT_ATTRS": {"_": {"IS_MEDICATION" : 1}}
        },
        # the_verb -> punct,spaces
        {
          "LEFT_ID": "the_verb",
          "REL_OP": ">",
          "RIGHT_ID": "pct",
          "RIGHT_ATTRS": { "POS": {"IN": ["SPACE" ]}}
        },
        # punctuation -> for
        {
          "LEFT_ID": "pct",
          "REL_OP": ">",
          "RIGHT_ID": "for_",
          "RIGHT_ATTRS": { "POS": "ADP"}
        },
        #for -> disease
        {
          "LEFT_ID": "for_",
          "REL_OP": ">",
          "RIGHT_ID": "disease",
          "RIGHT_ATTRS": {"ENT_TYPE": {"IN": ["bc5cdr:DISEASE",  "drugbank:MEDICATION_DRUGBANK"]}}
        }
    ]
    
    #pattern 2 - idem, but if tree has direct edge from "medication" to "for"
    pattern_2 = [
        # anchor token: verb ( takes [....] for, includes [...] for)
        {"RIGHT_ID": "the_verb",
         "RIGHT_ATTRS": {"POS": "VERB"} 
        },
        # verb -> medication
        {
          "LEFT_ID": "the_verb",
          "REL_OP": ">",
          "RIGHT_ID": "medication",
          "RIGHT_ATTRS": {"ENT_TYPE": "drugbank:MEDICATION_DRUGBANK"}
        },
        # the_verb -> for
        {
          "LEFT_ID": "medication",
          "REL_OP": ">",
          "RIGHT_ID": "for_",
          "RIGHT_ATTRS": { "POS": "ADP"}
        },
        #for -> disease
        {
          "LEFT_ID": "for_",
          "REL_OP": ">",
          "RIGHT_ID": "disease",
          "RIGHT_ATTRS": {"ENT_TYPE": {"IN": ["bc5cdr:DISEASE",  "drugbank:MEDICATION_DRUGBANK"]}}
        }
    ]
    
    #pattern 3 - e.g. is on  M for D 
    pattern_3 = [
        # anchor token: verb ( takes [....] for, includes [...] for)
        {"RIGHT_ID": "the_verb",
         "RIGHT_ATTRS": {"POS": {"IN" : ["VERB", "AUX"]}} 
        },
        #verb -> on
        {
          "LEFT_ID": "the_verb",
          "REL_OP": ">",
          "RIGHT_ID": "on_",
          "RIGHT_ATTRS": { "LEMMA": "on"}
        },
        # on -> medication
        {
          "LEFT_ID": "on_",
          "REL_OP": ">",
          "RIGHT_ID": "medication",
          "RIGHT_ATTRS": {"ENT_TYPE": "drugbank:MEDICATION_DRUGBANK"}
        },
        # medication -> for
        {
          "LEFT_ID": "medication",
          "REL_OP": ">",
          "RIGHT_ID": "for_",
          "RIGHT_ATTRS": { "POS": "ADP"}
        },
        #for -> disease
        {
          "LEFT_ID": "for_",
          "REL_OP": ">",
          "RIGHT_ID": "disease",
          "RIGHT_ATTRS": {"ENT_TYPE": "bc5cdr:DISEASE"}
        }
    ]
    
    #pattern 4 -e.g. include M1 and M2 for D1 ad D2 respectively 
    pattern_4 = [
        # anchor token: verb ( takes [....] for, includes [...] for)
        {"RIGHT_ID": "the_verb",
         "RIGHT_ATTRS": {"POS": "VERB"} 
        },
        # verb -> medication
        {
          "LEFT_ID": "the_verb",
          "REL_OP": ">",
          "RIGHT_ID": "medication1",
          "RIGHT_ATTRS": {"ENT_TYPE": "drugbank:MEDICATION_DRUGBANK"}
        },
        # medication1 -> and
        {
          "LEFT_ID": "medication1",
          "REL_OP": ">",
          "RIGHT_ID": "and_",
          "RIGHT_ATTRS": {"POS": "CCONJ"}
        },
        # medication1 -> medication2
        {
          "LEFT_ID": "medication1",
          "REL_OP": ">",
          "RIGHT_ID": "medication2",
          "RIGHT_ATTRS": {"ENT_TYPE": "drugbank:MEDICATION_DRUGBANK"}
        },
        # the_verb -> for
        {
          "LEFT_ID": "the_verb",
          "REL_OP": ">",
          "RIGHT_ID": "for_",
          "RIGHT_ATTRS": { "POS": "ADP"}
        },
        #for -> disease2
        {
          "LEFT_ID": "for_",
          "REL_OP": ">",
          "RIGHT_ID": "disease2",
          "RIGHT_ATTRS": {"ENT_TYPE": {"IN": ["bc5cdr:DISEASE",  "drugbank:MEDICATION_DRUGBANK"]}}
        },
        # disease2 -> disease1
        {
          "LEFT_ID": "disease2",
          "REL_OP": ">",
          "RIGHT_ID": "disease1",
          "RIGHT_ATTRS": {"ENT_TYPE": {"IN": ["bc5cdr:DISEASE",  "drugbank:MEDICATION_DRUGBANK"]}}
        },
        # disease1 -> and
        {
          "LEFT_ID": "disease1",
          "REL_OP": ">",
          "RIGHT_ID": "and__",
          "RIGHT_ATTRS": {"POS": "CCONJ"}
        },
        #the_verb -> respectively
        {
          "LEFT_ID": "the_verb",
          "REL_OP": ">",
          "RIGHT_ID": "respectively",
          "RIGHT_ATTRS": {"LOWER" : "respectively"}
        }
        
    ]
    
    
    depmatcher.add("patt1",[pattern_1])  
    depmatcher.add("patt1s",[pattern_1s])
    depmatcher.add("patt2",[pattern_2])  
    depmatcher.add("patt3",[pattern_3])
    depmatcher.add("patt4",[pattern_4])
    


#---------------------------------------------------------------------------

def prepare_spacy_pipeline():
    """Load English language model"""
    global nlp    
    global contexter
    nlp = spacy.load("en_core_web_lg", disable = ["ner"])
    nlp.add_pipe("custom_medspacy_context", last = True)
    contexter = nlp.get_pipe("custom_medspacy_context")
    return



def medspacy_findings(doc_bin):
    """Apply MedSpacy on each doc and register findings, it automatically updates extensions is_history and is_family_history on the doc's entities """
    list_docs = list(doc_bin.get_docs(nlp.vocab))
    list_docs_modified = []
    debug_flag = True
    
    for doc in list_docs:
        #the pipeline changed
        doc = contexter(doc)
        list_docs_modified.append(doc)
        
        if debug_flag is True:
            #debug prints
            for ii, modifier in enumerate(doc._.context_graph.modifiers):
                print(ii, "|", modifier, " | ", modifier.scope)
                print("-------------------------------------------------------------")

            print("|%40s | %20s | %20s | %20s | %20s |"%("ENTITY", "IS_HISTORY", "IS_FAMILY_HISTORY", "NEVER_HISTORY", "NEVER_FAMILY_HISTORY"))
            for ent in doc.ents:
                if ent.label_ == "bc5cdr:DISEASE":
                    print("|%40s | %20s | %20s | %20s | %20s |"%(ent.text, ent._.is_history, ent._.is_family_history, 
                                                  ent._.never_history, ent._.never_family_history))

            print("==========================================" * 3)
        
        #stop prints after first doc
        #debug_flag = False
        
    return list_docs_modified



def medication_disease_relations(list_docs):
    """Apply Spacy Dependency Matcher to extract relations between medication and their purpose (the disease)"""
    list_docs_modified = []
    
    for doc in list_docs:
        matches_ = depmatcher(doc)
        for match_ in matches_:
            pattern_name_matched = nlp.vocab.strings[match_[0]]  
            tokens_indices = match_[1]
            tokens_involved = [doc[ii] for ii in tokens_indices]
            print(pattern_name_matched, "-->", tokens_involved)
            
            if pattern_name_matched in ["patt1", "patt1s", "patt2", "patt3"]:
                #based on the name of the pattern, we decode the roles of the the takens involved
                if pattern_name_matched in ["patt1", "patt1s", "patt2"]:
                    medication_tok = tokens_involved[1]
                    purpose_tok =  tokens_involved[-1]
                elif pattern_name_matched in ["patt3"]:
                    medication_tok = tokens_involved[2]
                    purpose_tok =  tokens_involved[-1]
                    
                #on the medication entity set its purpose in an extension
                #get entity containing these tokens
                ent_medication = [ent for ent in doc.ents if ent.start <= medication_tok.i <= ent.end][0]
                ent_purpose =  [ent for ent in doc.ents if ent.start <= purpose_tok.i <= ent.end][0]
                ent_medication._.PURPOSE = ent_purpose.text
                
                print("=========> {}  HAS PURPOSE {}".format(ent_medication.text, ent_medication._.PURPOSE))
                    
            elif pattern_name_matched in ["patt4"]:
                medication1_tok = tokens_involved[1]
                medication2_tok = tokens_involved[3]
                purpose1_tok =  tokens_involved[5]
                purpose2_tok = tokens_involved[6]  
                
                #on the medication entity set its purpose in an extension
                #get entity containing these tokens
                ent_medication1 = [ent for ent in doc.ents if ent.start <= medication1_tok.i <= ent.end][0]
                ent_purpose1 =  [ent for ent in doc.ents if ent.start <= purpose1_tok.i <= ent.end][0]
                ent_medication1._.PURPOSE = ent_purpose1.text
                ent_medication2 = [ent for ent in doc.ents if ent.start <= medication2_tok.i <= ent.end][0]
                ent_purpose2 =  [ent for ent in doc.ents if ent.start <= purpose2_tok.i <= ent.end][0]
                ent_medication2._.PURPOSE = ent_purpose2.text
            
                print("=========> {}  HAS PURPOSE {}".format(ent_medication1.text, ent_medication1._.PURPOSE))
                print("=========> {}  HAS PURPOSE {}".format(ent_medication2.text, ent_medication2._.PURPOSE))
            
        list_docs_modified.append(doc)
        
    return list_docs_modified
    


def main():

    #parse arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('--myinput', action='append', nargs=1)  
    parser.add_argument('--myoutput', action='append', nargs=1)
    args = parser.parse_args()
    
    #extract inputs into variables
    input_file = args.myinput[0][0]
    target_file = args.myoutput[0][0]
    
    _ = prepare_spacy_pipeline()
    
    _ = prepare_depmatcher()
    
    doc_bin = DocBin().from_disk(input_file)
    
    one_doc = list(doc_bin.get_docs(nlp.vocab))[0]
    deplacy.render(list(one_doc.sents)[2],BoxDrawingWidth=1,EnableCR=False,WordRight=False,CatenaAnalysis=True)
    
    list_docs_modified = medspacy_findings(doc_bin)
    list_docs_modified2 = medication_disease_relations(list_docs_modified)
    
    
    #serialize the list of Spacy docs
    #however, TypeError: can not serialize 'ConTextModifier' object, so we remove the operational extensions set by medspacy
    
    #save docbin to file
    doc_bin2 = DocBin(store_user_data = True)
    for doc in list_docs_modified2:
        #useful to see all custom extension for a doc
        #print(doc.user_data)
        saved_userdata = {}
        for k,v in doc.user_data.items():
            if k[1] not in ["modifiers", "context_graph"]:
                saved_userdata[k] = v
        doc.user_data = saved_userdata
        doc_bin2.add(doc)
        
    doc_bin2.to_disk(target_file)
    
    
    
if __name__ == '__main__':
    main()