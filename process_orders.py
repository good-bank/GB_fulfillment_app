import pandas as pd
import numpy as np
import os
import sys
import datetime
import warnings
warnings.filterwarnings('ignore')

# disables jedi
%config Completer.use_jedi = False
print(os.getcwd())

# setup (later automate)
day = "THU"
week = 8
year = 2021
week_path = 'data/'+str(year)+'/CW'+str(week)+'/'

# infer date
for d, did in {"MON":"1", "TUE":"2", "WED":"3", "THU":"4", "FRI":"5" }.items():
    if d == day:
        day_no = did
today = datetime.datetime.strptime(str(year)+ '-W' + str(week) + '-' + day_no, "%Y-W%W-%w")
print('Inferred date: '+str(today))

### PREPARE FILE OF NEW ORDERS
# read the "processed" file and filter for new orders
new_raw = pd.read_csv(week_path+'processed_'+day+'_CW'+str(week)+'.csv')
df_new = new_raw.loc[new_raw['charge type']=="Subscription First Order",:]
df_new["type"] = "new"

# filter for current and past day in this week
for d, did in {"MON":"Montag", "TUE":"Dienstag", "WED":"Mittwoch", "THU":"Donnerstag", "FRI":"Freitag" }.items():
    if d == day:
        day_str = did

days = np.array(["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag"])
result = np.where(days == day_str)

key = np.empty((df_new.shape[0]))
for idx, i in enumerate(df_new["line_item_properties"]):
    key[idx] = any(ele in i for ele in days[0:result[0][0]+1])
df_new=df_new.loc[key==1,:]




### PREPARE FILE OF RECURRING ORDERS
# read the "upcoming" file and select the upcoming date
recurr_raw = pd.read_csv(week_path+'upcoming_'+day+'_CW'+str(week)+'.csv')
recurr_raw["charge date"]=pd.to_datetime(recurr_raw["charge date"])
df_recurr = recurr_raw.loc[recurr_raw["charge date"]==today,:]
df_recurr["type"] = "recurring"


### MERGE THE TWO PREPARED FILES
# unify headers before merge (teh headers are similar but not the same - possible to change in the recharge system?)
df_new = df_new.rename(columns={"charged date": "charge date", "total amount": "amount", "line_item_properties":"line item properties"})
# merge data for new and recurring orders
df = pd.concat([df_new, df_recurr]).reset_index()
df.to_csv(week_path+'raw_merged_file.csv')
# check for duplicates
# recharge customer id
if df["recharge customer id"].duplicated().any():
    print("Found duplicates! Keeping first entry")
    df=df.drop_duplicates(subset=["recharge customer id"])



############################################################
# Filter and rename items
output_columns = ["Email", "First Name", "Location name", "Address", "Notes", "ZIP", "PHONE", "TYPE", "DELIVERY DATE + INFOS"]

# item 27 - checking for local delivery in "product title"
# INSTRUCTION: Check for all "local delivery" rows as a duplicate to the Good Farm Box order rows.
# Copy here only the type of box of (column F) and line properties (column AQ) of the Good Farm Box
# order row to this one, and delete the Good Farm Box order row.
if df["product title"].isin(["local delivery"]).any():
    print('There is a local delivery value, but the scirpt doesnt filter it yet')
else:
    print("The script isn't equipped to deal with 'local delivery', check 'data/raw_merged_file.csv' if there is any and talk to Ondrej")

# rename key headers and shave data frame off
df = df.rename(columns={"email": "Email", "shipping first name": "First Name", "shipping last name": "Location name",
                            "shipping address 1": "Address", "shipping address 2": "Notes", "shipping postal code": "ZIP",
                            "shipping phone": "PHONE",  "variant title": "TYPE", "line item properties": "DELIVERY DATE + INFOS"})

# re-code the box type variable item 33
df["TYPE"] = df["TYPE"].replace({"OMNIVORE": "OMNI", "Omnivor (Fleisch / Fisch)": "OMNI", "OMNIE": "OMNI", "Vegetarisch": "VG", "VEGGIE": "VG", "Vegan":"VEGAN"})

# add specials
idx  = (df["DELIVERY DATE + INFOS"].str.contains("Laktosefrei")) & (df["TYPE"] != "VEGAN")
df["TYPE"][idx] = df["TYPE"][idx].astype(str)+" LF"

idx  = (df["DELIVERY DATE + INFOS"].str.contains("Glutenfrei"))
df["TYPE"][idx] = df["TYPE"][idx].astype(str)+" GF"

idx  = (df["DELIVERY DATE + INFOS"].str.contains("Ohne Schweinefleisch")) & (df["TYPE"] != "VEGAN") & (df["TYPE"] != "VG")
df["TYPE"][idx] = df["TYPE"][idx].astype(str)+" NP"

# add 1st box
idx = (df["type"] == "new")
df["TYPE"][idx] = df["TYPE"][idx].astype(str)+" (1st box)"



df.to_csv(week_path+'output.csv')

# only selected columns
df_min = df.loc[:,output_columns]
df_min.to_csv(week_path+'optimoroute_'+day+'_CW'+str(week)+'.csv', index=False)
