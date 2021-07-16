import pandas as pd
import json
import sys
import argparse

def preprocess_csv(zip_csv):
    """create dataframe from zipped csv file and project on columns of interest"""

    df_vocab = pd.read_csv(zip_csv)
    print(df_vocab.columns)
    print("--------------------------------------------------")
    print(df_vocab.head(5))
    
    #for this demo we ignore synonyms of the drugs names and adhere to their standard name (as is also used in the book)
    df_projected = df_vocab[["DrugBank ID", "Common name"]]
    return df_projected
    

def main():
    #parse arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('--myinput', action='append', nargs=1)
    parser.add_argument('--myoutput', action='append', nargs=1)
    args = parser.parse_args()
    
    #extract inputs into variables
    zip_csv = args.myinput[0][0]
    target_file = args.myoutput[0][0]
    
    df_drugbank = preprocess_csv(zip_csv)
    
    #dump output to json file
    df_drugbank.to_json(target_file, orient = "records")

if __name__ == '__main__':
    main()

