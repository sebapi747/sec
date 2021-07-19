import numpy as np
import pandas as pd
import sqlite3
import os
import config

dirname=config.dirname

def get_statement(relevantnum, relevantpre, stmt):
    preIS = relevantpre[relevantpre['stmt']==stmt].sort_values(by=["report","line"])
    labeledNum = relevantnum.merge(preIS, how="inner", on="tag")
    mainNum = labeledNum.groupby(['ddate',"qtrs"]).size()
    if len(mainNum)==0:
        return pd.DataFrame()
    colname = ["tag", "value", "line", "plabel", "negating"]
    newcols = ["line", "plabel", "negating"]
    finalcols = ["line", "plabel", "negating"]
    mapper = {}
    my = []
    for index in mainNum[mainNum==max(mainNum)].index:
        ddate, qtrs = index
        tmp = labeledNum[(labeledNum['ddate']==ddate)&(labeledNum['qtrs']==qtrs)][colname]
        newcols.append("value"+str(index))
        if len(my) == 0:
            my = tmp
            my[newcols[-1]] = tmp["value"]
        else:
            my = my.merge(tmp, "outer", on="tag", suffixes=["",str(index)])
        finalcols.append(str(ddate)+"q"+str(qtrs))
        mapper[newcols[-1]] = finalcols[-1]
    my = my.rename(columns=mapper)
    return my[finalcols].sort_values(by="line")

def cik_to_csv(cik, d, dirname, sub, num, pre):
    fileprefix = "%s/../seccsv/%s/%s-%s" %(dirname, cik, cik, d)
    if os.path.isfile("%s-%s.csv" % (fileprefix, "sub"))==True:
        print("skipping %s %s" % (cik, d))
        return
    print("%s %s" % (d, cik))
    relevantsub = sub[(cik==sub['cik']) & (sub['detail']==1)]
    if len(relevantsub)==0:
        print("empty sub cik=%s" % cik)
        return
    adsh = relevantsub.iloc[0]['adsh']
    relevantnum = num[num['adsh']==adsh]
    relevantpre = pre[pre['adsh']==adsh]
    if len(relevantpre)==0:
        print("empty pre cik=%s" % cik)
        return
    os.mkdir(os.path.dirname(fileprefix))
    for s in set(relevantpre['stmt']):
        if s not in ["BS", "CF", "IS"]:
            continue
        get_statement(relevantnum, relevantpre,s).to_csv("%s-%s.csv" % (fileprefix, s), index=False)
    relevantsub.to_csv("%s-%s.csv" % (fileprefix, "sub"), index=False)

def d_to_csv(dirname, d):
    print(d)
    filename = "%s/%s/sub.txt" % (dirname, d)
    if os.path.isfile(filename)==False:
        print("missing %s" % filename)
        return
    sub = pd.read_csv(filename, sep="\t")
    filename = "%s/%s/num.txt" % (dirname, d)
    if os.path.isfile(filename)==False:
        print("missing %s" % filename)
        return
    num = pd.read_csv(filename, sep="\t")
    filename = "%s/%s/pre.txt" % (dirname, d)
    pre = pd.read_csv(filename, sep="\t")
    if os.path.isfile(filename)==False:
        print("missing %s" % filename)
        return
    sub['dirname'] = d
    for cik in sorted(sub['cik']):
        cik_to_csv(cik, d, dirname, sub, num, pre)

def all_csv(dirname):
    for d in sorted(os.listdir(dirname)):
        if d < "2012q4":
            continue
        try:
            d_to_csv(dirname,d)
        except:
            print("fail for %s" % d)

all_csv(dirname)
