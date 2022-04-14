import csv
from collections import deque
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
        if object.parent is None:
            stack.append(object)
            return
        stack.append(object)
        self.generate_classifications(object.parent, stack)
        return stack

    def create_first_level_classifier(self):
        ICD9_CODE = 3
        next(self.__reader)
        first_lvl_seen_codes = {}
        first_lvl_codes = {}
        stack = deque()
        counter = 0
        for row in self.__reader:
            if row[ICD9_CODE]:
                if row[ICD9_CODE] not in first_lvl_seen_codes\
                        and row[ICD9_CODE] != '71970':
                    stack = self.generate_classifications(
                        search(row[ICD9_CODE]), stack
                    )
                    # only fails for code 719.70
                    first_lvl_sentence = stack.pop()
                    stack.pop()
                    if first_lvl_sentence not in first_lvl_codes:
                        first_lvl_codes[first_lvl_sentence] = counter
                        counter += 1
                    stack.clear()
                    first_lvl_seen_codes[row[ICD9_CODE]] = 'seen'
        self.__file.seek(0)
        return first_lvl_codes

    def create_second_level_classifier(self):
        ICD9_CODE = 3
        next(self.__reader)
        stack = deque()
        counter = 0
        second_lvl_seen_codes = {}
        second_lvl_codes = {}
        for row in self.__reader:
            if row[ICD9_CODE]:
                if row[ICD9_CODE] not in second_lvl_seen_codes\
                        and row[ICD9_CODE] != '71970':
                    second_lvl_seen_codes[row[ICD9_CODE]] = 'seen'
                    stack = self.generate_classifications(
                        search(row[ICD9_CODE]), stack
                    )
                    stack.pop()
                    second_lvl_sentence = stack.pop()
                    if second_lvl_sentence not in second_lvl_codes:
                        second_lvl_codes[second_lvl_sentence] = [counter,
                                                                 row[ICD9_CODE]
                                                                 ]
                        counter += 1
                    stack.clear()
        self.__file.seek(0)
        return second_lvl_codes

    def create_third_level_classifier(self):
        ICD9_CODE = 3
        next(self.__reader)
        stack = deque()
        counter = 0
        third_lvl_seen_codes = {}
        third_lvl_codes = {}
        for row in self.__reader:
            if row[ICD9_CODE]:
                if row[ICD9_CODE] not in third_lvl_seen_codes\
                        and row[ICD9_CODE] != '71970':
                    third_lvl_seen_codes[row[ICD9_CODE]] = 'seen'
                    stack = self.generate_classifications(
                        search(row[ICD9_CODE]), stack
                    )
                    stack.pop()
                    stack.pop()
                    third_lvl_sentence = stack.pop()
                    if third_lvl_sentence not in third_lvl_codes:
                        third_lvl_codes[third_lvl_sentence] = [counter,
                                                               row[ICD9_CODE]]
                        counter += 1
                    stack.clear()
        self.__file.seek(0)
        return third_lvl_codes

    def generate_diagnosis_icd(self, third_lvl_codes):
        HEADERS = ['subject_id', 'hadm_id', 'seq_num', 'icd9_code',
                   'third_level_code']
        ICD9_CODE = 3
        list = [HEADERS]
        next(self.__reader)
        stack = deque()
        for row in self.__reader:
            if row[ICD9_CODE] and row[ICD9_CODE] != '71970':
                stack = self.generate_classifications(
                    search(row[ICD9_CODE]), stack
                )
                stack.pop()
                stack.pop()
                third_lvl_sentence = stack.pop()
                third_lvl_code = third_lvl_codes[third_lvl_sentence][0]
                list.append(
                    [row[0], row[1], row[2], row[3], third_lvl_code]
                )
                stack.clear()
        return list

    def connect_third_lvl_to_second(self, second_lvl_codes, third_lvl_codes):
        stack = deque()
        for k, v in third_lvl_codes.items():
            third_lvl_pk = v[0]
            icd9_code = v[1]
            stack = self.generate_classifications(search(icd9_code), stack)
            stack.pop()
            second_lvl_sentence = stack.pop()
            if second_lvl_sentence not in second_lvl_codes:
                print('fuck')
            else:
                second_lvl_pk = second_lvl_codes[second_lvl_sentence][0]
                third_lvl_codes[k] = [third_lvl_pk, second_lvl_pk]
            stack.clear()

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
            stack.clear()

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
            x = str(k)
            k = x.replace(',', '-')
            if type(v) == list:
                file.write(str(v[0]) + ',' + str(k) + ',' + str(v[1]) + '\n')
            else:
                file.write(str(v) + ',' + str(k) + '\n')
        file.close()


if __name__ == '__main__':
    csv_obj = CSVReader('data/diagnosis_icd.csv')

    first_level_class = csv_obj.create_first_level_classifier()
    second_level_class = csv_obj.create_second_level_classifier()
    third_level_class = csv_obj.create_third_level_classifier()
    csv_obj.connect_second_lvl_to_first(first_level_class, second_level_class)
    csv_obj.connect_third_lvl_to_second(second_level_class, third_level_class)

    diagnosis_icd = csv_obj.generate_diagnosis_icd(third_level_class)
    csv_obj.save_to_path('celonis/diagnosis_icd.csv', diagnosis_icd)

    csv_obj.save_dict_to_file('celonis/first_level_icd9_codes.csv',
                              first_level_class,
                              ['primary_key', 'first_level_class'])
    csv_obj.save_dict_to_file('celonis/second_level_icd9_codes.csv',
                              second_level_class,
                              ['primary_key',
                               'second_level_class', 'fk_first_level_class'])
    csv_obj.save_dict_to_file('celonis/third_level_icd9_codes.csv',
                              third_level_class,
                              ['primary_key', 'third_level_class',
                               'fk_second_level_class'])
