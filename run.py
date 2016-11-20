# -*- coding: utf-8 -*-

# Relation Extraction Skeleton
# ==========================================
#
# Author: Jianbin Qin <jqin@cse.unsw.edu.au>

# THIS IS PART OF SKELETON
# DO NOT CHANGE THIS FILE


# The main file of running the relation extraction.
# To run it:
# python3 run.py training.json

import argparse
import os
import json
import sys
import pprint

def load_data(filename):
    """
    This function read a json file and check if this data is a valid
    data file for 6714 16s2 project input file.
    :param filename:
    :return: A list of sentence records.
    """
    if not os.path.exists(filename):
        return None
    try:
        json_data = open(filename).read()
        data = json.loads(json_data)
        return data
    except IOError:
        print('Oops! {0} cannot open.'.format(filename))
    except:
        print("Unexpected error:", sys.exc_info()[0])
        raise


def extraction_relations(record):
    """
    This function read a sentence record and then call the extraction function in the
    extractor modules to extract relations.
    :param record: The sentence record.
    :return: A list of relations.
    """
    results = []

    from extractor import extract_date_of_birth, extract_has_parent

    # Extract DateOfBrith relations.
    results.extend(extract_date_of_birth(record['sentence']))

    # Extract Parent relations.
    results.extend(extract_has_parent(record['sentence']))

    return results


def calculate_f1_score(data, results, predicate="DateOfBirth"):
    """
    Calculate F1 score for given relations.
    Returns:
        Precision, Recall, F1.
    """

    # Initialize Counters.
    number_of_correct = 0
    number_of_incorrect = 0
    number_of_ground = 0
    number_of_extracted = 0
    number_of_missing = 0

    # print (results)
    for i in range(len(data)):

        # Get the ground truth relations of certain predicate type.
        ground_relations = [(x['subject'].lower().replace(' ', ''), x['predicate'].lower(),
                             x['object'].lower().replace(' ', '')) for x in data[i]["relations"]
                            if x['predicate'].lower() == predicate.lower()]

        # Get the extracted relations of certain predicate type.
        extracted_relations = [(x.subject.lower().replace(' ', ''), x.predicate.lower(),
                                x.object.lower().replace(' ', '')) for x in results[i]
                               if x.predicate.lower() == predicate.lower()]

        # Perform set operations.
        ground_relations_set = set([x[0] + x[1] + x[2] for x in ground_relations])
        extracted_relations_set = set([x[0] + x[1] + x[2] for x in extracted_relations])
        correct_relations_set = ground_relations_set.intersection(extracted_relations_set)
        incorrect_relations_set = set(extracted_relations_set - ground_relations_set)
        missing_relations_set = set(ground_relations_set - extracted_relations_set)


        ####################### DEBUG #######################
        # if len(incorrect_relations_set) != 0:
        #     print("---------- incorrect_relations_set ------------")
        #     print("st ID: " + data[i]["sentence_id"])
        #     print(incorrect_relations_set)

        # if len(missing_relations_set) != 0:
        #     print("---------- missing_relations_set ------------")
        #     print("st ID: " + data[i]["sentence_id"])
        #     print(missing_relations_set)
        ####################### DEBUG #######################


        # Modify counters.
        number_of_extracted += len(extracted_relations_set)
        number_of_ground += len(ground_relations_set)
        number_of_correct += len(correct_relations_set)
        number_of_incorrect += len(incorrect_relations_set)
        number_of_missing += len(missing_relations_set)

    # Calculate the precision, recall and f1.
    precision = number_of_correct * 1.0 / number_of_extracted if number_of_extracted > 0 else 0
    recall = (number_of_ground - number_of_missing) * 1.0 / number_of_ground if number_of_extracted > 0 else 0
    f1 = (2 * precision * recall) / (precision + recall) if precision + recall > 0 else 0

    return precision, recall, f1


def run(filename):
    """
    Calculate F1 score for given relations.
    Returns:
        scores: A dictionary contains Precision, Recall, F1.
        allresults: A list of all extracted results.
    """
    allresults = []
    data = load_data(filename)
    # data = data[:100]
    for rcd in data:
        try:
            results = extraction_relations(rcd)
            allresults.append(results)
        except:
        #     Ignore all exceptions and continue.
        #     print("Exception sentence:")
        #     print(rcd['sentence_id'])
            allresults.append([])

    scores = {}
    p, r, f1 = calculate_f1_score(data, allresults, 'DateOfBirth')
    scores['DateOfBirth'] = {"Precision": p, "Recall": r, "F1": f1}

    p, r, f1 = calculate_f1_score(data, allresults, 'HasParent')
    scores['HasParent'] = {"Precision": p, "Recall": r, "F1": f1}

    return scores, allresults

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--verbose", help="increase output verbosity",
                        action="store_true")
    parser.add_argument("input", type=str,
                        help="The input json file location.")
    args = parser.parse_args()
    filename = args.input
    scores, *_ = run(filename)

    with open('score_output.json', 'w') as outfile:
        json.dump(scores, outfile, indent=4)

    # Print to the screen.
    pp = pprint.PrettyPrinter(indent=4)
    pp.pprint(scores)
