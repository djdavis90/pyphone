Phonological rulesets are saved in .txt files in the rulesets directory.

Each line in the file is one rule, apart from:
- Rule names are enclosed in `""`double quotes. Rule names are optional. A rule name takes up the entire line, and applies to whichever rule is next below it.
- Lines beginning with `#` are comments, and are ignored
- Blank or whitespace lines are ignored

# Phonological Rule Language

**Basic rule structure:** `<core> -> <transformation> / <left environment> _ <right environment>`
(Spaces are optional and are ignored by the parser)

Each of these fields is an Environment

## Environment Specifications
- Environments are composed of segments
- Segments are enclosed in [] brackets
- Segments can be either an IPA symbol, or a list of binary features separated by commas
    - eg: `[r]`, `[æ]` and `[+syl,-hi]` are both valid segment expressions

**~~Shorthand segments/features~~**
- ~~`C` is short for `[-syl +con]` (consonant)~~
- ~~`V` is short for `[+syl -con]` (vowel)~~

~~These can occur on their own, or inside brackets with other feats~~
    ~~eg: `[C,+voi,-son]` is equivalent to `[-syl,+con,+voi,-son]`~~  
(note: the above are not yet implemented)

**Stress:**  
- There are three stresses: `1`, `2`, and `0`, for primary, secondary, and no stress, respectively
- Similarly to a feature, you can use `stress=` followed by one number, or any combination of these three numbers in parentheses and it will match any of them
    - eg: `[+syl,stress=0]` will only match no stress, `[+syl,stress=(1,2)]` will match primary or secondary stress, but not no stress

**Boundaries:**
- `#`: word boundary
- `$`: syllable boundary
- ~~`+`: morpheme boundary~~ *(Not implemented. Since CMUdict doesn't have morpheme boundaries, these would have to be added in manually)**

A word boundary also counts as a syllable boundary

By default, environments will be boundary-insensitive, meaning they will ignore all boundaries. An environment will be boundary sensitive if either of the following is true:
- The environment contains a boundary, or
- The environment is tagged with `b` (see tags below)

**Greek features**  
Lower case Greek letters can be used in place of `+` or `-` in features to denote either `+` or `-`
- This will be consistent throughout the entire rule, including, core, transformation, and both left and right environments
    - eg: `[αnas] _ [αnas]` will match either `[+nas] _ [+nas]` or `[-nas] _ [-nas]`, but not `[+nas] _ [-nas]` or `[-nas] _ [+nas]`
- The same character can be used across different features
    - eg: `[βvoi] _ [βback]` will match `[+voi] _ [+back]` and `[-voi] _ [-back]`
- Usable Greek characters: `αβγδεζηθικλμνξοπρστυφχψω`

**Zero+ segments**  
- `<segment>0` will match 0 or more occurrences of `<segment>` (like * in regexp)
    - eg: ~~`C0`~~, ~~`V0`~~, `[+voi]0`, `#0`, `$0`, etc

**`{}` Brackets (possibilities):**  
- Contain multiple possible environments, separated by commas (sort of like [] in regexp)
    - eg: `{[C,+voi],#}` matches either `[C,+voi]` or `#`
- Possibilities can also be of variable length
    - eg: `{C0[V,+hi]#,[V,-hi][ʔ]}` will match either `C0[V,+hi]#` or `[V,-hi][ʔ]`
- Brackets can be nested
    - eg: `{C0[V,+hi]{$,[t]},#}` will match any of `C0[V,+hi]$` or `C0[V,+hi][t]` or `#`

Note: Brackets cannot be used in fixed-width environments (the core or the transformation)

**`()` Parentheses (optional):**  
- Environments/segments in parentheses are optional (sort of like ? in regexp)
    - eg: `([+con,+son,+nas])[V,stress12]` will match both `[+con,+son,+nas][V,stress12]` and `[V,stress12]`

Note: Parentheses cannot be used in fixed-width environments (the core or the transformation)

**Tags:**  
Tags provide additional details about an Environment. They are specified by adding a `:` at the end of the environment followed by one or more tags, separated by commas.

So far there is only one tag:
- `b`: boundary-sensitive

eg: `[a][ɪ]:b` will match /a͡ɪ/ but not /a.ɪ/ or /a ɪ/

### Core and transformation

The core and the transformation are types of Environment, with the following constraints:
- The core and transformation of a rules must be the same length
    - (This is because there is a one-to-one correspondence between them)
- The core and transformation must be fixed width
    - This means they can't use `{}` brackets, `()` parentheses, or `0` zero+ segments.
- *Future development notes:*
    - *Eventually brackets will be permitted in the core if they only contain a single segment*
    - *Eventually all of these will be permitted in the core, but only if transformation only occurs on segments with ordinals*
    - *For obvious reasons these won't ever be permitted in transformations*

The transformation consists of segments only.
- Transformation segments specify features to be changed.
- Any features not specified in transformation will be maintained from whatever the core has matched

Core and Transformation can also use the following expressions:

**Insertion and Deletion:**  
- Insertion or deletion is done through the null symbol `Ø` (the capital Scandinavian letter, since the unicode null symbol can have display issues) *TODO: Eventually both unicode null symbol `∅` and the letter `Ø` will work interchangeably for this*
    - eg: `Ø -> [u]` will insert `[u]`, and `[u] -> Ø` will delete [u], in the specified context
- If `Ø` occurs in the core, the corresponding segment in the transformation MUST be a complete segment with every feature specified (easiest way to do this is use an IPA token)

**`<>` brackets (conditional transformations):**  
- Features enclosed in <> brackets in the core and transformation represent additional conditional transformations
- A core will match whether or not the `<>`bracketed feature matches
- The `<>`bracketed features in the transformation are only applied if the `<>`bracketed features in the core match
- eg: `[-ant,-cont,<-voi>] -> [+strid,<+ant,+cont>]` has the following properties
    - The core will match all `[-ant,-cont]` segments and always apply the `[+strid]` transformation to them
    - If the segment matches `[-voi]` it will also apply the `[+ant,+cont]` transformation to it
        
**Ordinals (Metathesis and coalescence):**  
- Segments can be numbered with an ordinal in the core using `<ordinal>:<segment>`
    - eg: `1:[+syl]2:[-syl]`
- Segments can be reordered/backreferenced in the transformation by using just the ordinals (separate them with spaces if they're together)
    - eg: `1:[seg]2:[seg] -> 2 1`  (basic metathesis)
- Ordinal segments can be transformed using the `1:[seg]` syntax in the transformation
    - eg: `1:V[C,+nas] -> 1:[+nas]Ø` (this transforms a vowel, nasal consonant sequence to a nasalized vowel (without the consonant), like in French "blanc")