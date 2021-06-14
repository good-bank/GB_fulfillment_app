import numpy as np
import pandas as pd
import os
import re
import sys
import base64
sys.path.append(os.getcwd()+"scripts/")
from pathlib import Path
#from datetime import date, timedelta
import datetime as dt
import streamlit as st

### methods ##########################################

def get_table_download_link_csv(df, namestr):
    #csv = df.to_csv(index=False)
    csv = df.to_csv(index=False).encode()
    #b64 = base64.b64encode(csv.encode()).decode()
    b64 = base64.b64encode(csv).decode()
    href = f'<a href="data:file/csv;base64,{b64}" download="'+namestr+'.csv">Download '+ namestr +' file</a>'

    #href = f'<a href="data:file/csv;base64,{b64}">Download CSV File</a> (right-click and save as &lt;some_name&gt;.csv)'


    return href

def rename_box_type(df, incol, outcol):
    # re-code the box type variable item 33
    df[outcol] = df[outcol].replace({"OMNIVORE": "OMNI", "Omnivor (Fleisch / Fisch)": "OMNI", "OMNIE": "OMNI", "Vegetarisch": "VG", "VEGGIE": "VG", "Vegan":"VEGAN"})

    # add specials
    df[incol] = df[incol].fillna('')

    idx  = (df[incol].str.contains("Glutenfrei"))
    df[outcol][idx] = df[outcol][idx].astype(str)+" GF"

    idx  = ((df[incol].str.contains("Laktosefrei")) & ~(df[outcol].str.contains("VEGAN")))
    df[outcol][idx] = df[outcol][idx].astype(str)+" LF"

    idx  = (df[incol].str.contains("Ohne Schweinefleisch") & (df[outcol].str.contains("OMNI")))
    df[outcol][idx] = df[outcol][idx].astype(str)+" NP"

    # add 1st box
    idx = (df["type"] == "new")
    df[outcol][idx] = df[outcol][idx].astype(str)+" (1st box)"

    # when there are more than one box add the number of boxes to the front
    idx = df["quantity"].astype('int') > 1
    df[outcol][idx] = df["quantity"][idx].astype('int').astype('str') + " " + df[outcol][idx]
    return df

def process_duplicates(day, week, year, df, method="local"):
    # check for duplicates
    # recharge customer id
    df_dup = pd.DataFrame()
    if df["recharge customer id"].duplicated().any():
        print("Found duplicates by customer id:")
        print(df["recharge customer id"].loc[df["recharge customer id"].duplicated()])
        dupids = df["recharge customer id"].loc[df["recharge customer id"].duplicated()]
        df_dup = df.loc[df["recharge customer id"].isin(np.array(dupids)),:]

        #df_dup = df.loc[df["recharge customer id"].isin([df["recharge customer id"].loc[df["recharge customer id"].duplicated()]),:]
        print("Review to see duplicates:  extra_files/review_duplicates_"+day+"_CW"+str(week)+".csv")
        if method=="local":
            week_path = 'data/'+str(year)+'/CW'+str(week)+'/'
            df_dup.to_csv(week_path+'extra_files/review_duplicates_'+day+'_CW'+str(week)+'.csv', index=False)
        #print("Keeping entry that says 1st box + any EXTRA items")
        print("Keeping all duplicates - review manually!")
        # in duplicates keep the one that has 1st box OR if it's "extraitem"

        #idx = (~(df["recharge customer id"].isin(np.array(dupids)) & ~(df["variant title"].str.contains('(1st box)')))) | (df["item sku"].isin(["extraitem"]))
        #df= df.loc[idx,:]
    return df, df_dup

def process_extra_items(df):
    # EXTRA ITEM
    id = df["recharge customer id"].loc[df["item sku"].isin(["extraitem"])]
    if len(id)==0:
        extra_items = 0
    else:
        extra_items = 1
    for i in id:
        sz = df.loc[df["recharge customer id"].isin([i]) & df["item sku"].isin(["extraitem"]),]
        # number of extra items
        noextra = sz["quantity"].sum()

        # append how many extra items
        idd = (~df["item sku"].isin(["extraitem"]) & df["recharge customer id"].isin([i])) & ~(df["variant title"].str.contains(" x EXTRA ITEM"))
        df["variant title"][idd] = df["variant title"][idd]+" + " +str(int(noextra))+ " x EXTRA ITEM(S)"
        df["variant title"][df["item sku"].isin(["extraitem"])] = df["quantity"].astype('int').astype('str') + " EXTRA ITEM"

    # create a sheet of extra items
    df_extra=pd.DataFrame()
    df_extra_min=pd.DataFrame()
    extra_ids = id.unique()
    for i in extra_ids:
        idd = df["recharge customer id"].isin([i])
        df_extra = pd.concat([df_extra, df.loc[idd,:]]).reset_index().drop(columns=["level_0"])

        # drop extra item from the main data
        idd2 = df["recharge customer id"].isin([i]) & df["item sku"].isin(["extraitem"])
        df=df.loc[~idd2,:]
    return df, df_extra, df_extra_min, extra_items


### process_day ######################
def process_day(day, week, year, method="local", ignore=[],  new_raw=pd.DataFrame(), recurr_raw=pd.DataFrame(), df_prev=pd.DataFrame()):

    #method can be "local" or "streamlit"
    week_path = 'data/'+str(year)+'/CW'+str(week)+'/'
    print("---"+day+"---")
    # infer date
    for d, did in {"MON":"1", "TUE":"2", "WED":"3", "THU":"4", "FRI":"5" }.items():
        if d == day:
            day_no = did
    today = dt.datetime.strptime(str(year)+ '-W' + str(week) + '-' + day_no, "%Y-W%W-%w")
    print('Inferred date: '+str(today))

    ### PREPARE FILE OF NEW ORDERS
    # read the "processed" file and filter for new orders
    if method=="local":
        new_raw = pd.read_csv(week_path+'processed_'+day+'_CW'+str(week)+'.csv')
    elif method=="streamlit":
        new_raw = pd.read_csv(new_raw)
    df_new = new_raw.loc[new_raw['charge type']=="Subscription First Order",:]
    df_new["type"] = "new"


    # check if data got saved with "LOCAL DELIVERY" and merge the two created lines
    if df_new["product title"].str.contains("LOCAL DELIVERY").any():
        print("LOCAL DELIVERY found - please check!")
        temp = np.array(df_new.loc[df_new["product title"].str.contains("LOCAL DELIVERY")]["recharge customer id"])
        for id in temp:
            idxs = np.where(df_new["recharge customer id"].isin([id]))[0]
            print(idxs)
            if len(idxs)>2:
                print("In LOCAL DELIVERY, more than 2 lines of the same ID!")
            else:
                move_vars = ["product title", "variant title", "line_item_properties"]
                for mv in move_vars:
                    df_new = df_new.reset_index(drop=True);
                    df_new[mv][idxs[0]] = df_new[mv][idxs[1]]
                df_new = df_new.drop(index=idxs[1], axis=0).reset_index(drop=True)


    # filter for current and past day in this week
    for d, did in {"MON":"Montag", "TUE":"Dienstag", "WED":"Mittwoch", "THU":"Donnerstag", "FRI":"Freitag" }.items():
        if d == day:
            day_str = did

    # for all days exclude people who ordered the box for upcoming days
    days = np.array(["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag"])
    days_eng =np.array(["MON", "TUE", "WED", "THU", "FRI"])
    result = np.where(days == day_str)
    df_new["line_item_properties"] = df_new["line_item_properties"].fillna('')
    key = np.empty((df_new.shape[0]))
    for idx, i in enumerate(df_new["line_item_properties"]):
        key[idx] = any(ele in i for ele in days[0:result[0][0]+1])

    # save the new orders expected through the rest of the week
    df_expected=df_new.loc[key==0,:]
    df_expected = rename_box_type(df_expected, "line_item_properties", "variant title")

    # and now throw away the orders for next days
    df_new=df_new.loc[key==1,:]

    # remove national orders
    idx = ~(df_new["product title"].str.contains("National"))
    df_new = df_new.loc[idx,:]

    # if this is TUE (first day of the week, just take all orders in the file with delivery day up till this point)
    if day=="TUE":
        df_new = rename_box_type(df_new, "line_item_properties", "variant title")
        if method=="local":
            df_new.to_csv(week_path+'collected_processed_until'+day+'_CW'+str(week)+'.csv', index=False)
            df_new.to_csv(week_path+'extra_files/collected_processed_only'+day+'_CW'+str(week)+'.csv', index=False)
        df_till = df_new
        df_fornextday = df_new
    # if it's not TUE then load the previous day and check fo already completed orders
    else:
        yesterday = np.where(days_eng==day)
        if method=="local":
            df_prev = pd.read_csv(week_path+'collected_processed_until'+days_eng[yesterday[0]-1][0]+'_CW'+str(week)+'.csv')
        elif method=="streamlit":
            df_prev = pd.read_csv(df_prev)
        # merge previous and new using indicator=True
        df_new.to_csv(week_path+'test1.csv', index=False)
        df_prev.to_csv(week_path+'test2.csv', index=False)
        if (df_prev.shape[0] is not 0) and (df_new.shape[0] is not 0):
            df_new = df_new.merge(df_prev, on='external order number', how='outer', suffixes=['', '_extra'], indicator=True)
            #df_new = df_new.merge(df_prev, on='shopify order number', how='outer', suffixes=['', '_extra'], indicator=True)

            df_new = df_new.loc[:,~df_new.columns.str.contains('_extra', case=False)]
            df_new.loc[:,~df_new.columns.str.contains('Unnamed', case=False)]
            df_new = df_new.loc[df_new["_merge"]=="left_only",:]
            df_new = df_new.drop(["_merge"], axis=1)

        # rename box type
        df_new = rename_box_type(df_new, "line_item_properties", "variant title")
        if method=="local":
            df_new.to_csv(week_path+'extra_files/collected_processed_only'+day+'_CW'+str(week)+'.csv', index=False)


        # record all completed orders till now
        df_till = df_prev.append(df_new, ignore_index=True)
        df_fornextday = df_till
        if method=="local":
            df_till.to_csv(week_path+'collected_processed_until'+day+'_CW'+str(week)+'.csv', index=False)


    ### PREPARE FILE OF RECURRING ORDERS
    # read the "upcoming" file and select the upcoming date
    if method=="local":
        recurr_raw = pd.read_csv(week_path+'upcoming_'+day+'_CW'+str(week)+'.csv')
    elif method=="streamlit":
        recurr_raw = pd.read_csv(recurr_raw)
    recurr_raw["charge date"]=pd.to_datetime(recurr_raw["charge date"])

    # on TUE also check if there are any orders charged on Monday, Sunday or Saturday
    if day == "TUE":
        predates = pd.date_range(today-dt.timedelta(days=3), today,freq='d')
        df_recurr = recurr_raw.loc[recurr_raw["charge date"].isin(predates),:]
    else:
        df_recurr = recurr_raw.loc[recurr_raw["charge date"]==today,:]
    df_recurr["type"] = "recurring"
    df_recurr["line item properties"] = df_recurr["line item properties"].fillna("")
    df_recurr["variant title"] = df_recurr["variant title"].fillna("")

    # remove national orders
    idx = ~(df_recurr["product title"].str.contains("National"))
    df_recurr = df_recurr.loc[idx,:]

    # rename bo type and shorten
    df_recurr = rename_box_type(df_recurr, "line item properties", "variant title")

    ### MERGE THE TWO PREPARED FILES
    # unify headers before merge (teh headers are similar but not the same - possible to change in the recharge system?)
    df_new = df_new.rename(columns={"charged date": "charge date", "total amount": "amount", "line_item_properties":"line item properties"})

    # merge data for new and recurring orders
    #print(df_new.columns)
    #print(df_recurr.columns)
    df = pd.concat([df_new, df_recurr]).reset_index()
    df["processed_on"] = day
    df["item sku"] = df["item sku"].fillna("")
    df["variant title"] = df["variant title"].fillna("")

    # check for duplicates
    df, df_dup = process_duplicates(day, week, year, df, method=method)

    # check for extra items
    df, df_extra, df_extra_min, extra_items = process_extra_items(df)

    # remove types of boxes that are not featured this week
    for ig in ignore:
        idx = df["variant title"].str.contains(ig)
        df["variant title"][idx] = df["variant title"][idx].str.replace(" "+ig,"")


    ############################################################
    # Filter and rename items
    #output_columns = ["Email", "First Name", "Location name", "Address", "Notes", "ZIP", "PHONE", "TYPE", "DELIVERY DATE + INFOS"]
    output_columns = ["Email", "First Name", "Location name", "Address", "Notes", "ZIP", "TYPE", "DELIVERY DATE + INFOS"]
    rename_key = {"email": "Email", "shipping first name": "First Name", "shipping last name": "Location name",
                                "shipping address 1": "Address", "shipping address 2": "Notes", "shipping postal code": "ZIP",
                                "shipping phone": "PHONE",  "variant title": "TYPE", "line item properties": "DELIVERY DATE + INFOS"}

    # rename key headers and shave data frame off
    df = df.rename(columns=rename_key)

    # save full spreadsheet
    if method=="local":
        df.to_csv(week_path+'extra_files/optimoroute_'+day+'_CW'+str(week)+'_all_columns.csv', index=False)

    # keep only selected columns
    df_min = df.loc[:,output_columns]
    if method=="local":
        df_min.to_csv(week_path+'optimoroute_'+day+'_CW'+str(week)+'.csv', index=False)

    # only creates the manual file if it doesn't already exist
    if method=="local":
        if not os.path.exists(week_path+'optimoroute_'+day+'_CW'+str(week)+'_man.csv'):
            df_min.to_csv(week_path+'optimoroute_'+day+'_CW'+str(week)+'_man.csv', index=False)

    # save extra items as separate sheet
    if extra_items == 1:
        df_extra= df_extra.loc[:,["charge date", "quantity", "shipping first name", "shipping last name", "email", "product title", "variant title"]]
        if method=="local":
            df_extra.to_csv(week_path+'extra_items_'+day+'_CW'+str(week)+'.csv', index=False)
        #df_extra["name"] = df_extra["shipping first name"] + df_extra["shipping last name"]
        df_extra_min = df_extra.loc[:,["shipping last name", "product title", "quantity", "email", "shipping first name"]]
        if method=="local":
            df_extra_min.to_csv(week_path+'extra_items_PRINTABLE_'+day+'_CW'+str(week)+'.csv', index=False)

    # save NEW orders that are coming up in the upcoming days
    # get orders till today
    df_till = df_till.rename(columns={"charged date": "charge date", "total amount": "amount", "line_item_properties":"line item properties"})
    #df_till.columns
    #get new orders for upcoming days
    df_expected = df_expected.rename(columns={"charged date": "charge date", "total amount": "amount", "line_item_properties":"line item properties"})
    df_expected = df_expected.rename(columns=rename_key)
    # merge the two
    df_expected = pd.concat([df_expected.loc[:,output_columns], df_till.rename(columns=rename_key).loc[:,output_columns]])
    # polish the INFO column
    for d, deng in zip(days,days_eng):
        idx = df_expected["DELIVERY DATE + INFOS"].str.contains(d)
        df_expected["DELIVERY DATE + INFOS"][idx] = deng

    if method=="local":
        df_expected.to_csv(week_path+'collected_processed_upcoming_days_'+day+'_CW'+str(week)+'.csv', index=False)




    # also, Laiza wanted to have a backup every time the script generates a new file
    if method=="local":
        i = 0
        cond = False
        while not cond:
            i += 1
            if not os.path.exists(week_path+'extra_files/optimoroute_'+day+'_CW'+str(week)+'_'+str(i)+'.csv'):
                df_min.to_csv(week_path+'extra_files/optimoroute_'+day+'_CW'+str(week)+'_'+str(i)+'.csv', index=False)
                cond=True




    df_viz = df
    return df, df_dup, df_min, df_viz, df_extra, df_extra_min, df_expected, df_till, df_fornextday

def process_week(week, year, method="local", ignore=[],  new_raw=pd.DataFrame(), recurr_raw=pd.DataFrame()):
    if method=="local":
            week_path = 'data/'+str(year)+'/CW'+str(week)+'/'
    today = dt.datetime.strptime(str(year)+ '-W' + str(week) + '-2', "%Y-W%W-%w")
    st.markdown('---')
    st.markdown('Generating data for dates: **'+(today-dt.timedelta(days=6)).strftime('%Y-%b-%d')+'** until **'+today.strftime('%Y-%b-%d')+'**')
    #predates = pd.date_range(today-dt.timedelta(days=3), today,freq='d')
    #df_recurr = recurr_raw.loc[recurr_raw["charge date"].isin(predates),:]

    # read NEW orders
    if method=="local":
        new_raw = pd.read_csv(week_path+'processed_week_CW'+str(week)+'.csv')
    elif method=="streamlit":
        new_raw = pd.read_csv(new_raw)
    df_new = new_raw.loc[new_raw['charge type']=="Subscription First Order",:]
    df_new = df_new.rename(columns={"charged date": "charge date", "total amount": "amount", "line_item_properties":"line item properties"})
    df_new["type"] = "new"

    # read recurring orders
    if method=="local":
        recurr_raw = pd.read_csv(week_path+'upcoming_week_CW'+str(week)+'.csv')
    elif method=="streamlit":
        recurr_raw = pd.read_csv(recurr_raw)
    recurr_raw["type"] = "recurring"

    # merge them
    df = pd.concat([df_new, recurr_raw]).reset_index()
    df["item sku"] = df["item sku"].fillna("")
    df["variant title"] = df["variant title"].fillna("")
    df["line item properties"] = df["line item properties"].fillna("")

    # select dates used for analysis
    predates = pd.Series(pd.date_range(today-dt.timedelta(days=6), today,freq='d')).apply(lambda x: x.strftime('%Y-%m-%d'))
    df["charge date"]=pd.to_datetime(df["charge date"]).dt.strftime('%Y-%m-%d')
    df = df.loc[df["charge date"].isin(predates),:]

    # select ONLY the National orders in "product title"
    df = df.loc[df["product title"].str.contains("National"),:]
    df.to_csv(week_path+'test_filtered.csv', index=False)

    # check for duplicates
    df, df_dup = process_duplicates(day, week, year, df, method=method)

    # check for extra items
    df, df_extra, df_extra_min, extra_items = process_extra_items(df)

    # remove types of boxes that are not featured this week
    for ig in ignore:
        idx = df["variant title"].str.contains(ig)
        df["variant title"][idx] = df["variant title"][idx].str.replace(ig,"")

    return df, df_extra, df_extra_min, df_dup





######################################################
