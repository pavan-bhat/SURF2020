# SURF2020
### By: Pavan Bhat <pavan.bhat@nist.gov>

##### This project was developed for the NIST SURF Program, Summer of 2020.
It includes various programs for 
- getting the abstracts from PMCIDs 
- Formatting the metadata output for easy databse imports
- Formatting R&R Outputs
- Getting Abstracts from PMIDs
- Getting Abstracts from Springer Link
- Getting Spanish and English Abstracts from scielo

## Getting Abstracts From a list of PMCIDs

> 1. To start, go to the [PubMed Central Website](https://www.ncbi.nlm.nih.gov/pmc/)
> 2. Then, type in a term you want to search. You can also filter by year, author, etc. Keep in mind that the more results you get the longer it will take for the next steps, so breaaking up into smaller chunks is recommended.

It should look something like **this**

![PMC Homepage](pmc_hompeag.png "Pubmed Central Homepage")

&nbsp;  


> 3. Now we will get the PMCIDs from the website by clicking on the *Send to* button as shown below

![PMC Send to File](Send_To_FIle.png "How to Send Results to File")

The resulting file (*it may take a while to download*) should have the format:

```
PMC12345
PMC23456
PMC987654
```

#### Getting Abstracts

> 4. Now that we have the list of PMCIDs, we are ready to use the program ***pmc.py***. However, first make sure to download the dependencies.

The dependecies required are listen in requirments.txt navigate to the file in your terminal and run
``` pip install -r requirements.txt ```


