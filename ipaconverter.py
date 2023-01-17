import csv
import os.path
from segment import Segment
from init import *


FULL_NAME = "full"


class IpaConverter:
    """
    Converts between IPA string(s) and Segments
    
    Attributes
    ------------------------
    name: str
        Converter name. Should match an existing "data/ipa-<name>.csv"
        file to be loaded.
    names: list (str)
        names of IPA phonemes as listed in the csv file under "name" col.
        Generally not used for anything other than maybe debugging.
        
    _ipa_seg_dict: dict {str: Segment}
        Mapping of IPA representation to Segment
    _seg_ipa_dict: dict {frozenset: str}
        Mapping of Segment to IPA representation. Segment is represented by a
        frozenset (for hashing) provided by _to_set_key() method
    
        
    """
    STRESS_CHARS = {
        0: "", 1: "ˈ", 2: "ˌ"
    }
    FULL = None
    
    default = None
    
    def __init__(self, name):
        """
        
        """
        self.name = name
        self._ipa_seg_dict = None
        self._seg_ipa_dict = None
        self.names = None
        
        self.read_file()
        
    @classmethod
    def initialize_full(cls, name=FULL_NAME):
        ic = IpaConverter(name)
        cls.FULL = ic
        cls.default = cls.FULL
        return ic
        
    def set_as_default(self):
        """Set this instance as default to be used when no other is supplied"""
        IpaConverter.default = self
        
    def read_file(self):
        filename = "ipa-" + self.name + ".csv"
        filename = os.path.join(DATA_DIR, filename)
        
        s2n = {"-": -1, "0": 0, "+": 1}
        self._ipa_seg_dict = {}
        self._seg_ipa_dict = {}
        self.names = {}
        with open(filename, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(filter(lambda row: not row[0] == "#", f))
            
            featureset = set(reader.fieldnames)
            for fieldname in ("ipa", "name"):
                featureset.discard(fieldname)
            if featureset != FEATURESET:
                raise ValueError(filename + " featureset does not match features in full IPA csv")
                
            for row in reader:
                ipa = row["ipa"]
                name = row["name"]
                del row["ipa"]
                del row["name"]
                
                self.names[ipa] = name
                
                value = {feat: s2n[v] for feat, v in row.items()}
                seg = Segment(value, ipa=ipa)
                
                self._ipa_seg_dict[ipa] = seg
                self._seg_ipa_dict[seg.get_hash()] = ipa
                
    def __iter__(self):
        """
        Iterates over symbol, segment pairs (str, Segment)
        """
        return iter((k, v.copy()) for k, v in self._ipa_seg_dict.items())
        
    def get_ipa_symbol(self, seg):
        if seg == WORD_B:
            return " "
        if seg == SYLL_B:
            return "."
        if seg == NULL:
            return ""
        hash = seg.get_hash()
        if hash in self._seg_ipa_dict:
            return self._seg_ipa_dict[hash]
        # for ipa, value in self._ipa_seg_dict.items():
            # if seg.match(value):
                # return ipa
        return "<NO SYMBOL>"
    
    def to_ipa(self, segs):
        if isinstance(segs, Segment):
            segs = [segs]
            
        ipa_li = []
        last_stress = -1
        for seg in segs:
            ipa_li.append(self.get_ipa_symbol(seg))
            if seg in BOUNDARIES:
                last_stress = len(ipa_li)
                ipa_li.append("")
            elif seg.stress is not None:
                ipa_li[last_stress] = self.STRESS_CHARS[seg.stress]
        
        while ipa_li and ipa_li[0] in " .":
            ipa_li.pop(0)
        while ipa_li and ipa_li[-1] in " .":
            ipa_li.pop(-1)
            
        return "".join(ipa_li)
        
    def to_segments(self, ipa):
        segs = [WORD_B]
        for seg in self._ipa_tokenize(ipa):
            segs.append(seg)
        segs += [WORD_B]
        return segs
        
    def to_segment(self, ipa, stress=None):
        segment = self._ipa_seg_dict[ipa].copy()
        segment.stress = stress
        return segment
        
    def _ipa_tokenize(self, ipa):
        """
        TODO: Make this its own class
        
        Generator (str) for tokenizing IPA strings into individual phoneme
        representations, including ones that use multiple Unicode characters
        """
        
        # removing stress markers/word boundaries from IPA string
        # for c in "ˈˌ":
            # ipa = ipa.replace(c,"")
        # TODO: convert in whatever stress/boundary representation I end up doing
        if not ipa:
            return
        
        buffer = []
        possibilities = set(self._ipa_seg_dict.keys())
        
        pli = []
        
        i = 0
        next_boundary = None
        last_stress = 0
        while True:
            c = ipa[i]
            
            if c == " ":
                next_boundary = WORD_B
            elif c == ".":
                next_boundary = SYLL_B
            elif c == "ˈ":
                last_stress = 1
            elif c == "ˌ":
                last_stress = 2
            
            else:
                buffer.append(c)
                s = "".join(buffer)
                
                for p in possibilities.copy():
                    pli.append("%s starts with %s: %s" % (p, s, p.startswith(s)))
                    if not p.startswith(s):
                        possibilities.discard(p)
                    
            token = None
            if len(possibilities) == 0:
                # Tokenize and move back if no more possibilities
                if len(buffer) == 1:
                    token = buffer[0]
                else:
                    token = "".join(buffer[:-1])
                i -= 1
            elif i >= len(ipa)-1 or next_boundary:
                # Tokenize if at end of string, or if the character is a boundary
                token = "".join(buffer)
                
            if token is not None:
                if token in self._ipa_seg_dict:
                    segment = self._ipa_seg_dict[token].copy()
                    if segment.get("syl") == 1:
                        segment.stress = last_stress
                        last_stress = 0
                    yield segment
                    
                    possibilities = set(self._ipa_seg_dict.keys())
                    buffer = []
                else:
                    for x in pli:
                        print(self.name, x)
                    with open("out.txt", "w", encoding="utf-8") as f:
                        f.write("\n".join(pli))
                    raise ValueError("\"ipa-{}\" IpaConverter has no match for symbol \"{}\" in string {}".format(
                        self.name, token, ipa
                    ))
                    
                if i >= len(ipa)-1:
                    return
                    
            if next_boundary:
                yield next_boundary
                next_boundary = None
                
            i += 1


    


