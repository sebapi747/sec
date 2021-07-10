import requests
import datetime as dt
import csv
from lxml import html
from urllib.request import urlretrieve
import os
import config
outdir = config.dirname

url = "https://www.sec.gov/dera/data/financial-statement-data-sets.html"
x = requests.get(url)
print("%s %d" % (url,x.status_code))
parsed_body=html.fromstring(x.text)

href = parsed_body.xpath('//td[@class="views-field views-field-field-display-title"]/a/@href')
for h in href:
    url = "https://www.sec.gov" + h
    dst = outdir + "/" + os.path.basename(url)
    filebase = os.path.basename(url).split(".")[0]
    os.chdir(outdir)
    if os.path.isfile(dst) == False and os.path.isdir(outdir + "/" + filebase) == False:
        print("retrieving %s" % h)
        urlretrieve(url, dst)
        os.system("unzip %s -d %s" % (dst, filebase))
    else:
        print("skipping %s" % h)
