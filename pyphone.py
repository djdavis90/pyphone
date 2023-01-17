# -*- coding: utf-8 -*-

import sys
from ipaconverter import IpaConverter
from textparser import TextParser
from init import *
import rules


DEFAULT_RULESETS = {
    "sae": "standard-american-english",
    "rp": "received-pronunciation",
    "ae": "australian-english"
}
def read_args():
    # NOTE; the flag -v for verbose is read in init.py
    ruleset = "standard-american-english"
    for arg in sys.argv[1:]:
        if arg[0] == "-":
            arg = arg[1:]
            continue
        elif arg in DEFAULT_RULESETS:
            ruleset = DEFAULT_RULESETS[arg]
        else:
            ruleset = arg
    return ruleset


def main():
    icf = IpaConverter.initialize_full()
    icf.set_as_default()
    
    tp = TextParser("english")
    ic = IpaConverter("english")
    
    ruleset_name = read_args()
    from rules import load_ruleset
    rules = load_ruleset(ruleset_name, ic, icf)
    print("\nRuleset: {}\n{} Rules in effect:".format(ruleset_name, len(rules)))
    for rule in rules:
        if rule.name:
            print("{}:".format(rule.name))
        else:
            print("(rule)")
        print("  {}".format(rule))
    print()
    
    while True:
        inp = input(" (English input): ").strip().lower()
        broad_ipa = tp.to_ipa(inp)
        
        print("/{}/".format(broad_ipa))
        print()
        segments = ic.to_segments(broad_ipa)
        
        for rule in rules:
            segments = rule.apply(segments)
            
        narrow_ipa = icf.to_ipa(segments)
        print("[{}]".format(narrow_ipa))


if __name__ == "__main__":
    main()

