__author__ = "Harry"

from relation import Relation

import re
from collections import defaultdict

from config import spacynlp
# from config import ENT_TYPE, ENT_IOB
# from config import PERSON, ORG

from numpy import ndarray
import spacy.tokens


################################################ Utility functions below ###############################################

###############################################################################
# Transform the original annotations, grouping the sub-NE into one, and keep
# the non-NE as it is, to finally make a new real annnotation list for
# further processing
###############################################################################
def transform_annotations(annotations):
    NE_annotations = []
    NE_tag = None
    for i in range(len(annotations)):
        if annotations[i][4].startswith("B-"):
            NE_tag = annotations[i][4][2:]
            start = i
        elif annotations[i][4] == 'O':
            if NE_tag is not None:
                annotation_tuple = ( start, i-1, NE_tag, ' '.join([ x[1] for x in annotations[start: i]]),
                                     [x[3] for x in annotations[start: i]] )
                NE_annotations.append( annotation_tuple )

            NE_annotations.append( (i, i, "O", annotations[i][1], [annotations[i][3]]) )
            NE_tag = None
    if NE_tag is not None:
        annotation_tuple = (start, len(annotations)-1, NE_tag, ' '.join([x[1] for x in annotations[start: len(annotations)]]),
                            [x[3] for x in annotations[start: len(annotations)]])
        NE_annotations.append(annotation_tuple)

    return NE_annotations


def group_every_pair_of_NE_in_order( NE_annotations ):
    rel_dict_collection_dict = defaultdict(dict)
    index = 0
    for i in range(len(NE_annotations) - 1):
        if NE_annotations[i][2] == 'O': continue

        rel_dict_group = []
        for j in range(i + 1, len(NE_annotations)):
            if NE_annotations[j][2] == 'O': continue

            rel_dict = defaultdict(str)

            rel_dict['subject_left_text'] = " ".join([x[3] for x in NE_annotations[0:i]])  # Could be empty string
            rel_dict['subject_left_term'] = (
            " ".join([x[3] for x in NE_annotations[0:i]])).lower()  # Could be empty string

            rel_dict['subject_text'] = NE_annotations[i][3]
            rel_dict['subject_term'] = NE_annotations[i][3].lower()
            rel_dict['subject_class'] = NE_annotations[i][2]

            rel_dict['filler_text'] = " ".join([x[3] for x in NE_annotations[i + 1:j]])
            rel_dict['filler_term'] = " ".join([x[3] for x in NE_annotations[i + 1:j]]).lower()

            rel_dict['object_text'] = NE_annotations[j][3]
            rel_dict['object_term'] = NE_annotations[j][3].lower()
            rel_dict['object_class'] = NE_annotations[j][2]

            rel_dict['object_right_text'] = " ".join([x[3] for x in NE_annotations[j + 1:]])
            rel_dict['object_right_term'] = (" ".join([x[3] for x in NE_annotations[j + 1:]])).lower()

            rel_dict_group.append(rel_dict)

        rel_dict_collection_dict[index] = rel_dict_group
        index += 1
    return rel_dict_collection_dict

################################################ Utility functions below ###############################################





################################################## DOB extractor below #################################################

def date_of_birth_extractor(sentence, predicate='DateOfBirth', window=5):
    text = sentence['text']
    annotations = sentence['annotation']

    NE_annotations = transform_annotations(annotations)

    rel_dict_collection_dict = group_every_pair_of_NE_in_order(NE_annotations)
    # print(rel_dict_collection_dict)

    date_of_birth_class = Date_of_birth_rule()  # Initialize the rule class

    i = 0
    relation_results = []
    while i < len(rel_dict_collection_dict):
    # for i in range(len(rel_dict_collection_dict)):
        if len(rel_dict_collection_dict[i]) == 0:
            i += 1
            continue

        if rel_dict_collection_dict[i][0]['subject_class'] == 'PERSON':
            flag_skip = False
            rel_dict_list = rel_dict_collection_dict[i]
            for j in range(len(rel_dict_list)):
                if rel_dict_list[j]['object_class'] == 'DATE':
                    (object_list_for_subject, index_delimite) = \
                        date_of_birth_class.pos_rule_dict['person_born_or_birth_date'](rel_dict_list[j], i, j, rel_dict_collection_dict)
                    if object_list_for_subject is None:
                        continue

                    i = index_delimite
                    flag_skip = True
                    for item in object_list_for_subject:
                        rel = Relation( rel_dict_list[j]['subject_text'], predicate, item )
                        relation_results.append(rel)
                    break
            if flag_skip is False:
                i += 1

        elif rel_dict_collection_dict[i][0]['subject_class'] == 'DATE':
            rel_dict_list = rel_dict_collection_dict[i]
            for j in range(len(rel_dict_list)):
                if rel_dict_list[j]['object_class'] == 'PERSON':
                    (subject_for_object, index_delimite) = \
                        date_of_birth_class.pos_rule_dict['born_or_birth_date_person'](rel_dict_list[j], i, j, rel_dict_collection_dict)
                    if subject_for_object is not None:
                        i = index_delimite
                        rel = Relation( subject_for_object, predicate, rel_dict_list[j]['subject_text'] )
                        relation_results.append(rel)
                        break

                    (subject_for_object, index_delimite) = \
                        date_of_birth_class.pos_rule_dict['date_person_born_or_birth'](rel_dict_list[j], i, j, rel_dict_collection_dict)
                    if subject_for_object is not None:
                        i = index_delimite
                        rel = Relation( subject_for_object, predicate, rel_dict_list[j]['subject_text'])
                        relation_results.append(rel)
                        break
                continue
            i += 1

        else:
            i += 1


    # DEBUG:
    # for item in relation_results:
    #     test = item
    #     print(test)

    return relation_results



class Date_of_birth_rule():
    def __init__(self):

        self.window_rule1 = 7
        self.window_bornOrBirth_and_Date = 7

        self.punct = re.compile(r'\,', re.IGNORECASE)
        self.double_comma = re.compile(r',.*?,', re.IGNORECASE)

        self.rule_born_or_birth_regex_for_Basic = re.compile(r'\bborn\b|\bbirth\b|\bbirthday\b', re.IGNORECASE)
        self.rule_born_or_birth_regex_for_And = re.compile(r'\band\b', re.IGNORECASE)
        self.rule_born_or_birth_regex_for_But = re.compile(r'\bbut\b|\bwhile\b|\balthough\b|\bhowever\b', re.IGNORECASE) # Cannot determine by rule in this case

        self.pos_rule_dict = {
            "person_born_or_birth_date": self._rule_pos_person_born_or_birth_date,

            "born_or_birth_date_person": self._rule_pos_born_or_birth_date_person,
            "date_person_born_or_birth": self._rule_pos_date_person_born_or_birth,
        }

        # self.neg_rule_list = []


    def rule_neg_LifeSpan(self, relation_dict):
        pass
    ######################################################################
    # Below are three summarized rules:
    ######################################################################

    ############################### Rule 1 ###############################
    def _rule_pos_person_born_or_birth_date(self, relation_dict, outer_index, inner_index, rel_dict_collection_dict):
        if not self.rule_born_or_birth_regex_for_Basic.search( relation_dict['filler_term'] ):
            return ( None, None )

        # Already reach the last possible relation
        length = len(rel_dict_collection_dict)

        if (outer_index+inner_index+1  +  1) >= (length-1):
        # if (outer_index + inner_index + 1 + 1) >= (length - 1):
            return ( [relation_dict['object_text']], length )


        # To do: (avoid LifeSpan)


        index_delimite = None
        flag_unique_answer = False

        object_list_for_subject = [relation_dict['object_text']]

        # object_right_side_rel_dict_collection = rel_dict_collection_dict[ inner_index+outer_index+1  +  1 ]
        object_right_side_rel_dict_collection = rel_dict_collection_dict[ inner_index+outer_index+1 ]

        for i in range(len(object_right_side_rel_dict_collection)):

            # The object class is Date entity
            # This branch often indicated need to be further checked
            if object_right_side_rel_dict_collection[i]['object_class'] == 'DATE':

                # The filler term contains word "and"
                # This case often indicates only left side Date entity(entities) visited before are the anwsers
                if self.rule_born_or_birth_regex_for_And.search(
                    object_right_side_rel_dict_collection[i]['filler_term']
                ):
                    # Should store the current already processed index(items)
                    index_delimite = inner_index+outer_index+1  +  i  +  1
                    # Should return now and do the next IE extraction
                    return (object_list_for_subject, index_delimite)


                # The filler term between any two Date entity contains "but", "while"....
                # This case cannot determine by the rules method, using classification algorithms instead later...
                if self.rule_born_or_birth_regex_for_But.search(
                    object_right_side_rel_dict_collection[i]['filler_term']
                ):
                    pass # To to later


                # This object right side terms within specified window size contain word "born" or "birth" or "birthday"
                # This case often indicates only its left side Date entity is the answer
                # Also, set the "flag_unique_answer" to be True, to avoid adding other Date entities during further
                # iterations, because iteration still need to keep on until the current visiting entity is not Date anymore
                if self.rule_born_or_birth_regex_for_Basic.search(
                    object_right_side_rel_dict_collection[i]['object_right_term'][0: self.window_rule1]
                ):
                    flag_unique_answer = True
                    object_list_for_subject = [ object_right_side_rel_dict_collection[i]['object_text'] ]


                # Above cases are all skipped
                # This case often indicates this Date is also the answer
                # except that the flag "flag_unique_answer" is True set by the above case
                if flag_unique_answer is False:
                    object_list_for_subject.append( object_right_side_rel_dict_collection[i]['object_text'] )

            # The object class is not Date entity
            # This branch often indicates exit the iterations and return
            # means later entities has no relationship with the subject class
            else:
                index_delimite = inner_index+outer_index+1  +  i  +  1  # return the current processed index
                return (object_list_for_subject, index_delimite)



    ############################### Rule 2 ###############################
    def _rule_pos_born_or_birth_date_person(self, relation_dict, outer_index, inner_index, rel_dict_collection_dict):
        if not self.rule_born_or_birth_regex_for_Basic.search( relation_dict['subject_left_text'] ):
            return ( None, None )
        return ( relation_dict['object_text'], outer_index+inner_index+1  +  1 )


    ############################### Rule 3 ###############################
    def _rule_pos_date_person_born_or_birth(self, relation_dict, outer_index, inner_index, rel_dict_collection_dict):
        if not self.rule_born_or_birth_regex_for_Basic.search( relation_dict['object_right_text'] ):
            return ( None, None )
        return ( relation_dict['object_text'], outer_index+inner_index+1  +  1 )

################################################## DOB extractor above #################################################






################################################## HP extractor below #################################################

def apply_rules(relation_dict, parent_rule_object, outer_index, inner_index, whole_relations, relation_results_tmp,
                predicate, relation_results):
    rule_dict = parent_rule_object.pos_rule_dict
    for rule_F in rule_dict:
        (object_list_for_subject, index_delimite, flag_grandRelation, object_list_for_newSubject) = \
            rule_F(relation_dict, outer_index, inner_index, whole_relations )
        if object_list_for_subject is not None:
            for item in object_list_for_subject:
                rel = Relation(relation_dict['subject_text'], predicate, item)
                # Add the existing relations first then check grandRelation(in the case of only one parent appears before) next
                relation_results_tmp.append(rel)

            # This is for grandRelation extraction(in the case of only one parent appears before)
            # although in training data there is no such instances yet
            for rel in relation_results:
                for item in object_list_for_newSubject:
                    if rel.object.lower().split()[-1] == item.lower().split()[-1]:
                        rel = Relation(rel.object, predicate, item)
                        relation_results_tmp.append(rel)


            # Exit the whole while loop since it has already check all entities and no satisfaction
            if index_delimite == -1:
                return (relation_results_tmp, -1)
            # if flag_grandRelation is True:
            #     index_delimite =
            i = index_delimite
            return (relation_results_tmp, i)
    return (relation_results_tmp, 0)

def has_parent_extractor(sentence, predicate='HasParent'):
    text = sentence['text']
    annotations = sentence['annotation']

    NE_annotations = transform_annotations(annotations)
    rel_dict_collection_dict = group_every_pair_of_NE_in_order(NE_annotations)

    has_parent_class = Has_parent_rule()  # Initialize the rule class

    i = 0
    relation_results = []
    while i < len(rel_dict_collection_dict):
        if len(rel_dict_collection_dict[i]) == 0:
            i += 1
            continue

        if rel_dict_collection_dict[i][0]['subject_class'] == 'PERSON':
            if has_parent_class.within_left_bracket.search( rel_dict_collection_dict[i][0]['subject_left_term']) and \
               has_parent_class.within_right_bracket.search( rel_dict_collection_dict[i][0]['filler_term']):
                i += 1
                continue  # If this PERSON is within bracket, then it is very likely not the target relation
            # Now make sure that first PERSON entity as children candidate does exist
            # Another possibility is that the person is already the grandRelation with the previous PERSON now

            ################ First senario: the person is potentially the first grandRelation ################
            if has_parent_class.rule_grandRelation_regex.search( rel_dict_collection_dict[i][0]['subject_left_term'] ):
                flag_exit_all = False

                rel_dict_list = rel_dict_collection_dict[i]
                (relation_results_tmp, index_delimite) = has_parent_class._rule_find_grandRelation(
                    rel_dict_list, i, rel_dict_collection_dict, relation_results, predicate)
                relation_results.extend(relation_results_tmp)
                if index_delimite == -1:
                    break
                i = index_delimite
                continue
            ################ First senario: the person is potentially the first grandRelation ################


            ###################### Second senario: the person is potentially the child #######################
            flag_skip = False
            flag_exit_all = False
            rel_dict_list = rel_dict_collection_dict[i]
            for j in range(len(rel_dict_list)):
                if rel_dict_list[j]['object_class'] == 'PERSON':
                    if has_parent_class.within_left_bracket.search(rel_dict_list[j]['filler_term']) and \
                       has_parent_class.within_right_bracket.search(rel_dict_list[j]['object_right_term']):
                        continue  # If this PERSON is within bracket, then it is very likely not the target relation
                    # Now we are sure that second PERSON entity as first parent candidate does exist
                    ######### Now need to check through four summarized rules one by one #########
                    relation_results_tmp = []
                    (relation_results_tmp, index_delimite) = apply_rules(
                        rel_dict_list[j], has_parent_class, i, j, rel_dict_collection_dict, relation_results_tmp, predicate, relation_results)
                    if index_delimite == -1:
                        relation_results.extend(relation_results_tmp)
                        flag_exit_all = True
                        break
                    if len(relation_results_tmp) != 0:
                        relation_results.extend(relation_results_tmp)
                        i = index_delimite
                        flag_skip = True
                        break

            if flag_exit_all is True:
                break
            if flag_skip is False:
                i += 1
            ###################### Second senario: the person is potentially the child #######################

        else:
            i += 1

    # DEBUG:
    # for item in relation_results:
    #     test = item
    #     print(test)

    return relation_results


class Has_parent_rule():
    def __init__(self):

        ################## Auxiliary regex ##################
        # Match all possible comma pairs to get rid of all content within them,
        # since PERSON1..., ..., PERSON2, the content between comma pair is almost unlikely to form the relation for PERSON1 and PERSON2
        self.double_comma = re.compile(r',.*?,', re.IGNORECASE)

        # Match all content(already PERSON entity) between bracket, since it is often unlikty to form the HasParent relation within the bracket
        self.within_left_bracket = re.compile(r'[(][^)(]*?$', re.IGNORECASE)
        self.within_right_bracket = re.compile(r'^[^)(]*?[)]', re.IGNORECASE)

        # Match all second parent after "and" within 5 distance after getting rid of all content between comma pair
        # But this distance checking will be done within caller, not here, since it need to split the "filler_term" to count
        # the token to check
        # Also note that the matching part has already no comma pair, be processed already in caller
        self.contain_AND = re.compile(r'\band\b', re.IGNORECASE)
        self.window_between_AND_and_second_PARENT = 10  # This is distance used by the caller(default: 8)
        ################## Auxiliary regex ##################


        # self.window
        self.window_between_evidentWords_and_first_PARENT = 5
        self.rule_evident_words_regex = re.compile(r'(\bparent[s]?\b(?![\s][\'][s])|\bfather\b(?![\s][\'][s])|\bmother\b(?![\s][\'][s])|(\bson\b|\bchild\b|\bchildren\b|\bdaughter[s]?\b).*?(\bof\b|\bby\b))', re.IGNORECASE)
        # self.rule_evident_words_regex = re.compile(r'(\b[s]?tnerap\b|\brehtaf\b|\brehtom\b|(\bfo\b|\byb\b).*?(\bnos\b|\bdlihc\b|\bnerdlihc\b|\b[s]?rethguad\b))', re.IGNORECASE)


        self.window_between_TO_and_first_PARENT = 7 # This is distance used by the caller
        self.rule_TO_regex = re.compile(r'\bto\b', re.IGNORECASE)     # define the window_size=7

        self.rule_verb_regex = re.compile(r'\badopted\b|\braised\b', re.IGNORECASE)

        self.window_between_BORN_and_first_PARENT = 4 # This is distance used by the caller
        self.rule_BORN_regex = re.compile(r'\bborn\b[\s]*', re.IGNORECASE) # define the window_size=4
        # self.rule_BORN_regex = re.compile(r'\bborn\b[\s]+(\w+\s){,4}$', re.IGNORECASE) # define the window_size=4


        self.rule_grandRelation_regex = re.compile(r'\bgrandson\b|\bgrandparent\b|\bgrandfather\b|\bgrandmother\b|\bgrandparents\b', re.IGNORECASE)

        # self.pos_rule_dict = {
        #     "person1_evidentWords_person2_possiblePerson3": self._rule_pos_person_evidentWords_person_possibleSecondPerson,
        #     "person1_TO_person2_possiblePerson3": self._rule_pos_person_TO_person_possibleSecondPerson,
        #     "person1_verb_person2_possiblePerson3": self._rule_pos_person_verb_person_possibleSecondPerson,
        #     "person1_BORN_person2_possiblePerson3": self._rule_pos_person_BORN_person_possibleSecondPerson,
        # }
        self.pos_rule_dict = [
            self._rule_pos_person_evidentWords_person_possibleSecondPerson,
            self._rule_pos_person_TO_person_possibleSecondPerson,
            self._rule_pos_person_verb_person_possibleSecondPerson,
            # self._rule_pos_person_BORN_person_possibleSecondPerson, # Confused for this rule4 ???
        ]


    ######################################################################
    # Below are four summarized rules
    ######################################################################

    ############################### Rule 1 ###############################
    def _rule_pos_person_evidentWords_person_possibleSecondPerson(self, relation_dict, outer_index, inner_index, rel_dict_collection_dict):
        # The subject class is already PERSON1(child),
        # And the object class is already PERSON2(parent), and this PERSON2 is not within bracket now,
        # then check it further:

        filler_term = relation_dict['filler_term']

        # Get rid of all content between all commma pairs if it has, since it is impossible to form the relation in this case
        # new_filler_term = self.double_comma.subn('', filler_term)[0]
        # new_filler_term = filler_term[::-1]
        new_filler_term = filler_term

        # If doesn't have evident words between PERSON1 and PERSON2, then it doesn't follow this rule,
        # need to return and check other rules next.
        # if not self.rule_evident_words_regex.search( new_filler_term ):
        #     return ( None, None, False, None ) # Actually only first parameter "object_list_for_subject=None" is OK
        matchObj = self.rule_evident_words_regex.search( new_filler_term )
        if matchObj is None:
            return ( None, None, False, None )

        if len(new_filler_term[matchObj.span()[1]+1:].split()) > self.window_between_evidentWords_and_first_PARENT:
        # if len(new_filler_term[len(filler_term)-1-matchObj.span()[1]:].split()) > self.window_between_evidentWords_and_first_PARENT:
            return ( None, None, False, None )


        # Already reach the last possible relation
        length = len(rel_dict_collection_dict)
        if (outer_index + inner_index+1 ) >= (length - 1):
            return ( [relation_dict['object_text']], length, False, None )


        # The later part to find possible relations are same for all four summarized rules
        (object_list_for_subject, index_delimite, flag_grandRelation, object_list_for_newSubject) = \
            self.__rule_find_possible_parent_relations_in_one_round( relation_dict, outer_index, inner_index, rel_dict_collection_dict )

        return ( object_list_for_subject, index_delimite, flag_grandRelation, object_list_for_newSubject )



    ############################### Rule 2 ###############################
    def _rule_pos_person_TO_person_possibleSecondPerson(self, relation_dict, outer_index, inner_index, rel_dict_collection_dict ):
        # The subject class is already PERSON1(child),
        # And the object class is already PERSON2(parent), and this PERSON2 is not within bracket now,
        # then check it further:

        filler_term = relation_dict['filler_term']
        # Get rid of all content between all commma pairs if it has, since it is impossible to form the relation in this case
        new_filler_term = self.double_comma.subn('', filler_term)[0]
        # If doesn't have evident words between PERSON1 and PERSON2, then it doesn't follow this rule,
        # need to return and check other rules next.
        match_obj = self.rule_TO_regex.search(new_filler_term)
        if match_obj is None:
            return (None, None, False, None)  # Actually only first parameter "object_list_for_subject=None" is OK
        if len(new_filler_term[match_obj.span()[1]+1:].split()) > self.window_between_TO_and_first_PARENT:
            return (None, None, False, None)  # Actually only first parameter "object_list_for_subject=None" is OK
        # if not self.rule_TO_regex.search(new_filler_term):
        #     return (None, None, False, None)  # Actually only first parameter "object_list_for_subject=None" is OK

        # Already reach the last possible relation
        length = len(rel_dict_collection_dict)
        if ( outer_index + inner_index+1 ) >= (length - 1):
            return ([relation_dict['object_text']], length, False, None)


        # The later part to find possible relations are same for all four summarized rules
        (object_list_for_subject, index_delimite, flag_grandRelation, object_list_for_newSubject) = \
            self.__rule_find_possible_parent_relations_in_one_round(relation_dict, outer_index, inner_index, rel_dict_collection_dict )

        return (object_list_for_subject, index_delimite, flag_grandRelation, object_list_for_newSubject)



    ############################### Rule 3 ###############################
    def _rule_pos_person_verb_person_possibleSecondPerson(self, relation_dict, outer_index, inner_index, rel_dict_collection_dict ):
        # The subject class is already PERSON1(child),
        # And the object class is already PERSON2(parent), and this PERSON2 is not within bracket now,
        # then check it further:

        filler_term = relation_dict['filler_term']
        # Get rid of all content between all commma pairs if it has, since it is impossible to form the relation in this case
        new_filler_term = self.double_comma.subn('', filler_term)[0]
        # If doesn't have evident words between PERSON1 and PERSON2, then it doesn't follow this rule,
        # need to return and check other rules next.
        if not self.rule_verb_regex.search(new_filler_term):
            return (None, None, False, None)  # Actually only first parameter "object_list_for_subject=None" is OK

        # Already reach the last possible relation
        length = len(rel_dict_collection_dict)
        if (outer_index + inner_index+1) >= (length - 1):
            return ([relation_dict['object_text']], length, False, None)


        # The later part to find possible relations are same for all four summarized rules
        (object_list_for_subject, index_delimite, flag_grandRelation, object_list_for_newSubject) = \
            self.__rule_find_possible_parent_relations_in_one_round(relation_dict, outer_index, inner_index, rel_dict_collection_dict )

        return (object_list_for_subject, index_delimite, flag_grandRelation, object_list_for_newSubject)



    ############################### Rule 4 ###############################
    def _rule_pos_person_BORN_person_possibleSecondPerson(self, relation_dict, outer_index, inner_index, rel_dict_collection_dict ):
        # The subject class is already PERSON1(child),
        # And the object class is already PERSON2(parent), and this PERSON2 is not within bracket now,
        # then check it further:

        filler_term = relation_dict['filler_term']
        # Get rid of all content between all commma pairs if it has, since it is impossible to form the relation in this case
        new_filler_term = self.double_comma.subn('', filler_term)[0]
        # If doesn't have evident words between PERSON1 and PERSON2, then it doesn't follow this rule,
        # need to return and check other rules next.
        matchObj = self.rule_BORN_regex.search(new_filler_term)
        if matchObj is None:
            return (None, None, False, None)  # Actually only first parameter "object_list_for_subject=None" is OK
        if len(new_filler_term[matchObj.span()[1]+1:].split()) > self.window_between_BORN_and_first_PARENT:
            return (None, None, False, None)  # Actually only first parameter "object_list_for_subject=None" is OK

        # Already reach the last possible relation
        length = len(rel_dict_collection_dict)
        if (outer_index + inner_index+1) >= (length - 1):
            return ([relation_dict['object_text']], length, False, None)


        # The later part to find possible relations are same for all four summarized rules
        (object_list_for_subject, index_delimite, flag_grandRelation, object_list_for_newSubject) = \
            self.__rule_find_possible_parent_relations_in_one_round(relation_dict, outer_index, inner_index, rel_dict_collection_dict )

        return (object_list_for_subject, index_delimite, flag_grandRelation, object_list_for_newSubject)






    ############################### Rule 5 ###############################
    # this internal rule would only be called by method "_rule_find_grandRelation" to
    # extract the real grandRelation
    def __extract_real_grandRelation(self, person, relation_results, predicate):
        tmp_relation_results = []

        priority = -1
        subject = None
        person_fullname = person.split()
        for i in range( len(person_fullname)-1, -1, -1 ):
            flag_get_it = False
            for rel_obj in relation_results:
                full_name = rel_obj.object.split() # It is only possible to match the object(the subject's parent)
                for j in range( len(full_name)-1, -1, -1 ):
                    if full_name[j] == person_fullname[i]:
                        if i > priority:
                            priority = i
                            subject = rel_obj.object
                            flag_get_it = True
                            break
                if flag_get_it is True: break
            if flag_get_it is True: break

        if subject is not None:
            relation = Relation(subject, predicate, person)
            tmp_relation_results.append( relation )

        return tmp_relation_results
    def _rule_find_grandRelation(self, relation_dict_list, outer_index, rel_dict_collection_dict, relation_results, predicate):
        # Now already get the first grandparent(exclude the one within bracket),
        # and "relation_dict_list" is the list corresponding to this grandparent, i.e. all
        # element's subject_term is this grandparent PERSON within this list. So we need to
        # extract second grandparent if it is and return the next index where following the segment
        # of the sentence need to be processed as usual.

        # the list to store all grandparents objects
        object_list_for_subject = []
        object_list_for_subject.extend( self.__extract_real_grandRelation( relation_dict_list[0]['subject_text'],
                                                                           relation_results, predicate ) )
        # Already reach the last possible relation
        length = len(rel_dict_collection_dict)
        if outer_index >= (length - 1):
            return ( object_list_for_subject, outer_index+1 )

        for j in range(len(relation_dict_list)):
            if relation_dict_list[j]['object_class'] == 'PERSON':
                if self.within_left_bracket.search(relation_dict_list[j]['filler_term']) and \
                        self.within_right_bracket.search(relation_dict_list[j]['object_right_term']):
                    continue
                # If this PERSON is within bracket, then it is very likely not the target relation
                # Now the first grandparent is already confirmed, and there is the second PERSON,
                # which is the potential candidate for second grandparent
                relation_results_tmp = []
                relation_dict = relation_dict_list[j]
                filler_term = relation_dict['filler_term']

                # Get rid of all content between all commma pairs if it has, since it is impossible to form the relation in this case
                # new_filler_term = self.double_comma.subn('', filler_term)[0]
                new_filler_term = filler_term

                matchObj = self.contain_AND.search(new_filler_term)
                matchObj_sibling = re.search(r'sibling[s]|brother[s]|sister[s]', new_filler_term)
                # If the "filler_term" between first PERSON1 and candidate PERSON2 has no word 'and', then it is often the candidate is not the answer
                if matchObj is None or matchObj_sibling is not None: continue
                charIndexAfterAND = matchObj.span()[1] + 1
                # If the word count between 'and' and second candidate PERSON is larger than configured window size,
                # then the candidate is often not the second parent
                if len(new_filler_term[charIndexAfterAND:].split()) >= self.window_between_AND_and_second_PARENT: continue

                # Now the second PERSON candidate is PERSON entity, outside the bracket, has word 'and' before and
                # the distance from 'and' is less than configured window size 5, and no grandRelation until now,
                # then it means it is regarded as the second parent for the subject
                # Indicate that we extract two parent relations already and return
                object_list_for_subject.extend(self.__extract_real_grandRelation(relation_dict['subject_text'],
                                                                                 relation_results, predicate))

                # this delimited index is the next item(entity) need to be processed,
                # this is a bit different from the that of DateOfBirth
                index_delimite = outer_index + j+1 + 1
                return ( object_list_for_subject, index_delimite )

        # Actually, if program hit here, then it means no other relations need to be extracted for this sentence
        # So set the 'index_delimite=None' as the flag.
        return ( object_list_for_subject, -1 )





    ####### This rule is as a sub-rule used by all four summarized rules #######
    # To find all possible parent( one parent or two parents) relations for single round
    def __rule_find_possible_parent_relations_in_one_round(self, relation_dict, outer_index, inner_index,
                                                           rel_dict_collection_dict):
        object_list_for_subject = [relation_dict['object_text']]  # the list to store all objects(parents in this case)
        index_delimite = None
        object_right_side_rel_dict_collection = rel_dict_collection_dict[inner_index + outer_index + 1]

        # The object class is PERSON entity
        # This branch often indicated need to check the second parent if it has
        for i in range(len(object_right_side_rel_dict_collection)):
            if not object_right_side_rel_dict_collection[i]['object_class'] == 'PERSON': continue

            # The object class is already PERSON now, still need to check further,
            # It is only possible to be the second parent
            relation_dict = object_right_side_rel_dict_collection[i]

            if self.within_left_bracket.search(relation_dict['filler_term']) and \
                    self.within_right_bracket.search(relation_dict['object_right_term']):
                continue  # If this PERSON is within bracket, then it is very likely not the second parent

            # Note: if "filler_term" contain the words such as "grandfather"/"grandmother"/"grandson"/"grandparents",
            # then it is very likely this object is the parent relation for the already recogined parent for the children
            # In this case, just /*RETURN*/ and extract this kind of relation in other functions by checking
            # the surname of recognised parents in list "object_list_for_subject"(the list store all recoginised parent relations)
            # If no such matching or missing the matching, then just skip this grandRelation, and keep on.
            # Also the third parameter is only set to True in this case.
            # Note: this grandRelation method would only be callable in the case of only one parent appears before
            if self.rule_grandRelation_regex.search(relation_dict['filler_term']):
                index_delimite = inner_index + outer_index + 1 + i + 1
                object_list_for_newSubject = []
                (object_list_for_newSubject, index_delimite) = self.__rule_find_grandRelation_after_singleParent(
                    index_delimite, relation_dict, rel_dict_collection_dict, object_list_for_newSubject)

                return (object_list_for_subject, index_delimite, True, object_list_for_newSubject)

            # Now it is PERSON and also outside the bracet, it is a candidate now, need to check further:
            filler_term = relation_dict['filler_term']

            # Get rid of all content between all commma pairs if it has, since it is impossible to form the relation in this case
            # new_filler_term = self.double_comma.subn('', filler_term)[0]
            new_filler_term = filler_term

            matchObj = self.contain_AND.search(new_filler_term)
            matchObj_sibling = re.search(r'sibling[s]|brother[s]|sister[s]', new_filler_term)
            # If the "filler_term" between first PERSON1 and candidate PERSON2 has no word 'and', then it is often the candidate is not the answer
            if matchObj is None or matchObj_sibling is not None: continue
            charIndexAfterAND = matchObj.span()[1] + 1
            # If the word count between 'and' and second candidate PERSON is larger than configured window size,
            # then the candidate is often not the second parent
            if len(new_filler_term[charIndexAfterAND:].split()) >= self.window_between_AND_and_second_PARENT: continue

            # Now the second PERSON candidate is PERSON entity, outside the bracket, has word 'and' before and
            # the distance from 'and' is less than configured window size 5, and no grandRelation until now,
            # then it means it is regarded as the second parent for the subject
            # Indicate that we extract two parent relations already and return
            object_list_for_subject.append(relation_dict['object_text'])

            # this delimited index is the next item(entity) need to be processed,
            # this is a bit different from the that of DateOfBirth
            index_delimite = inner_index + outer_index + 1 + i + 1 + 1
            return (object_list_for_subject, index_delimite, False, None)

        # Actually, if program hit here, then it means no other relations need to be extracted for this sentence
        # So set the 'index_delimite=None' as the flag.
        return (object_list_for_subject, -1, False, None)


    ####### This rule is a sub-rule called by "__rule_find_possible_parent_relations_in_one_round" #######
    # Special rule to extract grandrelation
    # Note: this grandRelation method would only be callable in the case of only one parent appears before,
    # although there is no instance in training data yet, and for more common case, which is it appears after
    # parents, would be handled by method "__rule_find_grandRelation"
    def __rule_find_grandRelation_after_singleParent(self, outer_index, relation_dict, rel_dict_collection_dict, object_list_for_newSubject):
        # Just make sure its left-side has such words such as "grandson..."
        if not self.rule_grandRelation_regex.search(relation_dict['subject_left_term']):
            return ( object_list_for_newSubject, outer_index )

        new_relation_dict = rel_dict_collection_dict[outer_index]
        object_list_for_newSubject = [new_relation_dict['subject_text']]  # the list to store all objects(grandparents in this case)

        # The object class is PERSON entity
        # This branch often indicated need to check the second parent if it has
        for i in range(len(new_relation_dict)):
            if not new_relation_dict[i]['object_class'] == 'PERSON': continue

            # The object class is already PERSON now, still need to check further,
            # It is only possible to be the second parent
            relation_dict = new_relation_dict[i]

            if self.within_left_bracket.search(relation_dict['filler_term']) and \
                    self.within_right_bracket.search(relation_dict['object_right_term']):
                continue  # If this PERSON is within bracket, then it is very likely not the second parent

            # Now it is PERSON and also outside the bracet, it is a candidate now, need to check further:
            filler_term = relation_dict['filler_term']
            # Get rid of all content between all commma pairs if it has, since it is impossible to form the relation in this case
            new_filler_term = self.double_comma.subn('', filler_term)[0]
            matchObj = self.contain_AND.search(new_filler_term)
            # If the "filler_term" between first PERSON1 and candidate PERSON2 has no word 'and', then it is often the candidate is not the answer
            if matchObj is None: continue
            charIndexAfterAND = matchObj.span()[1] + 1
            # If the word count between 'and' and second candidate PERSON is larger than configured window size,
            # then the candidate is often not the second parent
            if len(new_filler_term[charIndexAfterAND:].split()) >= self.window_between_AND_and_second_PARENT: continue

            # Now the second PERSON candidate is PERSON entity, outside the bracket, has word 'and' before and
            # the distance from 'and' is less than configured window size 5, and no grandRelation until now,
            # then it means it is regarded as the second parent for the subject.
            # Indicate that we extract two parent relations already and return
            object_list_for_newSubject.append(relation_dict['object_text'])

            # this delimited index is the next item(entity) need to be processed,
            # this is a bit different from the that of DateOfBirth
            index_delimite = outer_index + i+1 + 1
            return (object_list_for_newSubject, index_delimite)

        # Actually, if program hit here, then it means no other relations need to be extracted for this sentence
        # So set the 'index_delimite=None' as the flag.
        return (object_list_for_newSubject, -1)

################################################## HP extractor above #################################################










####################################################################################################################
############################################# Dependency parse method ##############################################
####################################################################################################################
# # def replace_tokenizer(nlp, my_split_function):
# #     old_tokenizer = nlp.tokenizer
# #     nlp.tokenizer = lambda string: old_tokenizer.tokens_from_list(my_split_function(string))
#
# ###############################################################################
# # Transform the original annotations, grouping the sub-NE into one, and keep
# # the non-NE as it is, to finally make a new real annnotation list for
# # further processing
# ###############################################################################
# def transform_annotations_for_dependency_parse(annotations):
#     NE_annotations = []
#     NE_tag = None
#     for i in range(len(annotations)):
#         if annotations[i][4].startswith("B-"):
#             NE_tag = annotations[i][4][2:]
#             start = i
#         elif annotations[i][4] == 'O':
#             if NE_tag is not None:
#                 # annotation_tuple = (start, i - 1, NE_tag, '^'.join([x[1] for x in annotations[start: i]]),
#                 #                     [x[3] for x in annotations[start: i]])
#                 annotation_tuple = (start, i - 1, NE_tag, ''.join([x[1] for x in annotations[start: i]]), annotations[i-1][3])
#                 NE_annotations.append(annotation_tuple)
#
#             NE_annotations.append((i, i, "O", annotations[i][1], annotations[i][3]))
#             NE_tag = None
#     if NE_tag is not None:
#         # annotation_tuple = (start, len(annotations) - 1, NE_tag, '^'.join([x[1] for x in annotations[start: len(annotations)]]),
#         #                     [x[3] for x in annotations[start: len(annotations)]])
#         annotation_tuple = (start, len(annotations) - 1, NE_tag, ''.join([x[1] for x in annotations[start: len(annotations)]]), annotations[len(annotations)-1][3])
#         NE_annotations.append(annotation_tuple)
#
#
#     # # Manually generate name entity and IOB
#     entity_type = []
#     entity_IOB = []
#
#     # Seems like the dependency parse has nothing to do with the name entity, although currently just leave it here
#     NE_LIB_DICT = defaultdict(int)
#     NE_LIB_DICT["PERSON"] = 346
#     NE_LIB_DICT["NORP"] = 347
#     NE_LIB_DICT["FACILITY"] = 348
#     NE_LIB_DICT["ORG"] = 349
#     NE_LIB_DICT["GPE"] = 350
#     NE_LIB_DICT["LOC"] = 351
#     NE_LIB_DICT["PRODUCT"] = 352
#     NE_LIB_DICT["EVENT"] = 353
#     NE_LIB_DICT["WORK_OF_ART"] = 354
#     NE_LIB_DICT["LANGUAGE"] = 355
#     NE_LIB_DICT["DATE"] = 356
#     NE_LIB_DICT["TIME"] = 357
#     NE_LIB_DICT["PERCENT"] = 358
#     NE_LIB_DICT["MONEY"] = 359
#     NE_LIB_DICT["QUANTITY"] = 360
#     NE_LIB_DICT["ORDINAL"] = 361
#     NE_LIB_DICT["CARDINAL"] = 362
#
#     # IOB values are 0=missing, 1=I, 2=O, 3=B
#     for i in range(len(NE_annotations)):
#         if NE_annotations[i][2] != "O":
#             entity_type.append( NE_LIB_DICT[NE_annotations[i][2]] )
#             entity_IOB.append(3)
#         else:
#             entity_type.append(0)
#             entity_IOB.append(2)
#
#
#     text = ""
#     NE_actual = []
#     for item in NE_annotations:
#         sub_text = item[3] + " "
#         text += sub_text
#         NE_actual.append(item[2])
#
#     # Must do this way, if use spacy default api at single pass, then it will tokenize every dot anyway
#     sent = spacynlp.tokenizer.tokens_from_list( text.split() )
#     spacynlp.tagger(sent)
#     spacynlp.parser(sent)
#     # sent = spacynlp(sent.text, entity=False)
#
#
#     columns = [78, 77]  # ENT_TYPE: 78; ENT_IOB: 77
#     values = ndarray(shape=(len(sent), len(columns)), dtype='int32')
#     values[:, 0] = entity_IOB
#     # IOB values are 0=missing, 1=I, 2=O, 3=B
#     values[:, 1] = entity_type
#     sent.from_array(columns, values)
#
#     sentence_dependency = []
#     print("-------------------------------------------------------")
#     for i in range(len(sent)):
#         token_dependency = []
#
#         token_dependency.append( sent[i].dep_ )                      # dependency
#         token_dependency.append( sent[i].orth_ )                     # token
#         token_dependency.append( sent[i].head )                      # its head token
#         token_dependency.append( NE_actual[i] )                      # name entity
#         token_dependency.append( sent[i].pos_ )                      # POS tag
#         token_dependency.append( (t for t in sent[i].lefts) )        # its lefts as a tuple
#         token_dependency.append( (t for t in sent[i].rights) )       # its rights as a tuple
#
#         sentence_dependency.append(token_dependency)
#         # DEBUG
#         print("dep: "+sent[i].dep_+"  "+
#               "token: " + " ".join(sent[i].orth_.split("^")) + "  " +
#               "head: " + " ".join(sent[i].head.orth_.split("^"))+"  " +
#               "NE: " + NE_actual[i] + "  " +
#               "POS: " + sent[i].pos_ + "  " +
#               "lefts: " + ",".join([" ".join(t.orth_.split("^")) for t in sent[i].lefts]) + "  " +
#               "rights: " + ",".join([" ".join(t.orth_.split("^")) for t in sent[i].rights]) )
#
#     return sentence_dependency
#
#
#
#
# # def has_parent_extractor_denpendency_parse(sentence, predicate='HasParent'):
# #     annotations = sentence['annotation']
# #     sentence_dependency = transform_annotations_for_dependency_parse(annotations)
# #
# #     relation_results = []
# #     PARENTS = re.compile(r'parents', re.IGNORECASE)
# #     head_vbn_obj = None
# #     PERSON1 = None
# #     for i in range(len(sentence_dependency)):
# #         if sentence_dependency[i][3]=="PERSON":
# #             its_head_obj = sentence_dependency[i][2]
# #             if its_head_obj.pos_ == "VERB": # POS
# #                 head_vbn_obj = its_head_obj
# #                 PERSON1 = sentence_dependency[i][1]
# #                 break
# #     TO_obj = None
# #     if head_vbn_obj is not None:
# #         head_right_objs = head_vbn_obj.rights
# #         for obj in head_right_objs:
# #             if obj.orth_ == "to" and obj.dep_ == "prep":
# #                 TO_obj = obj
# #                 break
# #     candidate_parents = None
# #     flag_has_PARENTS = False
# #
# #     tmp_relation_results = []
# #     if TO_obj is not None:
# #         TO_right_objs = TO_obj.rights
# #         FIRST_PARENT = None
# #         for obj in TO_right_objs:
# #             if PARENTS.match(obj.orth_):
# #                 candidate_parents = obj.rights
# #                 flag_has_PARENTS = True
# #                 break
# #             if sentence_dependency[obj.i][3] == "PERSON":
# #                 relation = Relation(PERSON1, predicate, obj.orth_)
# #                 tmp_relation_results.append(relation)
# #                 FIRST_PARENT = obj
# #
# #
# #
# #     if flag_has_PARENTS is True:
# #         tmp_relation_results = []
# #         FIRST_PARENT = None
# #         if candidate_parents is not None:
# #             for obj in candidate_parents:
# #                 if sentence_dependency[obj.i][3] == "PERSON":
# #                     relation = Relation(PERSON1, predicate, obj.orth_)
# #                     tmp_relation_results.append(relation)
# #                     FIRST_PARENT = obj
# #                     break
# #         if FIRST_PARENT is not None:
# #             right_objs = FIRST_PARENT.rights
# #             flag_search_SECOND_PARENT = False
# #             for obj in right_objs:
# #                 if flag_search_SECOND_PARENT is True:
# #                     if sentence_dependency[obj.i][3] == "PERSON":
# #                         relation = Relation(PERSON1, predicate, obj.orth_)
# #                         tmp_relation_results.append(relation)
# #                         break
# #                 elif obj.orth_ == "and" or obj.orth_ == "AND":
# #                     flag_search_SECOND_PARENT = True
# #                     continue
# #
# #     else:
# #
# #     relation_results.extend( tmp_relation_results )
# #     print(relation_results)






















