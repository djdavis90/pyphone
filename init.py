import os.path
import csv


import sys
V = "-v" in sys.argv
print("verbose:", V)
def vpr(*args, i=0):
    if V:
        print("  " * i, *args)


DIR = os.path.split(__file__)[0]
DATA_DIR = os.path.join(DIR, "data")


# boundaries
SYLL_B = "<syll>"
WORD_B = "<word>"
BOUNDARIES = (SYLL_B, WORD_B)

NULL = ""
NULLSIGN = "Ø"
STATICSIGN = "◯"

def __load_featureset():
    filename = "ipa-full.csv"
    filename = os.path.join(DATA_DIR, filename)
    if not os.path.isfile(filename):
        raise IOError(filename + " does not exist. There must be a complete feature matrix contained in this file.")
        
    featureset = set()
    with open(filename, "r", newline="", encoding="utf-8") as f:
        reader = csv.reader(filter(lambda row: not row[0] == "#", f))
        header = next(reader)
        if not header or len(header) < 3 or header[0] != "ipa" or header[-1] != "name":
            raise ValueError(filename + " is invalid")
        featureset = set(header[1:-1])
    return featureset

FEATURESET = __load_featureset()

GREEK_ALPHABET = {
    "alpha": "α",
    "beta": "β",
    "gamma": "γ",
    "delta": "δ",
    "epsilon": "ε",
    "zeta": "ζ",
    "eta": "η",
    "theta": "θ",
    "iota": "ι",
    "kappa": "κ",
    "lambda": "λ",
    "mu": "μ",
    "nu": "ν",
    "xi": "ξ",
    "omicron": "ο",
    "pi": "π",
    "rho": "ρ",
    "sigma": "σ",
    "tau": "τ",
    "upsilon": "υ",
    "phi": "φ",
    "chi": "χ",
    "psi": "ψ",
    "omega": "ω"
}
GREEK = set(GREEK_ALPHABET.values())
