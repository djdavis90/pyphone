"""
Wrapper for panphon Segment object that allows it to be
initialized with a dict or a str without having to supply
names of all segments.
"""

from panphon.segment import Segment as _Segment
try:
    import regex as re
except ImportError:
    import re
from init import *


class AbstractSegment(_Segment):
    """
    Parent class of Segment and MetaSegment.
    """
    S2N = {"+": 1, "-": -1, "0": 0}
    N2S = {1: "+", -1: "-", 0: "0"}
    def __init__(self, features, stress=None, ipa=None):
        self.stress = stress
        self.ipa = ipa
        
        if isinstance(features, dict):
            names = list(features.keys())
            
        elif isinstance(features, str):
            d = {}
            for m in re.finditer(r"'(\+|0|-)(\w+)", features):
                d[m.group(1)] = m.group(2)
            features = d
            names = list(features.keys())
            
        else:
            raise ValueError("Segment must be initalized with type str or dict, not '%s'" % type(features))
        
        _Segment.__init__(self, names, features=features)
        
    def is_subsegment(self, other):
        """returns True if self is a subsegment of other. That is, all
        features in other are present in, and the same value as self"""
        for feat, val in other.iteritems():
            if val != self[feat]:
                return False
        if other.stress is not None and self.stress != other.stress:
            return False
        return True
        
    def get_hash(self):
        return hash(frozenset(self.data.items()))
        
    _STRESS_D = {0:-1, None:0, 1:1, 2:1}
    def __getitem__(self, k):
        if k == "stress":
            return self._STRESS_D[self.stress]
        return _Segment.__getitem__(self, k)
        
    
    def get(self, k, default=None):
        return self.data.get(k, default)
        
    def copy(self):
        seg = Segment(self.data, stress=self.stress, ipa=self.ipa)
        return seg
        
    def __str__(self):
        if self.ipa is not None:
            return self.ipa
        return _Segment.__str__(self)
                

class Segment(AbstractSegment):
    """
    Represents a complete phonological segment. Differs from MetaSegment in that
    1) Segment must have a + or - in self.data for ALL features. This
    represents a complete segment, not a transformation or environment, and
    2) Segment stress is an int (or None if the segment is -syl)
    """
    def __init__(self, features, stress=None, ipa=None):
        AbstractSegment.__init__(self, features, stress=stress, ipa=ipa)
        if set(self.data.keys()) != FEATURESET:
            missing_feats = set()
            extra_feats = set()
            for feat in self.data.keys():
                if feat not in FEATURESET:
                    print("EXTRA FEAT: '{}'".format(feat))
                    extra_feats.add(feat)
            for feat in FEATURESET:
                if feat not in self.data:
                    missing_feats.add(feat)
            error = []
            if missing_feats:
                error.append("missing feats: [{}]".format(", ".join(missing_feats)))
            if extra_feats:
                error.append("extra feats: [{}]".format(", ".join(missing_feats)))
            error = "  ".join(error)
            raise ValueError("Instantiating full Segment with featureset that does not match default. {}".format(error))
        if self.stress not in (None, 0, 1, 2):
            raise ValueError("Segment stress must be 0, 1, 2, or None.")
            
    def __eq__(self, other):
        if not isinstance(other, Segment):
            return False
        return self.stress == other.stress and self.data == other.data
        
    def update(self, other, greek=None):
        odata = other.data if isinstance(other, Segment) else other
        if greek:
            for feat, value in odata.items():
                if value in greek:
                    odata[feat] = greek[value]
        data = self.data.copy()
        for feat, val in odata.items():
            data[feat] = val
        return Segment(data, stress=self.stress)
        
    def copy(self):
        return Segment(self.data, stress=self.stress, ipa=self.ipa)


class MetaSegment(AbstractSegment):
    """
    Represents a cluster of features that may not be a complete segment. Can
    be used for environment matching and transformations. Differs from Segment:
    1) does not need a value in self.data for every feature, or even any feature
    2) Values in self.data can be greek letters, meaning their +/- value is
    dependent on something else.
    3) MetaSegment stress is a set of ints (or None) OR an int if being used
    for transformation
    4) Has a bracketed value (MetaSegment or None) representing optional features
    """
    def __init__(self, features, stress=None, bracketed=None, ipa=None):
        AbstractSegment.__init__(self, features, stress=stress, ipa=ipa)
        for feat in self.data:
            if feat not in FEATURESET:
                raise ValueError("Feature '{}' does not exist in default featureset".format(feat))
        if isinstance(self.stress, int):
            self.stress = set([self.stress])
        self.bracketed = bracketed
        
    def __eq__(self, other):
        if not isinstance(other, MetaSegment):
            return False
        return self.stress == other.stress and self.data == other.data
        
    def matches(self, segment, greek=None):
        for feat in self.data:
            if isinstance(self[feat], str):
                # skips Greek values
                continue
            if segment[feat] != self[feat]:
                vpr("no match on feat:", feat)
                return False
                
        if greek:
            for feat in self.data:
                if self[feat] not in greek:
                    continue
                if segment[feat] != greek[self[feat]]:
                    vpr("no match on feat:", feat, "(greek)")
                    return False
                
        if self.stress is not None:
            if segment.stress not in self.stress:
                vpr("no match on stress:", self.stress, "vs", segment.stress)
                return False
        return True
        
    def transform(self, segment, greek=None):
        new_data = dict(segment.data)
        for feat, v in self.data.items():
            if v in greek:
                v = greek[v]
            new_data[feat] = v
            
            if self.stress is None:
                new_stress = segment.stress
            else:
                if not isinstance(self.stress, int):
                    raise ValueError(
                        "MetaSegments used for Transformation must have stress of 0, 1, or 2, not of type {}".format(type(self.stress))
                    )
                new_stress = self.stress
        return Segment(new_data, stress=new_stress)
        
    def __repr__(self):
        """Return a string representation of a feature vector"""
        pairs = [(self.n2s.get(self.data[k], self.data[k]), k) for k in self.names]
        fts = ', '.join(['{}{}'.format(*pair) for pair in pairs])
        return '<Segment [{}]>'.format(fts)
    


