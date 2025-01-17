import streamlit as st
import pandas as pd
import numpy as np
import base64
import sys, os, re
sys.path.append(os.getcwd()+"/scripts/")
from gb_lib import rename_box_type, process_day, process_week, get_table_download_link_csv

import datetime
my_date = datetime.date.today()
year, week_num, day_of_week = my_date.isocalendar()

task = st.sidebar.radio('Select',['Regular (daily)', 'National orders (weekly)'])


if task=="Regular (daily)":
    ### settings
    st.sidebar.markdown('#### Select week, year and day')
    week = int(st.sidebar.number_input('Week number (e.g.: 16):',week_num, format='%.0f'))
    year = st.sidebar.number_input('Year (e.g.: 2021):', 2021, format='%.0f')
    day = st.sidebar.selectbox('Select a day', ['TUE','WED'])#,'THU', 'FRI'])
    ignore = st.sidebar.multiselect('Which box type to not consider this week', ['NP', 'LF', 'GF'])
    st.sidebar.markdown('---')


    upcoming = st.sidebar.file_uploader("Select \"upcoming_"+day+"_CW"+str(week)+".csv\" file")
    processed = st.sidebar.file_uploader("Select \"processed_"+day+"_CW"+str(week)+".csv\" file")

    if not (str(day)=="TUE"):
        days_eng =np.array(["MON", "TUE", "WED", "THU", "FRI"])
        yesterday = np.where(days_eng==day)
        st.sidebar.markdown('\* The `collected_processed_until` file needs to be the one you downloaded yesterday')
        coll_proc_until = st.sidebar.file_uploader("Select \"collected_processed_until"+days_eng[yesterday[0]-1][0]+"_CW"+str(week)+".csv\" file")
    elif day=="TUE":
        coll_proc_until = []

    if (upcoming is not None) and (processed is not None) and (coll_proc_until is not None):
        #df = pd.read_csv(upl)
        #st.dataframe(df)

        df, df_dup, df_min, df_viz, df_extra, df_extra_min, df_expected, df_till, df_fornextday = process_day(day, week, year, method="streamlit", ignore=ignore,  new_raw=processed, recurr_raw=upcoming, df_prev=coll_proc_until)

        ## PRINT summary of a given day (optimoroute_summarized)
        print("DAY: "+day)
        # total counts
        # streamlit has a serious bug/feature here, if one assigns a DF ANYWHERE in codo to another df,
        # and then makes changes, the MOTHER DF will also be changed
        majtypes = ["VEGAN", "VG", "OMNI"]
        # counts including specials
        df_viz["TYPE"] = df_viz["TYPE"].str.replace(re.escape(" (1st box)"),"")
        df_viz["TYPE"] = df_viz["TYPE"].str.split("+").str[0].str.rstrip(" ")
        df_viz["Number"] = df_viz["Email"]
        sdf = df_viz.groupby(by=["TYPE"]).count()["Number"]
        total_boxes = sdf.sum()
        for tp in majtypes:
                sdf = sdf.append(pd.Series(df_viz["TYPE"].str.contains(tp).sum(), index=[tp+" TOTAL"]))
                st.markdown(tp +" boxes: "+str(df_min["TYPE"].str.contains(tp).sum()))
        sdf =sdf.append(pd.Series(total_boxes, index=["TOTAL"]))

        import plotly.graph_objects as go
        fig = go.Figure(data=[go.Table(
            header=dict(values=list(["Box Type (WK "+ str(week) + ", "+ day +")", "Number"]),
                        fill_color='paleturquoise',
                        align='left'),#
            cells=dict(values=[sdf.index, sdf],
                       fill_color='lavender',
                       align='left'))
        ])
        st.plotly_chart(fig)

        st.markdown('**Duplicate entries**')
        st.dataframe(df_dup)

    #dwnld = st.button('Download optimoroute')
    #if (dwnld):
        st.markdown(get_table_download_link_csv(df_min, 'optimoroute_'+day+'_CW'+str(week)), unsafe_allow_html=True)
        st.markdown(get_table_download_link_csv(df_extra_min, 'extra_items_PRINTABLE_'+day+'_CW'+str(week)), unsafe_allow_html=True)
        st.markdown(get_table_download_link_csv(df_fornextday, 'collected_processed_until'+day+'_CW'+str(week)), unsafe_allow_html=True)

elif task=="National orders (weekly)":
    week = int(st.sidebar.number_input('This week number (e.g.: 16):',week_num, format='%.0f'))
    year = st.sidebar.number_input('Year (e.g.: 2021):', 2021, format='%.0f')
    ign_wk = st.sidebar.multiselect('Which box type to not consider this week', ['NP', 'LF', 'GF'])
    upc_wk = st.sidebar.file_uploader("Select \"upcoming_nationals_\" since last Wednesday")
    proc_wk = st.sidebar.file_uploader("Select \"processed_nationals_\" since last Wednesday")
    st.markdown('### Notice')
    st.markdown('The weekly script assumes that the processed days are from last Tuesday (Mon/Tue midnight) until Monday of the present week.')
    if (upc_wk is not None) and (proc_wk is not None) :
        df, df_extra, df_extra_min, df_dup, df_dpd = process_week(week, year, method="streamlit", ignore=ign_wk,  new_raw=proc_wk, recurr_raw=upc_wk)

        majtypes = ["VEGAN", "VG", "OMNI"]

        # counts including specials
        df["variant title"] = df["variant title"].str.replace(re.escape(" (1st box)"),"")
        df["variant title"] = df["variant title"].str.split("+").str[0].str.rstrip(" ")
        df["Number"] = df["email"]
        sdf = df.groupby(by=["variant title"]).count()["Number"]
        total_boxes = sdf.sum()
        for tp in majtypes:
            sdf = sdf.append(pd.Series(df["variant title"].str.contains(tp).sum(), index=[tp+" TOTAL"]))
            print(tp +" boxes: "+str(df["variant title"].str.contains(tp).sum()))
        sdf =sdf.append(pd.Series(total_boxes, index=["TOTAL"]))

        import plotly.graph_objects as go
        fig = go.Figure(data=[go.Table(
            header=dict(values=list(["Nationals, Box Type (WK "+ str(week) +")", "Number"]),
                        fill_color='paleturquoise',
                        align='left'),
            cells=dict(values=[sdf.index, sdf],
                       fill_color='lavender',
                       align='left'))
        ])

        st.plotly_chart(fig)

        st.markdown('**Duplicate entries (in the DPD file, only the one from "processed" is kept)**')
        st.dataframe(df_dup)
        st.markdown(get_table_download_link_csv(df_dpd, 'DPD_nationals_CW'+str(week)), unsafe_allow_html=True)
        st.markdown(get_table_download_link_csv(df_extra_min, 'nationals_extra_items_PRINTABLE_CW'+str(week)), unsafe_allow_html=True)


    #st.markdown(get_table_download_link_csv(df_min, 'optimoroute_'+day+'_CW'+str(week)), unsafe_allow_html=True)
    #st.markdown(get_table_download_link_csv(df_extra_min, 'extra_items_PRINTABLE_'+day+'_CW'+str(week)), unsafe_allow_html=True)
    #st.markdown(get_table_download_link_csv(df_fornextday, 'collected_processed_until'+day+'_CW'+str(week)), unsafe_allow_html=True)
