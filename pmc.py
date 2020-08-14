from Bio import Entrez              #allows us to connect to database
from Bio import Medline             #allows us to read Medline citations
import pandas as pd                 #used for data handling
from urllib.error import HTTPError
import requests  #check for HTTP errors
import datetime                     #used for timekeeping (large values)
from datetime import datetime as dt
from functools import reduce        #used for merging dataframes
import re                           #used for regular expressions
import time                         #used for short times
import numpy                        #also used for exploding and data structures
import shutil                       #quick way to join CSVs
import glob                         #quick way to get pathnames for combining CSVs
import os
import math
from requests.adapters import HTTPAdapter
from bs4 import BeautifulSoup
import sys

start = dt.now()                                                        #record total time for program
def get_pmcid_master(PMCID_path, output_path, lines_per_file, windows = False):
    csv_file_number = 0                                                 #initialize naming parameter                   #open the ID file and read every newline into a list
    _clean_europmc_ids(PMCID_path)
    idlist = list(filter(None, open(PMCID_path).read().splitlines()))                        #filters out any random blank lines               
    chunks = [idlist[x:x+lines_per_file] for x in range(0, len(idlist), lines_per_file)]        #break up the IDs into chunks
    total_ids = len(idlist)
    print("Number of IDs is", total_ids)
    estimated_time = (datetime.timedelta(seconds =  .323 * total_ids))
    print('Estimated Time:', str(estimated_time))
    time.sleep(2)                           
    times = []                                                  #the time each record took to retrieve and parse
    problematic_pmcids = []                                     #record PMCIDS with no abstract
    Entrez.email = 'pbhat@terpmail.umd.edu'
    Entrez.api_key = "a7d48bae5b50d916e974238db878570d8d08"     #allows for 10 downloads per request
    i = 0
    for chunk in chunks:
        csv_file_number += 1                                        #for the filename naming convention
        abstract_dict = {}                                          #initialize dictionaries, flush them everytime you start a new chunk
        abstract_section_dict = {}                                  #how many sections the abstract was split into
        author_dict = {}                                            #author
        title_dict = {}                                             #title
        affiliation_dict = {}                                       #affiliations 
        year_dict = {}                                              # year of publication
        pmid_dict = {}                                              #PMID (if avaliable)
        doi_dict= {}                                                #dois/identifiers
        print('Number of Lines Per File:', str(len((chunk))))
        print('Number of Files: ', str(math.ceil(total_ids/len(chunk))))
        for pmcid in chunk:
            i+=1                                         #for each pmcid
            if not re.match(r'PMC\d{2,8}', pmcid):                  #make sure the ID is a valid PMCID
                print('This is not a PMCID')
            start_time = time.time()                                #time each for loop
            try:
                handle = Entrez.efetch(db="PMC", id= pmcid,
                        rettype ="medline", retmode="text")  #retrieve MEDLINE citations from each ID
            except:                                       #try not to kill the program if server bans you
                continue
            articles = Medline.read(handle)                         #read medline citation into a python 
            print("Fetching Information for",pmcid, "... (", 
                    i, '/', total_ids, ')')
            time.sleep(.01)                                                                 
            for _ in articles:                          
                if "AB" in articles:                                                        #check for abstracts
                    abstract = articles['AB']                                   
                    if len(abstract) < (3000):                                              #if length is below 3000 characters                    
                        abstract_section_dict[pmcid] = [1]                                  #should be only 1 section (in list form)
                        abstract_dict[pmcid] = [abstract]
                    else:                                                                   #if the length of abstract is more than 3000 characters
                        sentences = re.findall(r'(.{0,3000}(?<=\.))', abstract)             
                        sentences = list(filter(None, sentences))                           #use regex to chunk texts into ~3000 character parts
                        abstract_dict[pmcid] = sentences                                    #without interrupting sentences  
                        r1 = 1
                        r2 = len(sentences)
                        abstract_section_dict[pmcid] = [item for item in range(r1, r2+1)]   #number of sections the abstract was split into (as a list)
                else:
                    problematic_pmcids.append(pmcid)                                        #if no abstract, append into problematic pmcids
                    abstract_dict[pmcid] = None
        #check for identifier
            for _ in articles:
                if "AID" in articles:                                                          
                    identifs = articles['AID']
                    if any('[doi]' in s for s in identifs):                                    #DOI preffered
                        dois = [s for s in identifs if '[doi]' in s]
                        cleandois = _clean_lists(dois)
                        doi_dict[pmcid] = cleandois
                    else:
                        cleanidentifs = _clean_lists(identifs)                              #if the DOI isnt there, use any identifier that is there
                        doi_dict[pmcid] = cleanidentifs
                else:
                    doi_dict[pmcid] = None
        #check for title
            for _ in articles:
                if "TI" in articles:                                                           
                    title = articles['TI']
                    title_dict[pmcid] = title
                else:
                    title_dict[pmcid] = None
        #check for authors
            for _ in articles:
                if "FAU" in articles:
                    authors = articles['FAU']
                    cleanauth = (_clean_lists(authors)).rstrip(',')             #remove the trailing comma after the last author
                    author_dict[pmcid] =cleanauth
                else:
                    author_dict[pmcid] = None
                    problematic_pmcids.append(pmcid)
        #check for PMID
            for _ in articles:
                if "PMID" in articles:
                    pmid = articles['PMID']
                    pmid_dict[pmcid] = pmid
                else:
                    pmid_dict[pmcid] = None
        #check for affiliations
            for _ in articles:
                if "AD" in articles:
                    if len(articles['AD']) >= 5:                                                    #only want first 5 affiliations if more are present
                        affil=articles['AD'][:5]
                        cleanaffil = "~~ ".join([" ".join(n.split(", ")[::-1]) for n in affil])     #change delimiter to '~~ ' and remove brackets around list
                        affiliation_dict[pmcid] = cleanaffil                        
                    else:
                        short = articles['AD']
                        short += [''] * (5 - len(short))                                            #pad the affiliations list if it is below length 5 
                        cleanshort = "~~ ".join([" ".join(n.split(", ")[::-1]) for n in short])     #change delimiter and remove brackets
                        affiliation_dict[pmcid] = cleanshort
                else:
                    nulls = ["","","","",""]                                                        #if no affiliation is listed, then insert empty list
                    cleannulls = "~~ ".join([" ".join(n.split(", ")[::-1]) for n in nulls])         #change delimiter
                    affiliation_dict[pmcid] = cleannulls
        #check for various dates: see https://biopython.org/docs/1.74/api/Bio.Medline.html
            for _ in articles:
                if "DP" in articles:      #publication date                                                          
                    date = articles['DP']
                    year_dict[pmcid] = str(date)
                elif "DEP" in articles:  # electronic publication date
                    elecdate = str(articles['DEP'])
                    if len(elecdate) == 8:
                        cleandate= dt(year=int(elecdate[0:4]), month=int(elecdate[4:6]), day=int(elecdate[6:8]))      #seperate month day and year from date string
                        year_dict[pmcid] = str(dt.strftime(cleandate, "%Y"))                                          #only take the year as a string
                    else:
                    #date was already given just as a year
                        year_dict[pmcid] = elecdate                                         
                elif "DCOM" in articles:  # date completed
                    comtitle = articles['DCOM']
                    year_dict[pmcid] = comtitle
                elif "DA" in articles:     # date created
                    credate = articles['DA']
                    year_dict[pmcid] = credate
                elif "LR" in articles:     #date last revised
                    lastrev = articles['LR']
                    year_dict[pmcid] = lastrev
                elif "EDAT" in articles:    #Entrez date
                    entrezdate = articles['EDAT']
                    year_dict[pmcid] = entrezdate
                else:
                    #print("No Date!")
                    problematic_pmcids.append(pmcid)
                    year_dict[pmcid] = None 
            time_taken = time.time()- start_time            #time for for loop
            times.append(time_taken)                        #add each time the for-loop took into a list 
            print("* took", time_taken, 's *')
            if (time_taken) > 20:                           #try to avoid request overload to Entrez database
                print('Sleeping for 15 seconds')
                time.sleep(15)
        
        new_output_path = output_path + str(csv_file_number) + '.csv' #change output path names for every new chunk by adding the stem + a section number
        
        _handle_dataframes(abstract_dict,title_dict,author_dict,year_dict, pmid_dict, affiliation_dict, doi_dict, abstract_section_dict, new_output_path, estimated_time, windows= False) #pass dictionaries to data conversion function
            #send the dictionaries (for each chunk), to the handle data frames function where thet will be merged
            #and sent to a .csv
            #time.sleep(.02) #avoid overloads
    handle.close()
    print('\n', 'Average Time per PMCID:', (reduce(lambda a, b: a + b, times) / len(times) ), 'sec')
    return


# function to manage the dictionaries and create the final CSV file
def _handle_dataframes(dict1,dict2,dict3,dict4, dict5, dict6, dict7, dict8, output_path, estimated_time, windows):
    pd.set_option("display.max_rows", None, "display.max_columns", None)
    prepared_abstract_dict = _prepare_dicts(dict1)      #use helper function to fix abstracts
    df = pd.DataFrame.from_dict(prepared_abstract_dict, orient='index', columns=['PMCID','ABSTRACT'] )      #load prepared dictionary into data frames
                                                                                                                #       |
                                                                                                                #       |
    prepared_title_dict = _prepare_dicts(dict2)                                                                 #       |
    df2 = pd.DataFrame.from_dict(prepared_title_dict, orient='index', columns=['PMCID','TITLE'] )               #       |    
                                                                                                                #       |
                                                                                                                #       |
    prepared_author_dict = _prepare_dicts(dict3)                                                                #       |
    df3 = pd.DataFrame.from_dict(prepared_author_dict, orient='index', columns=['PMCID','AUTHORS'] )            #       |
                                                                                                                #       |

    prepared_year_dict = _prepare_dicts(dict4)                                                                  #       |
    df4 = pd.DataFrame.from_dict(prepared_year_dict, orient='index', columns=['PMCID','YEAR'] )                 #       |
    
    prepared_pmid_dict = _prepare_dicts(dict5)                                                                  #       |
    df5 = pd.DataFrame.from_dict(prepared_pmid_dict, orient = 'index', columns = ['PMCID', 'PMID'])             #       |


    prepared_affil_dict = _prepare_dicts(dict6)                                                                 #       |
    df6 = pd.DataFrame.from_dict(prepared_affil_dict, orient = "index", columns = ['PMCID', 'Affiliations'])        #Just the first 5 affiliations, read into dataframe
    df6['Affiliations'] = df6['Affiliations'].astype(str)
    #split the list of affiliations into the five different authors based on the delimiter
    df6[['Author 1 Affiliation','Author 2 Affiliation','Author 3 Affiliation','Author 4 Affiliation','Author 5 Affliation']] = df6.Affiliations.str.split("~~ ", expand = True)
    
    
    prepared_doi_dict = _prepare_dicts(dict7)
    df7 = pd.DataFrame.from_dict(prepared_doi_dict, orient = 'index', columns = ['PMCID', 'Identifier'])
    df7['Identifier'] = df7['Identifier'].str.strip().str.extract(r'(\s+(.*\S))', expand = False)

    prepared_abstract_num_dict = _prepare_dicts(dict8)
    df8 = pd.DataFrame.from_dict(prepared_abstract_num_dict, orient = 'index', columns = ['PMCID', 'SECTION'])


    dfs = [df4, df5, df3, df2, df7, df, df6, df8]                                                   #data frames to be merged
    df_final = reduce(lambda left,right: pd.merge(left,right,on='PMCID'), dfs)                      #merge the data frames based on PMCID           
    
    df_final['YEAR'] = df_final['YEAR'].str.extract(r'(\d+)', expand=False)                         #guarantees that only the year is selected
    df_final.drop(['Affiliations'], axis =1)                                                        #drop the column with unassociated affiliations
    
    #if the abstract section is more than 1, we want to copy each row except for the abstract section, which is iterated over
    df_final = _explode(df_final, ['SECTION', 'ABSTRACT'], fill_value='', preserve_index=False)     #use the EXPLODE helper function to handle the abstract sections
    clean_affiliations(df_final,'Author 1 Affiliation','Author 2 Affiliation','Author 3 Affiliation','Author 4 Affiliation','Author 5 Affliation') #apply a regex to clean up the affiliations column


    df_final = df_final.sort_values(by =['PMCID'], ascending = False) 
    df_final['len'] = df['ABSTRACT'].astype(str).map(len)                                           #optional length of the abstract column
                                                                                                    #include in colnames array if u use it    
    
    new = df_final["SECTION"].astype(str).copy()
    df_final["UNIQUEID"] = df_final["PMCID"].str.cat(new, sep ="_")
    first_col = df_final.pop("UNIQUEID")
    df_final.insert(0, 'UNIQUEID', first_col)
    
    
    #column names to be written to the CSV (need to match with the dataframe columns)
    colnames =(['UNIQUEID','PMCID', 'PMID', 'YEAR', 'TITLE', 'SECTION', 'ABSTRACT', 'Identifier', 'AUTHORS', 'Author 1 Affiliation','Author 2 Affiliation','Author 3 Affiliation',
                'Author 4 Affiliation','Author 5 Affliation'])
    
    df_final.to_csv(output_path, sep = ',', encoding = 'utf-8-sig', index= False, columns = colnames) #write to the CSV
    
    #everytime a .csv file is created, we want to print this statement
    print('************************************************************')
    time_to_csv = dt.now()-start
    print('\n\n','CSV created', 'in', output_path, '\n', 'Process took', str(time_to_csv))  #the total is a running total

    print('\n')
    print('************************************************************')
    if not windows:
        _notify(title    = 'CSV' +  output_path[-7:] + ' has been Created',
        subtitle =  'Runtime: ' + str(time_to_csv),
        message  = 'Est. Time Remaning: ' + str(estimated_time-time_to_csv) 

        )              #We should post the message to the OS every time the CSV is made
    return df_final

#--------------- helper functions---------------#
# column explodes rows based on the "Abstract Section" entry to make sure entries are less than 3000 characters

def _explode(df, lst_cols, fill_value='', preserve_index=False ): #adapted from      https://stackoverflow.com/questions/12680754/split-explode-pandas-dataframe-string-entry-to-separate-rows
    # make sure `lst_cols` is list-alike (abstract_section and abstract)
    if (lst_cols is not None
        and len(lst_cols) > 0
        and not isinstance(lst_cols, (list, tuple, numpy.ndarray, pd.Series))):
        lst_cols = [lst_cols]                                               #make sure list columns are actual columns
    # all columns except `lst_cols`
    idx_cols = df.columns.difference(lst_cols)
    # calculate lengths of lists
    try:
        lens = df[lst_cols[0]].str.len()                                    #make sure the headers are strings
    except AttributeError:
        return
    # preserve original index values    
    idx = numpy.repeat(df.index.values, lens)
    # create "exploded" DF
    res = (pd.DataFrame({
                col:numpy.repeat(df[col].values, lens)
                for col in idx_cols},
                index=idx)
             .assign(**{col:numpy.concatenate(df.loc[lens>0, col].values)
                            for col in lst_cols}))
    # append those rows that have empty lists
    if (lens == 0).any():
        # at least one list in cells is empty
        res = (res.append(df.loc[lens==0, idx_cols], sort=False)
                  .fillna(fill_value))
    # revert the original index order
    res = res.sort_index()
    # reset index if requested
    if not preserve_index:        
        res = res.reset_index(drop=True)
    return res

def combine_csv(output_path, output_csv):                     #function to combine all of the CSVs
    path = re.sub(r'([^\/]+$)', '', output_path)                                      
    allFiles = glob.glob(path + "/*.csv")                       #look for all files ending with .csv in the directory
    allFiles.sort()  # glob lacks reliable orders the file by ID
    with open(output_csv, 'wb') as outfile:                     #start writing to the output .csv
        for i, fname in enumerate(allFiles):
            with open(fname, 'rb') as infile:
                if i != 0:
                    infile.readline()  # Throw away header on all but first file
                # Block copy rest of file from input to output without parsing
                shutil.copyfileobj(infile, outfile)
                print(fname + " has been imported.")   
    return 

def _prepare_dicts(dict_in):
    prepared_dict= {i: x for i, x in enumerate(dict_in.items())}  #creates a dictionary within a dictionary
    return prepared_dict
   
def _clean_lists(list_in):
    cleaned_list = " ".join([" ".join(n.split(" ")[::-1]) for n in list_in])        #remove the square brackets and the commas from a string
    return cleaned_list                                                             #to place it in CSV file

def _clean_europmc_ids(euro_pmcid_file):
    pattern  = r'PMC\d{4,8}'
    new_file = [] # Make sure file gets closed after being iterated
    with open(euro_pmcid_file, 'r') as f:
    # Read the file contents and generate a list with each line
        lines = f.readlines()
    # Iterate each line
    for line in lines:
        # Regex applied to each line 
        match = re.search(pattern, line)
        if match:
            # Make sure to add \n to display correctly when we write it back
            new_line = match.group() + '\n'
            new_file.append(new_line)
    with open(euro_pmcid_file, 'w') as f:
         # go to start of file
        f.seek(0)
        # actually write the lines
        f.writelines(new_file)
    return new_file

def _notify(title, subtitle, message):                  #sends a notification to mac computers every time a CSV file is created
    t = '-title {!r}'.format(title)
    s = '-subtitle {!r}'.format(subtitle)
    m = '-message {!r}'.format(message)
    sound = '-sound deafult'
    os.system('terminal-notifier {}'.format(' '.join([m, t, s, sound])))           #post the notification to the computer
    return

def clean(affiliation):
    return re.sub(r'[\d\s]+[a-zA-Z]?grid.?[\d\s.]+[a-z]?[\d\s]*[a-z]?','',affiliation)

def clean_affiliations(data, col1, col2, col3, col4, col5):
    data[col1]= data[col1].astype(str)
    data[col1]= data[col1].apply(clean)
    data[col2]= data[col2].astype(str)
    data[col2]= data[col2].apply(clean)
    data[col3]= data[col3].astype(str)
    data[col3]= data[col3].apply(clean)
    data[col4]= data[col4].astype(str)
    data[col4]= data[col4].apply(clean)
    data[col5]= data[col5].astype(str)
    data[col5]= data[col5].apply(clean)

def get_abstracts_in_german(id_txtfile):
    german_dict = {}
    idlist = list(filter(None, open(id_txtfile).read().splitlines()))
    pmids = [int(i) for i in idlist][1001:]
    print(len(pmids))
    i = 0
    for pmid in pmids:
        start = time.time()
        print(i, '/', str(len(pmids)))
        i += 1
        try:
            s = requests.Session()
            s.mount('https://', HTTPAdapter(max_retries = 5))
            page = s.get('https://pubmed.ncbi.nlm.nih.gov/' + str(pmid) + '/', headers = {'User-agent': 'your bot 0.1'}, timeout =20)
        except (requests.ConnectionError, requests.exceptions.HTTPError):
            time.sleep(15)
            print('Sleeping')
            pass
        page.encoding = 'utf-8-sig'
        soup = BeautifulSoup(page.content, 'lxml')
        ger_abs = soup.find(id = 'de-abstract')
        if ger_abs:
            ger_abs = ger_abs.get_text()
            german_dict[pmid] = ger_abs
            print('Found German Abstract !')
        else:
            print('Running...')
            german_dict[pmid] = ''
        time_taken = time.time() - start
        print('~~~took', time_taken, 's~~~')
    prepared_german_dict = _prepare_dicts(german_dict)    
    df = pd.DataFrame.from_dict(prepared_german_dict, orient='index', columns=['PMID','GERMAN'] )
    print(df.shape)
    df.to_csv('german.csv', sep = ',', encoding = 'utf-8-sig', index= False)
    return
        

if __name__ == "__main__":
    #ID list path, path where you want the output CSV files, followed by the term name
    get_pmcid_master(sys.argv[1], sys.argv[2], sys.argv[3])

    #combine_csv('/Users/pavanbhat/Desktop/test/temp', '/Users/pavanbhat/Desktop/titles.csv')
    """same as output path from first function, then specify where you want the combined CSV and what name it should be
    ####***** if on a MAC just use *****###
    awk 'FNR==1 && NR!=1{next;}{print}' *.csv >merged.csv
    make sure your current directory is the folder with the CSVs""" 
    #get_abstracts_in_german('/Users/pavanbhat/Desktop/NIST MML/german.txt')
