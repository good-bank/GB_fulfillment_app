# tool to compare two csv files

import pandas as pd
import numpy as np
import os
# disables jedi
%config Completer.use_jedi = False
print(os.getcwd())
folder = os.getcwd()+'/data/2021/CW13/'
file1 = 'optimoroute_TUE_CW13_man.csv'
file2 = 'Optimoroute_TUE_CW13_Laiza.csv'
# what to compare
variable = 'Email'
# what to show
additional_show_vars = [ "First Name", "Location name"]

df1 = pd.read_csv(folder+file1)
df2 = pd.read_csv(folder+file2)

df = df1.merge(df2, on=variable, how='outer', suffixes=['_file1', '_file2'], indicator=True)
df.to_csv(folder+"merged.csv")
print('Values only in '+file1+': ')
f1vars =  list([variable]) + list([s+"_file1" for s in additional_show_vars])
print(df[f1vars].loc[df["_merge"]=="left_only"])

print('')
print('Values only in '+file2+': ')
f2vars =  list([variable]) + list([s+"_file2" for s in additional_show_vars])
print(df[f2vars].loc[df["_merge"]=="right_only"])

print('')
print('Values in both: ')
f2vars =  list([variable]) + list([s+"_file1" for s in additional_show_vars])
print(df[f2vars].loc[df["_merge"]=="both"])
