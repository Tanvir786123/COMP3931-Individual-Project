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
                    first_lvl_sentence = code_stack.pop()
                    second_lvl_sentence = code_stack.pop()
                    if first_lvl_sentence not in second_lvl_codes:
                        second_lvl_codes[first_lvl_sentence] = counter
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
                        second_lvl_codes[second_lvl_sentence] = [counter, row[ICD9_CODE]]
                        counter += 1
                    stack.clear()
        self.__file.seek(0)
        return second_lvl_codes

    def generate_diagnosis_icd(self, second_lvl_codes):
        HEADERS = ['subject_id', 'hadm_id', 'seq_num', 'icd9_code', 'second_level_code']
        ICD9_CODE = 3
        list = [HEADERS]
        next(self.__reader)
        stack = deque()
        for row in self.__reader:
            if row[ICD9_CODE] and row[ICD9_CODE] != '71970':
                stack = self.generate_classifications(search(row[ICD9_CODE]), stack)
                first_lvl_sentence = stack.pop()
                second_lvl_sentence = stack.pop()
                second_lvl_code = second_lvl_codes[second_lvl_sentence][0]
                list.append(
                    [row[0], row[1], row[2], row[3], second_lvl_code]
                )
                stack.clear()
        return list

    def connect_second_lvl_to_first(self, first_lvl_codes, second_lvl_codes):
        stack = deque()
        for k, v in second_lvl_codes.items():
            second_lvl_pk = v[0]
            icd9_code = v[1]
            stack = self.generate_classifications(search(icd9_code), stack)
            first_lvl_sentence = stack.pop()
            if first_lvl_sentence not in first_lvl_codes:
                print('fuck')
            else:
                first_lvl_pk = first_lvl_codes[first_lvl_sentence]
                second_lvl_codes[k] = [second_lvl_pk, first_lvl_pk]

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

    def save_dict_to_file(self, path, dict, headers):
        file = open(path, 'w')
        count = 0
        for header in headers:
            if count == len(headers) - 1:
                file.write(str(header) + '\n')
            else:
                file.write(str(header) + ',')
            count += 1
        for k, v in dict.items():
            if type(v) == list:
                file.write(str(v[0]) + ',' + str(k) + ',' + str(v[1]) + '\n')
            else:
                file.write(str(v) + ',' + str(k) + '\n')
        file.close()

if __name__ == '__main__':
    csv_obj = CSVReader('data/diagnosis_icd.csv')

    second_level_class = csv_obj.create_second_level_classifier()
    first_level_class = csv_obj.create_first_level_classifier()
    csv_obj.connect_second_lvl_to_first(first_level_class, second_level_class)

    diagnosis_icd = csv_obj.generate_diagnosis_icd(second_level_class)
    csv_obj.save_to_path('celonis/diagnosis_icd.csv', diagnosis_icd)

    csv_obj.save_dict_to_file('celonis/first_level_icd9_codes.csv', first_level_class, ['primary_key', 'first_level_class'])
    csv_obj.save_dict_to_file('celonis/second_level_icd9_codes.csv', second_level_class, ['primary_key', 'second_level_class', 'fk_first_level_class'])
