import pandas as pd
import numpy as np
import os
import sys
from pathlib import Path
import datetime
import warnings
warnings.filterwarnings('ignore')
# disables jedi
%config Completer.use_jedi = False


### methods ##########################################
def rename_box_type(df, incol, outcol):
    # re-code the box type variable item 33
    df[outcol] = df[outcol].replace({"OMNIVORE": "OMNI", "Omnivor (Fleisch / Fisch)": "OMNI", "OMNIE": "OMNI", "Vegetarisch": "VG", "VEGGIE": "VG", "Vegan":"VEGAN"})

    # add specials
    df[incol] = df[incol].fillna('')

    idx  = (df[incol].str.contains("Laktosefrei")) & (df[outcol] != "VEGAN")
    df[outcol][idx] = df[outcol][idx].astype(str)+" LF"

    idx  = (df[incol].str.contains("Glutenfrei"))
    df[outcol][idx] = df[outcol][idx].astype(str)+" GF"

    idx  = (df[incol].str.contains("Ohne Schweinefleisch")) & (df[outcol] != "VEGAN") & (df[outcol] != "VG")
    df[outcol][idx] = df[outcol][idx].astype(str)+" NP"

    # add 1st box
    idx = (df["type"] == "new")
    df[outcol][idx] = df[outcol][idx].astype(str)+" (1st box)"
    return df

######################################################


print(os.getcwd())

# setup (later automate)
#days = ["TUE", "WED", "THU", "FRI"]
days = ["WED"]
week = 13
year = 2021
week_path = 'data/'+str(year)+'/CW'+str(week)+'/'

for day in days:
    print("---"+day+"---")
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

    # for all days exclude people who ordered the box for upcoming days
    days = np.array(["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag"])
    result = np.where(days == day_str)
    df_new["line_item_properties"] = df_new["line_item_properties"].fillna('')
    key = np.empty((df_new.shape[0]))
    for idx, i in enumerate(df_new["line_item_properties"]):
        key[idx] = any(ele in i for ele in days[0:result[0][0]+1])
    df_new=df_new.loc[key==1,:]

    # check if data got saved with "LOCAL DELIVERY" and merge the two created lines
    if df_new["product title"].isin(["LOCAL DELIVERY - BERLIN ONLY"]).any():
        temp = np.array(df_new.loc[df_new["product title"].isin(["LOCAL DELIVERY - BERLIN ONLY"])]["recharge customer id"])
        for id in temp:
            idxs = np.where(df_new["recharge customer id"].isin([id]))[0]
            print(idxs)
            if len(idxs)>2:
                print("In LOCAL DELIVERY, more than 2 lines of the same ID!")
            else:
                move_vars = ["product title", "variant title", "line_item_properties"]
                for mv in move_vars:
                    df_new[mv][idxs[0]] = df_new[mv][idxs[1]]
                df_new = df_new.drop(index=idxs[1], axis=0)

    # if this is TUE (first day of the week, just take all orders in the file with delivery day up till this point)
    if day=="TUE":
        df_new["processed_on"] = day
        df_new = rename_box_type(df_new, "line_item_properties", "variant title")
        df_new.to_csv(week_path+'collected_processed_until'+day+'_CW'+str(week)+'.csv', index=False)
        df_new.to_csv(week_path+'extra_files/collected_processed_only'+day+'_CW'+str(week)+'.csv', index=False)

    # if it's not TUE then load the previous day and check fo already completed orders
    else:
        days_eng =np.array(["MON", "TUE", "WED", "THU", "FRI"])
        yesterday = np.where(days_eng==day)
        df_prev = pd.read_csv(week_path+'collected_processed_until'+days_eng[yesterday[0]-1][0]+'_CW'+str(week)+'.csv')
        # merge previous and new using indicator=True
        df_new = df_new.merge(df_prev, on='shopify order number', how='outer', suffixes=['', '_extra'], indicator=True)

        df_new = df_new.loc[:,~df_new.columns.str.contains('_extra', case=False)]
        df_new.loc[:,~df_new.columns.str.contains('Unnamed', case=False)]
        df_new = df_new.loc[df_new["_merge"]=="left_only",:]
        df_new = df_new.drop(["_merge"], axis=1)
        df_new["processed_on"] = day
        # rename box type
        df_new = rename_box_type(df_new, "line_item_properties", "variant title")
        df_new.to_csv(week_path+'extra_files/collected_processed_only'+day+'_CW'+str(week)+'.csv', index=False)

        # record all completed orders till now
        df_till = df_prev.append(df_new, ignore_index=True)
        df_till.to_csv(week_path+'collected_processed_until'+day+'_CW'+str(week)+'.csv', index=False)


    ### PREPARE FILE OF RECURRING ORDERS
    # read the "upcoming" file and select the upcoming date
    recurr_raw = pd.read_csv(week_path+'upcoming_'+day+'_CW'+str(week)+'.csv')
    recurr_raw["charge date"]=pd.to_datetime(recurr_raw["charge date"])
    df_recurr = recurr_raw.loc[recurr_raw["charge date"]==today,:]
    df_recurr["type"] = "recurring"
    df_recurr = rename_box_type(df_recurr, "line item properties", "variant title")

    ### MERGE THE TWO PREPARED FILES
    # unify headers before merge (teh headers are similar but not the same - possible to change in the recharge system?)
    df_new = df_new.rename(columns={"charged date": "charge date", "total amount": "amount", "line_item_properties":"line item properties"})
    # merge data for new and recurring orders
    df = pd.concat([df_new, df_recurr]).reset_index()
    # check for duplicates
    # recharge customer id
    if df["recharge customer id"].duplicated().any():
        print("Found duplicates by customer id:")
        print(df["recharge customer id"].loc[df["recharge customer id"].duplicated()])
        print("Review to see duplicates:  extra_files/review_duplicates_"+day+"_CW"+str(week)+".csv")
        df.to_csv(week_path+'extra_files/review_duplicates_'+day+'_CW'+str(week)+'.csv', index=False)
        print("Keeping first entry")
        df=df.drop_duplicates(subset=["recharge customer id"])



    ############################################################
    # Filter and rename items
    output_columns = ["Email", "First Name", "Location name", "Address", "Notes", "ZIP", "PHONE", "TYPE", "DELIVERY DATE + INFOS"]

    # rename key headers and shave data frame off
    df = df.rename(columns={"email": "Email", "shipping first name": "First Name", "shipping last name": "Location name",
                                "shipping address 1": "Address", "shipping address 2": "Notes", "shipping postal code": "ZIP",
                                "shipping phone": "PHONE",  "variant title": "TYPE", "line item properties": "DELIVERY DATE + INFOS"})

    # keep only selected columns
    df_min = df.loc[:,output_columns]
    df_min.to_csv(week_path+'optimoroute_'+day+'_CW'+str(week)+'.csv', index=False)

    # only creates the manual file if it doesn't already exist
    if not os.path.exists(week_path+'optimoroute_'+day+'_CW'+str(week)+'_man.csv'):
        df_min.to_csv(week_path+'optimoroute_'+day+'_CW'+str(week)+'_man.csv', index=False)

    # also, Laiza wanted to have a backup every time the script generates a new file
    i = 0
    cond = False
    while not cond:
        i += 1
        if not os.path.exists(week_path+'extra_files/optimoroute_'+day+'_CW'+str(week)+'_'+str(i)+'.csv'):
            df_min.to_csv(week_path+'extra_files/optimoroute_'+day+'_CW'+str(week)+'_'+str(i)+'.csv', index=False)
            cond=True

    print("---END---")
