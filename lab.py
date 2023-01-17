# -*- coding: utf-8 -*-

from segment import Segment
from panphon.featuretable import FeatureTable
from ipaconverter import IpaConverter
from textparser import TextParser
import json
import os.path
from init import *
import csv
from rules import test_rules


def to_cf(seg):
    n2s = {-1:"-", 0:"0", 1:"+"}
    li = [n2s[v] for k,v in seg.items()]
    return ",".join(li)
    
    
def output(s):
    with open("out.txt","w",encoding="utf-8") as f:
        f.write(s)
        
        
def convert_cmudict():
    fn = "cmudict.txt"
    ofn = "cmudict-modified.txt"
    
    with open("xsampa.json", "r", encoding="utf-8") as f:
        ipa = json.load(f)
    stress = {"1": "ˈ", "2": "ˌ", "0": ""}
    
    new_d = []
    with open(fn, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith(";;;"):
                continue
            word, p = line.split("  ")
            p = p.split(" ")
            li = []
            for c in p:
                if c[-1] in "012":
                    st = c[-1]
                    c = c[:-1]
                    li.append(stress[st])
                ic = ipa[c]
                if ic == "ʌ" and st == "0":
                    ic = "ə"
                li.append(ic)
            new_d.append("%s  %s" % (word, "".join(li)))
    new_d = "\n".join(new_d)
    with open(ofn, "w", encoding="utf-8") as f:
        f.write(new_d)


def syllabify_cmudict():
    from collections import Counter
    fn = "cmudict.txt"
    ofn = "cmudict-modified.txt"
    
    with open("xsampa.json", "r", encoding="utf-8") as f:
        ipa = json.load(f)
        
    c = Counter()
    vowels = set()
    vowels.add("ə")
    i = 0
    with open(fn, "r") as f:
        for line in f:
            line = line.strip()
            if line.startswith(";;;"):
                continue
            word, p = line.split("  ")
            p = p.split(" ")
            ons = []
            for pp in p:
                if pp[-1] in "012":
                    break
                ons.append(pp)
            ons = tuple(ons)
            c[ons] += 1
                    
            i += 1
    onsets = [k for k,v in c.items() if v >= 20]

    def split_onset(li):
        if not li:
            return [], []
        for i in range(len(li)):
            c1 = li[:i]
            c2 = li[i:]
            if tuple(c2) in onsets:
                return c1, c2
        return li, []
    
    new_d = []
    with open(fn, "r", encoding="utf-8") as f:
        n = 0
        for line in f:
            n += 1
            line = line.strip()
            if line.startswith(";;;"):
                continue
            word, p = line.split("  ")
            # print(word, p)
            p = p.split(" ")
            
            chunks = []
            chunk = []
            for pp in p:
                if pp[-1] in "012":
                    if chunk:
                        chunks.append(("c",chunk))
                    chunks.append(("v",[pp]))
                    chunk = []
                else:
                    chunk.append(pp)
            if chunk:
                chunks.append(("c",chunk))
            
            chunks2 = []
            for i in range(len(chunks)-1):
                t1, chunk1 = chunks[i]
                t2, chunk2 = chunks[i+1]
                if i == 0 and t1 == "v":
                    chunks2.append([])
                chunks2.append(chunk1)
                if t1 == "v" and t2 == "v":
                    chunks2.append([])
            chunks2.append(chunk2)
            if t2 == "v":
                chunks.append([])
                
            chunks3 = []
            for i in range(len(chunks2)):
                chunk = chunks2[i]
                # print("       ", chunk)
                if i != 0 and i != (len(chunks2)-1) and i % 2 == 0:
                    c1, c2 = split_onset(chunk)
                    chunks3 += [c1,c2]
                else:
                    chunks3.append(chunk)
            
            stress = {"1": "ˈ", "2": "ˌ", "0": ""}
            sylls = []
            for i in range(0,len(chunks3),3):
                li = chunks3[i:i+3]
                li2 = []
                strs = ""
                for x in li:
                    xli = []
                    for p in x:
                        if p[-1] in stress:
                            strs = stress[p[-1]]
                            p = p[:-1]
                        p = ipa[p]
                        if p == "ʌ" and strs == "":
                            p = "ə"
                        xli.append(p)
                    li2.append("".join(xli))
                sylls.append(strs + "".join(li2))
            sylls = ".".join(sylls)
            p = "".join(sylls)
            new_d.append("%s  %s" % (word, p))
    new_d = "\n".join(new_d)
    with open(ofn, "w", encoding="utf-8") as f:
        f.write(new_d)


def build_english_ipa():
    import csv
    head = """# This feature list was adapted from the PanPhon library by David R. Mortenson.
# https://github.com/dmort27/panphon
# 
# David R. Mortensen, Patrick Littell, Akash Bharadwaj, Kartik Goyal, Chris
# Dyer, Lori Levin (2016). "PanPhon: A Resource for Mapping IPA Segments to
# Articulatory Feature Vectors." Proceedings of COLING 2016, the 26th
# International Conference on Computational Linguistics: Technical Papers,
# pages 3475–3484, Osaka, Japan, December 11-17 2016.
#
#"""
    ks = [
        "ipa","syl","son","cons","cont","delrel","lat","nas","strid","voi","sg","cg","ant",
        "cor","distr","lab","hi","lo","back","round","velaric","tense","long","hitone","hireg","name"
    ]
    ipas = {"t","d","p","b","k","g","s","z","f","v","θ","ð","ʃ","ʒ","x","t͡ʃ","d͡ʒ","n","m","ŋ","l","r","j","w","h","ɪ","i","ʊ","u","ɛ","e","ə","ɜ","ɒ","o","æ","a","ʌ","ɑ","ɔ","ɚ"}
    
    d = {}
    with open("data/ipa-full.csv", "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(filter(lambda row: not row[0] == "#", f))
        for row in reader:
            if row["ipa"] in ipas:
                del row["name"]
                d[row["ipa"]] = row
            
    with open("data/ipa-english.csv", "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(filter(lambda row: not row[0] == "#", f))
        for row in reader:
            ipa = row["ipa"]
            seg = d.get(ipa)
            del row["name"]
            if row != seg:
                if seg is None:
                    dss = ("<NO FULL SEGMENT>", ipa)
                elif row is None:
                    dss = (ipa, "<NO ENGLISH SEGMENTS>")
                else:
                    dss = {}
                    for k in ks:
                        if k == "name":
                            continue
                        v1 = seg[k] if seg else "<NO FULL SEGMENT>"
                        v2 = row[k] if row else "<NO ENGLISH SEGMENT>"
                        if v1 != v2:
                            dss[k] = (v1, v2)
                print(ipa, dss)


def add_feature():
    if input("Are you sure you want to add a feature to ipa-full.csv?").lower() != "y":
        return
        
    li = []
    with open("data/ipa-full - Copy.csv", "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(filter(lambda row: not row[0] == "#", f))
        for row in reader:
            li.append(row)
            
    nf = "front"
    for d in li:
        if d["syl"] == "-" or d["back"] == "+":
            d[nf] = "-"
            continue
        for c in "iyɪʏeøɛœæaɶ":
            if c in d["ipa"]:
                d[nf] = "+"
                break
        if nf in d:
            continue
        d[nf] = "-"
        print(d["ipa"] + "\n")
            
    feats = ["ipa","syl","son","cons","cont","delrel","lat","nas","strid","voi","sg","cg","ant","cor","distr","lab","hi","lo","back","front","round","velaric","tense","long","hitone","hireg","name"]
    with open('data/ipa-full.csv', 'w', newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=feats)

        writer.writeheader()
        for d in li:
            writer.writerow(d)
            
            
def rewrite_english_ipa():
    if input("Are you sure you want to rewrite ipa-english.csv?").lower() != "y":
        return
        
    fulld = {}
    with open("data/ipa-full.csv", "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(filter(lambda row: not row[0] == "#", f))
        for row in reader:
            fulld[row["ipa"]] = row
            
    li = []
    with open("data/old-ipa-english.csv", "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(filter(lambda row: not row[0] == "#", f))
        for row in reader:
            new_row = fulld[row["ipa"]]
            li.append(new_row)
            
            
    feats = ["ipa","syl","son","cons","cont","delrel","lat","nas","strid","voi","sg","cg","ant","cor","distr","lab","hi","lo","back","front","round","velaric","tense","long","hitone","hireg","name"]
    with open('data/ipa-english.csv', 'w', newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=feats)

        writer.writeheader()
        for d in li:
            writer.writerow(d)
            
            
def _main():
    from collections import Counter
    
    icf = IpaConverter.initialize_full()
    icf.set_as_default()
    
    tp = TextParser("english")
    ic = IpaConverter("english")
    
    a = ic.to_segment("ə")
    d = {k:v for k,v in a.items()}
    c = Counter()
    n = 0
    for symbol, segment in ic:
        if any(segment[x] != y for x, y in (
            ("syl", 1),
            ("tense", -1),
            ("hi", -1)
        )):
            continue
        n += 1
        print("{}  vs  {}".format(a, symbol))
        for k, v in d.items():
            if segment[k] != v:
                c[k] += 1
                print("    {}: {}  vs  {}".format(k, v, segment[k]))
    for k, v in c.most_common():
        print(k, v, round(v/n, 2)) 
                


def main():
    icf = IpaConverter.initialize_full()
    icf.set_as_default()
    
    tp = TextParser("english")
    ic = IpaConverter("english")
    
    rules = test_rules(ic, icf)
    # exit()
    
    # s = tp.to_ipa("Betty bought a bit of butter But she said the butters bitter If I put it in my batter it will make my batter bitter But a bit of better butter will make my batter better So she bought a bit of butter better than her bitter butter And she put it in her batter And the batter was not bitter taco")

    while True:
        inp = input(" _: ").strip().lower()
        # inp = "Eddie"
        s = tp.to_ipa(inp)
        # s = "ˈtrwi"
        
        print("/{}/".format(s))
        print()
        s2 = ic.to_segments(s)
        
        for rule in rules:
            s2 = rule.apply(s2)
            
        s3 = icf.to_ipa(s2)
        print("[{}]".format(s3))
        #   return


if __name__ == "__main__":
    main()

