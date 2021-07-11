#!/usr/bin/python3
import numpy as np
import pandas as pd
import os
import re
import sys

sys.path.append(os.getcwd()+"/scripts/")
from pathlib import Path
import datetime
import warnings
from gb_lib import rename_box_type, process_day, process_week
from datetime import date, timedelta

warnings.filterwarnings('ignore')
# disables jedi
%config Completer.use_jedi = False
pd.set_option('precision', 0)



# setup (later automate)
#days = ["TUE", "WED", "THU"]
method = "weekly"

days = ["THU"]
week = 25
year = 2021
# ignore this week
ignore = ["LF"] # ["NP", "LF", "GF"]
week_path = 'data/'+str(year)+'/CW'+str(week)+'/'

# if doesn't exist create extra files folder
if not os.path.exists(week_path+'extra_files/'):
    os.mkdir(week_path+'extra_files/')

print(os.getcwd())
if method == "daily":
    for day in days:
        df, df_dup, df_min, df_viz, df_extra, df_extra_min, df_expected, df_till, df_fornextday = process_day(day, week, year,  ignore=ignore)


        ## PRINT summary of a given day (optimoroute_summarized)
        print("DAY: "+day)
        # total counts
        majtypes = ["VEGAN", "VG", "OMNI"]

        # counts including specials
        df_min["TYPE"] = df_min["TYPE"].str.replace(re.escape(" (1st box)"),"")
        df_min["TYPE"] = df_min["TYPE"].str.split("+").str[0].str.rstrip(" ")
        df_min["Number"] = df_min["Email"]
        sdf = df_min.groupby(by=["TYPE"]).count()["Number"]
        total_boxes = sdf.sum()
        for tp in majtypes:
            sdf = sdf.append(pd.Series(df_min["TYPE"].str.contains(tp).sum(), index=[tp+" TOTAL"]))
            print(tp +" boxes: "+str(df_min["TYPE"].str.contains(tp).sum()))
        sdf =sdf.append(pd.Series(total_boxes, index=["TOTAL"]))
        sdf.to_csv(week_path+'boxes_type_count_'+day+'_CW'+str(week)+'.csv')


        #print(sdf)
        import plotly.graph_objects as go
        fig = go.Figure(data=[go.Table(
            header=dict(values=list(["Box Type (WK "+ str(week) + ", "+ day +")", "Number"]),
                        fill_color='paleturquoise',
                        align='left'),
            cells=dict(values=[sdf.index, sdf],
                       fill_color='lavender',
                       align='left'))
        ])

        fig.show()

        print("")

        print("---END---")
elif method == "weekly":
    df, df_extra, df_extra_min, df_dup, df_dpd = process_week(week, year, method="local", ignore=ignore)
