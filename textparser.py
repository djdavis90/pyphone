import os.path
try:
    import regex as re
except ImportError:
    import re
from ipaconverter import IpaConverter
from init import *


class TextParser:
    """
    Converts orthographic text to IPA strings
    """
    def __init__(self, name, ipa_converter=None):
        self.name = name
        self.ipa_converter = ipa_converter if ipa_converter else IpaConverter.default
        self._d = self.load_dictionary()
        
    def load_dictionary(self):
        """
        Loads phonetic dictionary of words
        """
        d = {}
        filename = "dict-" + self.name + ".txt"
        filename = os.path.join(DATA_DIR, filename)
        
        with open(filename, "r", encoding="utf-8") as f:
            for line in f:
                if line[0] == "#":
                    continue
                line = line.strip()
                word, p = line.split("  ")
                p = p.replace("g", "ɡ")
                
                d[word] = p
        return d
                
    def to_ipa(self, text):
        li = []
        for word in self.word_tokenize(text):
            ipa = self._d.get(word.upper())
            if ipa:
                li.append(ipa)
        return " ".join(li)
        
    def word_tokenize(self, text):
        for word in re.split(r"\s+", text):
            yield word
