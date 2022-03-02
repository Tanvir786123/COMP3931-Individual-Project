import csv
from collections import deque
from re import S
from icd9cms.icd9 import search


class CSVReader(object):
    __file = None
    __reader = None

    def __init__(self, path) -> None:
        self.__file = open(path)
        self.__reader = csv.reader(self.__file)

    def __del__(self):
        self.__file.close()

    def generate_classifications(self, object, stack):
        if object.parent == None:
            stack.append(object)
            return
        stack.append(object)
        self.generate_classifications(object.parent, stack)
        return stack

    def create_first_level_classifier(self):
        ICD9_CODE = 3
        next(self.__reader)
        first_lvl_seen_codes = {}
        second_lvl_codes = {}
        code_stack = deque()
        counter = 0
        for row in self.__reader:
            if row[ICD9_CODE]:
                if row[ICD9_CODE] not in first_lvl_seen_codes and row[ICD9_CODE] != '71970':
                    code_stack = self.generate_classifications(search(row[ICD9_CODE]), code_stack)
                    # only fails for code 719.70
                    sentence = code_stack.pop()
                    if sentence not in second_lvl_codes:
                        second_lvl_codes[sentence] = counter
                        counter += 1
                    code_stack.clear()
                    first_lvl_seen_codes[row[ICD9_CODE]] = 'seen'
        self.__file.seek(0)
        return second_lvl_codes

    def create_second_level_classifier(self):
        ICD9_CODE = 3
        next(self.__reader)
        stack = deque()
        counter = 0
        second_lvl_seen_codes = {}
        second_lvl_codes = {}
        for row in self.__reader:
            if row[ICD9_CODE]:
                if row[ICD9_CODE] not in second_lvl_seen_codes and row[ICD9_CODE] != '71970':
                    second_lvl_seen_codes[row[ICD9_CODE]] = 'seen'
                    stack = self.generate_classifications(search(row[ICD9_CODE]), stack)
                    first_lvl_sentence = stack.pop()
                    second_lvl_sentence = stack.pop()
                    if second_lvl_sentence not in second_lvl_codes:
                        second_lvl_codes[second_lvl_sentence] = counter
                        counter += 1
                    stack.clear()
        self.__file.seek(0)
        return second_lvl_codes

    def generate_diagnosis_icd(self, icd9_dict):
        HEADERS = ['subject_id', 'hadm_id', 'seq_num', 'icd9_code', 'high_level_code']
        ICD9_CODE = 3
        list = [HEADERS]
        next(self.__reader)
        stack = deque()
        for row in self.__reader:
            if row[ICD9_CODE] and row[ICD9_CODE] != '71970':
                stack = self.generate_classifications(search(row[ICD9_CODE]), stack)
                value = icd9_dict[stack.pop()]
                list.append(
                    [row[0], row[1], row[2], row[3], value]
                )
        return list

    def convert_icd9_dict_to_list(self, first_lvl_classes, second_level_classes):
        HEADERS = ['primary_key', 'high_level_classification', 'second_level_f_key']
        list = [HEADERS]
        sentence = None
        stack = deque()
        for key, value in first_lvl_classes.items():
            sentence = str(key)
            sentence = sentence.replace(',', '-')
            list.append([value, sentence, 'something'])
        return list

    def save_to_path(self, path, list):
        file = open(path, 'w')
        counter = 0
        for row in list:
            for item in row:
                if counter == len(row) - 1:
                    file.write(str(item))
                else:
                    file.write(str(item) + ',')
                    counter += 1
            file.write('\n')
            counter = 0
        file.close()


if __name__ == '__main__':
    csv_obj = CSVReader('data/diagnosis_icd.csv')

    second_level_class = csv_obj.create_second_level_classifier()
    first_level_class = csv_obj.create_first_level_classifier()
    code_table = csv_obj.convert_icd9_dict_to_list(first_level_class, second_level_class)
    # csv_obj.save_to_path('celonis/icd9_codes.csv', code_table)

    # here is where i do magic to connect to 2nd level classifer whom connects to the high level classifier
    diagnosis_icd_table = csv_obj.generate_diagnosis_icd(first_level_class)
    # csv_obj.save_to_path('celonis/diagnosis_icd_table.csv', diagnosis_icd_table)

    print(len(code_table))
    print(len(diagnosis_icd_table))
    print(len(second_level_class))
