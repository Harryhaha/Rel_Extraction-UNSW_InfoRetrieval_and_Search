# -*- coding: utf-8 -*-

# Relation Extraction Skeleton
# ==========================================
#
# Author: Jianbin Qin <jqin@cse.unsw.edu.au>

from nltk.parse.stanford import StanfordDependencyParser


# Please download from http://nlp.stanford.edu/software/ and put it
# somewhere you can access. Change this value accordingly.
STANFORD_PARSER_ROOT = "../stanford-corenlp-full-2015-12-09/"

STANFORD_PARSER_JAR = STANFORD_PARSER_ROOT + 'stanford-corenlp-3.6.0.jar'
STANFORD_PARSER_MODEL = STANFORD_PARSER_ROOT + 'stanford-corenlp-3.6.0-models.jar'


from nltk.parse.stanford import StanfordDependencyParser
# You can import this variable to use stanford_dependacy_parser
# stanford_dependency_parser = StanfordDependencyParser(path_to_jar=STANFORD_PARSER_JAR,
#                                              path_to_models_jar=STANFORD_PARSER_MODEL)

from nltk.parse.stanford import StanfordParser

# You can import this variable to use stanford_constituent_parser
# stanford_constituent_parser = StanfordParser(path_to_jar=STANFORD_PARSER_JAR, path_to_models_jar=STANFORD_PARSER_MODEL)

import spacy
# from spacy.attrs import ENT_TYPE, ENT_IOB
# from spacy.symbols import *


# You can import this variable to use spacy.
spacynlp = spacy.load('en')