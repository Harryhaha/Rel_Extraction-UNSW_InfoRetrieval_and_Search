# -*- coding: utf-8 -*-

# Relation Extraction Skeleton
# ==========================================
#
# Author: Jianbin Qin <jqin@cse.unsw.edu.au>

from relation import Relation

def extract_date_of_birth(sentence):
    predicate = "DateOfBirth"
    results = []

    ############################################################
    from my_extractor import date_of_birth_extractor

    results.extend( date_of_birth_extractor(sentence) )
    ############################################################

    return results


def extract_has_parent(sentence):
    predicate = "HasParent"
    results = []

    ############################################################
    from my_extractor import has_parent_extractor

    results.extend( has_parent_extractor(sentence) )
    # results.extend( has_parent_extractor_denpendency_parse(sentence) )
    ############################################################

    return results
