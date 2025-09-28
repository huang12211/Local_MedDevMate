import pandas as pd

def read_input_file(input_path):
    #Read in the list of articles to download if free
    if ".csv" in input_path:
        pubmed_df = pd.read_csv(input_path)
        pubmed_df = pubmed_df.drop(['Citation', 'First Author', 'Create Date', 'PMCID', 'NIHMS ID'], axis=1)
    elif ".xlsx" in input_path:
        pubmed_df = pd.read_excel(input_path)

    pubmed_df['Title'] = pubmed_df['Title'].astype(str)
    pubmed_df['Authors'] = pubmed_df['Authors'].astype(str)
    pubmed_df['DOI'] = pubmed_df['DOI'].astype(str)
    
    return pubmed_df