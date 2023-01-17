from segment import Segment, MetaSegment
from init import *
from ipaconverter import IpaConverter
try:
    import regex
except ImportError:
    import re as regex
        
        
def load_ruleset(name, ipaconverter, ipaconverter_full):
    fn = "rulesets/{}.txt".format(name)
    if not os.path.isfile(fn):
        raise IOError("No such ruleset '{}'".format(fn))
    rules = []
    name = None
    with open(fn, "r", encoding="utf-8", newline="") as f:
        for line in f:
            line = line.strip()
            if not line or line.isspace() or line[0] == "#":
                continue
            if line[0] == '"':
                name = line[1:-1]
            else:
                rule = RuleParser(
                    line,
                    ipaconverter=ipaconverter,
                    ipaconverter_full=ipaconverter_full
                ).parse()
                rule.name = name
                name = None
                rules.append(rule)
        
    return rules


class Rule:
    def __init__(self):
        self.left_environment = None
        self.right_environment = None
        self.core = None
        self.transformation = None
        self.name = None
        
    def __str__(self):
        return "{} -> {} / {} _ {}".format(
            self.core,
            self.transformation,
            self.left_environment,
            self.right_environment
        )
        
    def __eq__(self, other):
        if not isinstance(other, Rule):
            return False
        vpr(
            "Rule eq:",
            # "core:", self.core == other.core,
            "tf:", self.transformation == other.transformation,
            # "left:", self.left_environment == other.left_environment,
            "right:", self.right_environment == other.right_environment
        )
        return (
            self.core == other.core and \
            self.transformation == other.transformation and \
            self.left_environment == other.left_environment and
            self.right_environment == other.right_environment
        )
        
    def validate(self):
        rs = str(self)
        
        if not self.core.is_fixed:
            raise ValueError("core must be fixed width in rule {}".format(rs))
        if len(self.core) != len(self.transformation):
            raise ValueError("core and transformation must be same length in rule {}".format(rs))
        
        cos = set()
        tos = set()
        for i in range(len(self.core)):
            cn = self.core[i]
            tn = self.transformation[i]
            if (cn.ordinal is not None or tn.ordinal is not None):
                if (cn.ordinal is None or tn.ordinal is None):
                    raise ValueError("core and transformation ordinals don't correspond in index {} in rule {}".format(i, rs))
                if cn.ordinal in cos:
                    raise ValueError("Repeated core ordinal {} in rule {}".format(cn.ordinal, rs))
                if tn.ordinal in tos:
                    raise ValueError("Repeated transformation ordinal {} in rule {}".format(tn.ordinal, rs))
                cos.add(cn.ordinal)
                tos.add(tn.ordinal)
                
            if cn.kind == Environment.Node.SEGMENT:
                if cn.value.bracketed is not None:
                    if tn.kind != Transformation.Node.METASEGMENT or tn.value.bracketed is None:
                        raise ValueError("core and transformation do not have corresponding <>bracketed segments at index {} in rule {}".format(i, rs))
        if cos != tos:
            raise ValueError("core and transformation ordinals dont' match in rule {}".format(rs))
                    
    def apply(self, context):
        vpr("\nApplying rule: {}".format(self))
        result = []
        i = 0
        last_i = -1
        while i < len(context):
            if self.core.crosses_boundaries and context[i] in BOUNDARIES:
                result.append(context[i])
                i += 1
                continue
                
            vpr("context index {}: {}".format(i, context[i]))
            
            matches = True
            core_matcher = Matcher(context, self.core, i=i)
            core_match = core_matcher.match()
            vpr("  matching core...")
            if not core_match:
                vpr("  no core match")
                matches = False
            else:
                vpr("  core match!")
                
            if matches and self.left_environment:
                vpr("  matching left...")
                left_matcher = Matcher(context, self.left_environment, i=i-1, reverse=True)
                if not left_matcher.match():
                    vpr("  no left match")
                    matches = False
                else:
                    vpr("  left match!")
            if matches and self.right_environment:
                vpr("  matching right...")
                right_matcher = Matcher(context, self.right_environment, i=core_match.range[1])
                if not right_matcher.match():
                    vpr("  no right match")
                    matches = False
                else:
                    vpr("  right match!")
                
            if matches:
                vpr("match at content index {}. Applying transformation...".format(i))
                tf = self.transformation.apply(core_match, self.core)
                
                prli = [(
                    IpaConverter.FULL.to_ipa(tfi) if isinstance(tfi, (Segment, MetaSegment)) else tfi
                ) for tfi in tf]
                vpr("transformation: {}".format("".join(prli)))
                result += tf
                
                if core_match.range[1] == core_match.range[0]:
                    # if core_match has a length of zero, we manually increment i, otherwise it will never advance
                    result.append(context[i])
                    i = core_match.range[1] + 1
                else:
                    i = core_match.range[1]
            else:
                result.append(context[i])
                i += 1
                
        result = [x for x in result if x != ""]
        return result
    
    
class RuleParser:
    def __init__(self, literal, ipaconverter=None, ipaconverter_full=None):
        self.literal = literal
        self.i = 0
        self.ic = ipaconverter if ipaconverter else IpaConverter.default
        self.icf = ipaconverter_full if ipaconverter_full else IpaConverter.FULL

    def parse(self):
        try:
            return self._parse()
        except ValueError:
            print("i = %s" % self.i)
            print(self.literal)
            print((" " * self.i) + "^")
            raise

    def _parse(self):
        rule = Rule()
        
        vpr("\nParsing core...")
        rule.core = self.EnvironmentParser(self, self.ic, stopat="->").parse()
        vpr("Completed core:", rule.core)
        vpr("\nParsing transformation...")
        rule.transformation = self.EnvironmentParser(self, self.icf, stopat="/", is_trans=True).parse()
        vpr("Completed transformation:", rule.transformation)
        vpr("\nParsing left_environment...")
        rule.left_environment = self.EnvironmentParser(self, self.icf, stopat = "_").parse()
        vpr("Completed left_environment:", rule.left_environment)
        vpr("\nParsing right_environment...")
        rule.right_environment = self.EnvironmentParser(self, self.icf, stopat=":").parse()
        vpr("Completed right_environment:", rule.right_environment)
        if self.i < len(self.literal):
            flags = self.parse_flags()
        rule.validate()
        vpr("\ncompleted rule:", rule)
        
        return rule
        
    def get_last_char(self):
        if self.i == 0:
            return None
        return self.literal[self.i-1]
        
    class EnvironmentParser:
        def __init__(self, parser, ic, stopat=None, is_trans=False, depth=0): # trans rights
            self.parser = parser
            self.nodes = []
            self.ic = ic
            
            self.env_class = Transformation if is_trans else Environment
            
            self.stopat = stopat
            if self.stopat:
                if isinstance(self.stopat, str):
                    self.stopat = [self.stopat]
            
            self.in_square = False  # when in []
            self.in_brackets = False  # when in <>
            self.in_curly = False  # when in {}
            
            self.feats = None
            self.stress = None
            self.bracketed_feats = None
            self.bracketed_stress = None
            self.feat_value = None  # when reading a feat, either + or - or greek
            self.ordinal = None
            self.has_tags = False
            
            self.segment_closed = False  # if True, next char should be ]
            
            self.curly_envs = None
            
            self.buffer = []
            
            self._depth = depth
        
        def parse(self):
            while self.parser.i < len(self.parser.literal):
                # check for stopat
                if not any((
                    self.in_square, self.in_curly, self.in_brackets
                )) and self.stopat is not None:
                    if self.stop_here():
                        vpr("Breaking due to stopat", i=self._depth)
                        break
                        
                token = self.parser.literal[self.parser.i]
                vpr("  Token: \"{}\"  i={}/{}".format(token, self.parser.i, len(self.parser.literal)), i=self._depth)
                vpr("  {}\n  {}^".format(self.parser.literal, " " * self.parser.i), i=self._depth)
                if token.isspace():
                    vpr("    skipping whitespace")
                    pass
                elif self.in_curly:
                    self.__parse_env_token_in_curly(token)
                elif self.in_square:
                    self.__parse_env_token_in_square(token)
                else:
                    self.__parse_env_token_out_square(token)
                        
                self.parser.i += 1
                vpr("    advancing parser generally ::", self.parser.literal[self.parser.i] if self.parser.i < len(self.parser.literal) else "END", i=self._depth)
                
            tags = {}
            if self.has_tags:
                tags = self.read_tags_from_buffer()
            if self.in_square or self.in_brackets or self.in_curly:
                raise ValueError()
            return self.env_class(self.nodes, depth=self._depth, **tags)
            
        def stop_here(self):
            for _stopat in self.stopat:
                test_stop = self.parser.literal[self.parser.i:self.parser.i + len(_stopat)]
                vpr("    test_stop: \"{}\" == \"{}\": {}".format(test_stop, _stopat, test_stop == _stopat), i=self._depth)
                if test_stop == _stopat:
                    self.parser.i += len(_stopat)
                    vpr("    advancing parser to end of stopat", _stopat, "::", self.parser.literal[self.parser.i] if self.parser.i < len(self.parser.literal) else "END", i=self._depth)
                    return True
            return False
            
        def __parse_env_token_in_square(self, token):
            # TODO: This is where you would add parsing for C and V shortcuts
            
            # brackets
            if self.segment_closed and token != "]":
                raise ValueError
            if token == "[":
                if self.in_square:
                    raise ValueError("Nested or improperly matched []brackets")
                self.in_square = True
                self.feats = {}
            elif token == "]":
                self.finalize_square_node()
            elif token == "<":
                if self.bracketed_feats is not None:
                    raise ValueError("Nested or unmatched <>brackets")
                self.in_brackets = True
                self.bracketed_feats = {}
            elif token == ">":
                if self.bracketed_feats is not None:
                    raise ValueError("Nested or unmatched <>brackets")
                self.in_brackets = True
                self.bracketed_feats = {}
                
            # feats
            elif token in "+-":
                self.feat_value = Segment.S2N[token]
            elif token in GREEK:
                self.feat_value = token
            elif token in " ,":
                if self.feat_value is not None:
                    self.finalize_feat()
            else:
                self.buffer.append(token)
        
        def __parse_env_token_out_square(self, token):
            # ordinals
            if self.buffer:
                if token.isnumeric():
                    self.buffer.append(token)
                    vpr("    adding ordinal digit +{} (ordinal is now {})".format(token, "".join(self.buffer)), i=self._depth)
                elif token == ":":
                    if not self.buffer:
                        raise ValueError("Invalid rule syntax (colon without ordinal)")
                    self.ordinal = int("".join(self.buffer))
                    self.buffer.clear()
                else:
                    raise ValueError("invalid rule syntax (ordinal not closed with colon)")
            elif token.isnumeric() and token != "0":
                self.buffer.append(token)
                vpr("    adding ordinal digit +{} (ordinal is now {})".format(token, "".join(self.buffer)), i=self._depth)
                
            elif token == ":":
                self.has_tags = True
            elif self.has_tags:
                self._parse_token_to_buffer(token)
        
            elif token == NULLSIGN:
                node = self.env_class.Node(
                    self.env_class.Node.NULL, NULL, ordinal=self.ordinal
                )
                vpr("   +node  (null): ", node, i=self._depth)
                self.nodes.append(node)
                self.ordinal = None
            elif token == STATICSIGN:
                if (self.env_class != Transformation):
                    raise ValueError("Static symbol in non-Transformation environment")
                node = Transformation.Node(
                    Transformation.Node.STATIC, STATICSIGN, ordinal=self.ordinal
                )
                vpr("   +node  (static): ", node, i=self._depth)
                self.nodes.append(node)
                self.ordinal = None
            elif token == "0":
                self.nodes[-1]._zero_plus = True  # Don't like how ugly this is
            elif token in "#$+":
                node = self.env_class.Node(
                    self.env_class.Node.BOUNDARY,
                    WORD_B if token == "#" else SYLL_B if token == "$" else MORPHEME_B,
                    ordinal=self.ordinal
                )
                vpr("   +node (bound): ", node, i=self._depth)
                self.nodes.append(node)
                self.ordinal = None
            elif token == "[":
                self.in_square = True
                self.feats = {}
                
            elif token == "{":
                self.in_curly = True
                self.curly_envs = []
            elif token == "(":
                self.parser.i += 1
                vpr("    advancing parser after ( ::", self.parser.literal[self.parser.i] if self.parser.i < len(self.parser.literal) else "END", i=self._depth)
                env = RuleParser.EnvironmentParser(self.parser, self.ic, stopat=")", depth=self._depth+1).parse()
                node = Environment.Node(
                    Environment.Node.OPTIONAL, env
                )
                vpr("   +node (paren): ", node, i=self._depth)
                self.nodes.append(node)
            
            else:
                raise ValueError("Unrecognized or invalid rule syntax")
                
        def __parse_env_token_in_curly(self, token):
            vpr("  instantiating new EnvironmentParser within curly braces", i=self._depth)
            env = RuleParser.EnvironmentParser(self.parser, self.ic, stopat=[",","}"], depth=self._depth+1).parse()
            self.curly_envs.append(env)
            if self.parser.get_last_char() == "}":
                node = Environment.Node(
                    Environment.Node.POSSIBILITIES,
                    self.curly_envs
                )
                vpr("   +node (  }  ): ", node, i=self._depth)
                self.nodes.append(node)
                self.curly_envs = None
                self.in_curly = False
            else:
                vpr("  comma break in curly braces", i=self._depth)
                # To counteract the automatic skipping of initial and final characters in EnvironmentParsers
                # ("," is both the end of the previous and the start of the new Enviornment)
            self.parser.i -= 1
            vpr("    receding parser after , in {} ::", self.parser.literal[self.parser.i] if self.parser.i < len(self.parser.literal) else "END", i=self._depth)
                
        def finalize_square_node(self):
            self.finalize_feat()
            if self.feats and not self.segment_closed:
                bracketed = None
                if self.bracketed_feats:
                    bracketed = MetaSegment(
                        self.bracketed_feats, stress=self.bracketed_stress
                    )
                    
                kind = Transformation.Node.METASEGMENT if self.env_class == Transformation else Environment.Node.SEGMENT
                node = self.env_class.Node(
                    kind,
                    MetaSegment(
                        self.feats, stress=self.stress, bracketed=bracketed
                    ),
                    ordinal=self.ordinal
                )
                vpr("   +node (metaS): ", node, i=self._depth)
                self.nodes.append(node)
                
            self.feats = None
            self.stress = None
            self.bracketed_feats = None
            self.bracketed_stress = None
            self.feat_value = None
            self.segment_closed = False
            self.in_square = False
            self.ordinal = None
            
        STRESS_REGEX = regex.compile(r"stress=(\((?P<group>[012]+)\)|(?P<single>[012]))")
        def finalize_feat(self):
            if not self.buffer:
                return
            feat = "".join(self.buffer)
            vpr("     feat:", feat, i=self._depth)
            self.buffer.clear()
            
            m = self.STRESS_REGEX.match(feat)
            if m:
                if m.group("group"):
                    stress = list(m.group("group"))
                    self.stress = set(int(x) for x in stress)
                elif m.group("single"):
                    self.stress = int(m.group("single"))
            elif self.feat_value:
                if self.in_brackets:
                    self.bracketed_feats[feat] = self.feat_value
                else:
                    self.feats[feat] = self.feat_value
            else:
                try:
                    seg = self.ic.to_segment(feat)
                except KeyError:
                    raise ValueError("No segment for IPA \"{}\"".format(feat))
                    
                if self.env_class != Transformation:
                    seg = MetaSegment(seg.data, stress=self.stress, ipa=seg.ipa)
                node = self.env_class.Node(
                    self.env_class.Node.SEGMENT, seg
                )
                vpr("   +node (sgmnt): ", node, i=self._depth)
                self.nodes.append(node)
                self.close_segment = True
                
            self.feat_value = None
            
        def _parse_token_to_buffer(self, token):
            self.buffer.append(token)
            
        def read_tags_from_buffer(self):
            tags = {}
            s = "".join(self.buffer)
            s = s.split(",")
            for i in s:
                i = i.strip().lower()
                if i == "b":
                    tags["crosses_boundaries"] = False
                else:
                    raise ValueError("Invalid tag \"{}\"".format(i))
            return tags
        


class Environment:
    """
    Represents a phonetic environment for the purpose of matching a context
    (context is a list of Segments/boundaries)
    Immutable
    
    Attributes
    --------------------
    nodes: (tuple of Environment.Node)
    """
    def __init__(self, nodes, crosses_boundaries=None, depth=0):
        self.nodes = nodes
        if crosses_boundaries is not None:
            self._crosses_boundaries = crosses_boundaries
        else:
            self._crosses_boundaries = True
            for node in self.nodes:
                if node.kind == Environment.Node.BOUNDARY:
                    self._crosses_boundaries = False
                    break
        
        self._is_fixed = self._check_fixed()
        self._inverse = None
        
        self._depth = depth
        
    def _check_fixed(self):
        for node in self.nodes:
            if not node.is_fixed():
                return False
        return True
        
    def __str__(self):
        sli = [str(node) for node in self.nodes]
        # if self._crosses_boundaries:
            # sli += "(cb:t)"
        return "".join(sli)
        
    def __eq__(self, other):
        vpr(
            "Environment eq:",
            "instance", isinstance(other, Environment),
            "nodes", self.nodes == other.nodes,
            "cb", self.crosses_boundaries == other.crosses_boundaries,
            i=self._depth
        )
        if not isinstance(other, Environment):
            return False
        return (
            self.nodes == other.nodes and self.crosses_boundaries == other.crosses_boundaries
        )
        
    @property
    def crosses_boundaries(self):
        return self._crosses_boundaries
    @property
    def is_fixed(self):
        return self._is_fixed
        
    def __len__(self):
        return len(self.nodes)
    
    def __getitem__(self, i):
        return self.nodes[i]
        
    def inverse(self):
        if not self._inverse:
            nodes = []
            for node in reversed(self.nodes):
                _node = node.inverse()
                nodes.append(_node)
            self._inverse = Environment(
                nodes, crosses_boundaries=self.crosses_boundaries,
                depth=self._depth
            )
            self._inverse._inverse = self
        return self._inverse
    
    class Node:
        """
        Represents a piece of the context.
        """
        SEGMENT = 1
        NULL = 2
        BOUNDARY = 3
        OPTIONAL = 4
        POSSIBILITIES = 5
        
        def __init__(self, kind, value, zero_plus=False, ordinal=None):
            self._kind = kind
            self._value = value
            self._zero_plus = zero_plus
            self._ordinal = ordinal
            
        def __eq__(self, other):
            # vpr(
            (
                "ENode {} == {} eq:".format(self, other),
                "isntance", isinstance(other, Environment.Node),
                "kind", self._kind == other._kind,
                "value", self._value == other._value,
                "zp", self._zero_plus == other._zero_plus,
                "ord", self._ordinal == other._ordinal,
                # i=self._depth
            )
            if not isinstance(other, Environment.Node):
                return False
            return (
                self._kind == other._kind and \
                self._value == other._value and \
                self._zero_plus == other._zero_plus and \
                self._ordinal == other._ordinal
            )
            
        def is_fixed(self):
            """Returns True if Node is of fixed width"""
            if self.zero_plus:
                return False
            if self.kind == self.OPTIONAL:
                return self.value.is_fixed
            if self.kind == self.POSSIBILITIES:
                for env in self.value:
                    if not env.is_fixed:
                        return False
                return True
            return True
            
        def inverse(self):
            if self.kind == self.OPTIONAL:
                value = self.value.inverse()
            elif self.kind == self.POSSIBILITIES:
                value = [env.inverse() for env in self.value]
            else:
                value = self.value
            return Environment.Node(
                self.kind, value, self.zero_plus, self.ordinal
            )
            
        def __str__(self):
            s = None
            if self.kind == self.SEGMENT:
                if self.value.ipa is not None:
                    s = "[" + self.value.ipa + "]"
                else:
                    li = []
                    for feat, val in self.value.data.items():
                        val = "+" if val == 1 else "-" if val == -1 else 0
                        li.append("{}{}".format(val, feat))
                    if self.value.stress is not None:
                        if isinstance(self.value.stress, int):
                            stress_str = self.value.stress
                        elif len(self.value.stress) == 1:
                            (stress_str,) = self.value.stress
                        else:
                            stress_str = ",".join([str(s) for s in self.value.stress])
                        li.append("stress={}".format(stress_str))
                    s = "[{}]".format(", ".join(li))
            elif self.kind == self.NULL:
                s = NULLSIGN
            elif self.kind == self.BOUNDARY:
                # TODO: make these constants
                if self.value == WORD_B:
                    s = "#"
                elif self.value == SYLL_B:
                    s = "$"
                elif self.value == MORPHEME_B:
                    s = "+"
            elif self.kind == self.OPTIONAL:
                s = "({})".format("".join([str(v) for v in self.value]))
            elif self.kind == self.POSSIBILITIES:
                s = "{%s}" % (", ".join([str(v) for v in self.value]))
            
            if self.ordinal is not None:
                s = "{}:{}".format(self.ordinal, s)
            if self.zero_plus:
                s += "0"
            return s
        
        @property
        def kind(self):
            return self._kind
        @property
        def value(self):
            return self._value
        @property
        def zero_plus(self):
            return self._zero_plus
        @property
        def ordinal(self):
            return self._ordinal
            
            
class TriDict:
    """
    (index, meta, ordinal)
    """
    def __init__(self):
        self._data = []
        
    def add(self, index, meta, ordinal):
        self._data.append((index, meta, ordinal))
        
    def index_to_meta(self, index):
        for i, j, o in self._data:
            if i == index:
                return j
        return None
        
    def meta_to_index(self, index):
        for i, j, o in self._data:
            if j == index:
                return i
        return None
        
    def ordinal_to_index(self, ordinal):
        for i, j, o in self._data:
            if o == ordinal:
                return i
        return None
        
    def index_to_ordinal(self, index):
        for i, j, o in self._data:
            if i == index:
                return o
        return None
        
    def ordinal_to_meta(self, ordinal):
        for i, j, o in self._data:
            if o == ordinal:
                return j
        return None
        
    def meta_to_ordinal(self, index):
        for i, j, o in self._data:
            if j == index:
                return o
        return None
        
    
class Matcher:
    """
    Attributes:
    --------------------------
    context: list of Segment/boundry
        This should be a reference to the original context, so don't change
        anything in it. We're going to be making a lot of Matchers, so we
        really don't want to clone this
    environment: Environment
        The Environment to be matched
    i: int
        The index currently being operated on
    _start_i: int
        Original value of i. We need this for making the range in the Match
        object at the end.
    reverse: bool
        if True will attempt to match from right end of Environment and i
        will decrement instead of increment. Also Match object range will
        be reversed (i, _start_i)
        
    matchli: list of Segment/boundaries
        Working list of match in context
    
    indexes: TriDict
        3-way map matching indexes in matchli, to environment, to ordinals.
        Only instantiated in fixed-width environments
    """
    def __init__(self, context, environment, i, reverse=False):
        self.context = context
        self.environment = environment
        self.i = i
        self._start_i = i
        self.reverse = reverse
        
        self.matchli = []
        self.greek = {}
        
        self.indexes = None
        if self.environment.is_fixed and not self.reverse:
            self.indexes = TriDict()
            
        if self.reverse:
            self.environment = self.environment.inverse()
        vpr("    MATCHER {} ON: {}".format(
            self.environment,
            "".join([str(x) for x in 
                (self.context[:self.i+1] if self.reverse else self.context[self.i:])
            ]),
            i=self.environment._depth
        ))
        
    def _is_end_of_context(self):
        if (not self.reverse and self.i >= len(self.context)) \
                or (self.reverse and self.i < 0):
            vpr("    end of context", i=self.environment._depth)
            return True
        return False
        
    def match(self):
        meta_index = 0
        while True:
            # have we reached the end of the environment?
            if meta_index >= len(self.environment):
                break
        
            node = self.environment[meta_index]
            vpr("    env index {}: {}".format(meta_index, node), i=self.environment._depth)
            
            if self._is_end_of_context():
                return None
            # Add boundaries to matchli if needed
            if self.environment.crosses_boundaries:
                vpr("    skipping boundaries...", i=self.environment._depth)
                while self.context[self.i] in BOUNDARIES:
                    vpr("      i:{} is boundary {}".format(self.i, self.context[self.i]), i=self.environment._depth)
                    self.matchli.append(self.context[self.i])
                    self.i += -1 if self.reverse else 1
                    if self._is_end_of_context():
                        return None
            
            vpr("    i is {}".format(self.i), i=self.environment._depth)
            vpr("    does {} match {}".format(node, self.context[self.i]), i=self.environment._depth)
            matches = self.match_node(node, meta_index)
            vpr("      {}".format(matches), i=self.environment._depth)
            if node.zero_plus:
                if not matches:
                    vpr("    zp match end", i=self.environment._depth)
                    meta_index += 1
                else:
                    vpr("    zp match...", i=self.environment._depth)
            else:
                if not matches:
                    vpr("    no match, returning None", i=self.environment._depth)
                    return None
                vpr("      match", i=self.environment._depth)
                meta_index += 1
                
        vpr("    match!", i=self.environment._depth)
        match = Match(
            tuple(self.matchli),
            (self._start_i, self.i),
            self.indexes,
            self.greek
        )
        if self.reverse:
            match.reverse()
        return match
        
    def match_node(self, node, meta_index):
        if node.kind == Environment.Node.SEGMENT:
            matches = self.match_segment_node(node, meta_index)
        elif node.kind == Environment.Node.NULL:
            matches = self.match_null_node(node, meta_index)
        elif node.kind == Environment.Node.BOUNDARY:
            matches = self.match_boundary_node(node, meta_index)
        elif node.kind == Environment.Node.OPTIONAL:
            matches = self.match_optional_node(node)
        elif node.kind == Environment.Node.POSSIBILITIES:
            matches = self.match_possibilities_node(node)
        return matches
        
    def match_segment_node(self, node, meta_index):
        seg = self.context[self.i]
        if seg in BOUNDARIES:
            vpr("    seg in boundaries: {}".format(seg), i=self.environment._depth)
            return False
        if not node.value.matches(seg, greek=self.greek):
            vpr("    seg does not match: {}".format(seg), i=self.environment._depth)
            return False
        self.matchli.append(self.context[self.i])
        
        if self.environment.is_fixed and self.indexes:
            match_index = len(self.matchli) - 1
            self.indexes.add(match_index, meta_index, node.ordinal)
                
        self.set_greek(node, seg)
        self.i += -1 if self.reverse else 1
        return True
        
    def set_greek(self, node, segment):
        for feat, value in node.value.items():
            if value in GREEK and value not in greek:
                self.greek[value] = segment[feat]
            
    def match_null_node(self, node, meta_index):
        self.matchli.append(NULL)
        
        if self.environment.is_fixed and not self.reverse:
            match_index = len(self.matchli) - 1
            self.indexes.add(match_index, meta_index, node.ordinal)
            
        return True
    
    def match_boundary_node(self, node, meta_index):
        if node.value == SYLL_B:
            if self.context[self.i] not in (SYLL_B, WORD_B):
                return False
        elif node.value != self.context[self.i]:
            return False
        self.matchli.append(self.context[self.i])
        
        if self.environment.is_fixed and not self.reverse:
            match_index = len(self.matchli) - 1
            self.indexes.add(match_index, meta_index, node.ordinal)
        
        self.i += -1 if self.reverse else 1
        return True
                
    def match_optional_node(self, node):
        vpr("    checking optional node...", i=self.environment._depth)
        matcher = Matcher(self.context, node.value, self.i, reverse=self.reverse)
        m = matcher.match()
        if m is None:
            vpr("    optional node nbd", i=self.environment._depth)
            return True
        self.matchli += m.matchli
        self.i = m.range[0 if self.reverse else 1]
        vpr("    optional node match!", i=self.environment._depth)
        return True
    
    def match_possibilities_node(self, node):
        for env in node.value:
            matcher = Matcher(self.context, env, self.i, reverse=self.reverse)
            m = matcher.match()
            if m is not None:
                self.matchli += m.matchli
                self.i = m.range[0 if self.reverse else 1]
                return True
        return False


class Match:
    def __init__(self, matchli, range, indexes, greek):
        self.matchli = matchli
        self.range = range
        self.indexes = indexes
        self.greek = greek
        
    def reverse(self):
        self.matchli = tuple(reversed(self.matchli))
        self.range = (self.range[1], self.range[0])
        
    def __len__(self):
        return len(self.matchli)
        
    def __getitem__(self, i):
        return self.matchli[i]


class Transformation:
    def __init__(self, nodes, depth=0):
        self.nodes = nodes
        self._depth = depth
        
    @classmethod
    def from_environment(self, env):
        return Transformation([
            Transformation.Node.from_environment_node(node) for node in env.nodes
        ])
        
    def __str__(self):
        return "".join([
            str(node) for node in self.nodes
        ])
        
    def __eq__(self, other):
        vpr(
            "Transformation {} == {} eq:".format(self, other),
            "isinstance", isinstance(other, Transformation),
            "nodes:", self.nodes == other.nodes
        )
            
        if not isinstance(other, Transformation):
            return False
        return self.nodes == other.nodes
    
    class Node:
        METASEGMENT = 1
        NULL = 2
        BOUNDARY = 3
        SEGMENT = 4
        STATIC = 5
        
        def __init__(self, kind, value, ordinal=None):
            self._kind = kind
            self._value = value
            self._ordinal = ordinal
            
        def __eq__(self, other):
            vpr(
                "TNode {} == {}".format(self, other),
                "isinstance {} == {}".format(type(self), type(other)), isinstance(other, Transformation.Node),
                "kind", self._kind == other._kind,
                "value", self._value == other._value,
                "ordinal", self._ordinal == other._ordinal
            )
            if not isinstance(other, Transformation.Node):
                return False
            return (
                self._kind == other._kind and \
                self._value == other._value and \
                self._ordinal == other._ordinal
            )
            
        def __str__(self):
            s = None
            if self.kind == self.METASEGMENT or self.kind == self.SEGMENT:
                if self.value.ipa is not None:
                    s = self.value.ipa
                    s = "[" + s + "]"
                else:
                    li = []
                    for feat, val in self.value.data.items():
                        if val == 1:
                            val = "+"
                        elif val == -1:
                            val = "-"
                        li.append("{}{}".format(val, feat))
                    if self.value.stress is not None:
                        if len(self.value.stress) == 1:
                            li.append("stress={}".format(self.value.stress[0]))
                        else:
                            li.append("stress=[{}]".format(",".join([str(s) for s in self.value.stress])))
                    s = "[{}]".format(", ".join(li))
            elif self.kind == self.NULL:
                s = NULLSIGN
            elif self.kind == self.BOUNDARY:
                if self.value == WORD_B:
                    s = "#"
                elif self.value == SYLL_B:
                    s = "$"
                elif self.value == MORPHEME_B:
                    s = "+"
            elif self.kind == self.STATIC:
                s = STATICSIGN
            if self.ordinal is not None:
                s = "{}:{}".format(self.ordinal, s)
            return s
        
        @property
        def kind(self):
            return self._kind
        @property
        def value(self):
            return self._value
        @property
        def ordinal(self):
            return self._ordinal
            
        def apply(self, segment, core_node, greek=None):
            if self.kind == self.STATIC:
                return segment
            if self.kind != self.METASEGMENT:
                return self.value
            vpr("new seg: {}  value: {}".format(type(segment), type(self.value)))
            new_seg = segment.update(self.value, greek=greek)
            if core_node.value.bracketed:
                if core_node.value.bracketed.matches(seg):
                    new_seg = new_seg.update(self.value.bracketed, greek=greek)
            return new_seg
            
    def __len__(self):
        return len(self.nodes)
    
    def __getitem__(self, i):
        return self.nodes[i]
            
    def apply(self, core_match, core):
        vpr("\nApplying Transformation to {}...".format("".join(str(x) for x in core_match)))
        result = []
        ii = 0
        for t, t_node in enumerate(self.nodes):
            vpr("  {}".format(t_node))
            # Load boundaries if applicable
            vpr("    last i: {}".format(ii))
            if core.crosses_boundaries:
                while ii < len(core_match) and core_match[ii] in BOUNDARIES:
                    vpr("      loading boundary {}".format(core_match[ii]))
                    result.append(core_match[ii])
                    ii += 1
                
            o = t_node.ordinal
            if o is not None:
                j = core_match.indexes.ordinal_to_meta(o)
                vpr("    ordinal {} == meta {}".format(o, j))
            else:
                j = t
                vpr("    no ordinal == meta {}".format(j))
            core_node = core[j]
            vpr("    core node: {}".format(core_node))
            
            i = core_match.indexes.meta_to_index(j)
            vpr("    index == {}".format(i))
            ii = i + 1
            seg = core_match[i]
            vpr("    core match segment == {}".format(seg))
            
            vpr("    applying {} to {}".format(t_node, seg))
            new_seg = t_node.apply(seg, core_node, greek=core_match.greek)
            vpr("      result: {}".format(new_seg))
            result.append(new_seg)
            vpr("  {}".format("".join(str(x) for x in result)))
            
        # Load any remaining boundaries before the end
        if core.crosses_boundaries:
            vpr("    last i: {}".format(ii))
            while ii < len(core_match) and core_match[ii] in BOUNDARIES:
                vpr("      final loading boundary {}".format(core_match[ii]))
                result.append(core_match[ii])
                ii += 1
                
        vpr("completed: {}".format("".join(str(x) for x in result)))
        return result
