import os
import requests
import json
import pandas as pd


headers = {"X-Recharge-Access-Token": "f67c3c620b33afdd59b43e4bcbfa58bf05fd91f76d4232867c15df14"}
url = "https://api.rechargeapps.com/orders?limit=4"

result = requests.get(url, headers=headers)
dt= json.dump(json.loads(result.text), indent=2)
#js = json.loads(result.text)
js = result.json()["orders"]
for i in js:
    print(i)
df = pd.read_json(result.json()["orders"])
df
