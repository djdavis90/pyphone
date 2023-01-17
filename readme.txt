### Dependencies:
  - Panphon by David R. Mortensen, available here: https://github.com/dmort27/panphon

### How to use:

`$ python pyphone.py <ruleset>`

`<ruleset>` is the name of the ruleset
Abbreviations can be used for <ruleset>. They are:
    - `sae`: standard-american-english
    - `rp`: received-pronunciation
    - `ae`: australian-english
Otherwise an additional ruleset can be added to the ruleset directory, and be used by passing in the name of the file (without .txt)

Consult phonological-rules-language.md for specifications on the language used to write rulesets

NOTE: The existing rulesets and phonological dictionary exist as proof of concept. They are not guaranteed to produce accurate results.

### Resources:
The English phonetic dictionary used is a modified version of the CMU Pronouncing Dictionary by Carnegie Mellon University, available here: http://www.speech.cs.cmu.edu/cgi-bin/cmudict

The features matrices are adapted from Panphon (see above)