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

    def create_event_log(self):
        new_headers = ['subject_id', 'hadm_id',
                       'event', 'timestamp',
                       'admission_type', 'admission_location',
                       'discharge_location', 'insurance',
                       'language', 'religion',
                       'marital_status', 'ethnicity',
                       'diagnosis', 'hospital_expire_flag',
                       'has_chartevents_data'
                    ]
        new_list = [new_headers]
        next(self.__reader)
        ADMITTIME = 2
        DISCHTIME = 3
        DEATHTIME = 4
        EDREGTIME = 13
        EDOUTTIME = 14
        DIAGNOSIS = 15
        for row in self.__reader:
            row[DIAGNOSIS] = row[DIAGNOSIS].replace(',', '-')
            if row[ADMITTIME]:
                new_list.append([
                    row[0], row[1],
                    'Admit', row[ADMITTIME],
                    row[5], row[6],
                    row[7], row[8],
                    row[9], row[10],
                    row[11], row[12],
                    row[15], row[16],
                    row[17]
                ])
            if row[DISCHTIME]:
                new_list.append([
                    row[0], row[1],
                    'Discharge', row[DISCHTIME],
                    row[5], row[6],
                    row[7], row[8],
                    row[9], row[10],
                    row[11], row[12],
                    row[15], row[16],
                    row[17]
                ])
            if row[DEATHTIME]:
                new_list.append([
                    row[0], row[1],
                    'Death', row[DEATHTIME],
                    row[5], row[6],
                    row[7], row[8],
                    row[9], row[10],
                    row[11], row[12],
                    row[15], row[16],
                    row[17]
                ])
            if row[EDREGTIME]:
                new_list.append([
                    row[0], row[1],
                    'Edreg', row[EDREGTIME],
                    row[5], row[6],
                    row[7], row[8],
                    row[9], row[10],
                    row[11], row[12],
                    row[15], row[16],
                    row[17]
                ])
            if row[EDOUTTIME]:
                new_list.append([
                    row[0], row[1],
                    'Edout', row[EDOUTTIME],
                    row[5], row[6],
                    row[7], row[8],
                    row[9], row[10],
                    row[11], row[12],
                    row[15], row[16],
                    row[17]
                ])
        self.__file.seek(0)
        return new_list

    def create_high_level_classification(self, object, stack):
        if object.parent == None:
            stack.append(object)
            return
        stack.append(object)
        self.create_high_level_classification(object.parent, stack)
        return stack

    def create_dict_of_codes(self):
        ICD9_CODE = 3
        next(self.__reader)
        seen_codes = {}
        calculated_sentence = {}
        code_stack = deque()
        counter = 0
        for row in self.__reader:
            if row[ICD9_CODE]:
                if row[ICD9_CODE] not in seen_codes and row[ICD9_CODE] != '71970':
                    code_stack = self.create_high_level_classification(search(row[ICD9_CODE]), code_stack)
                    # only fails for code 719.70
                    sentence = code_stack.pop()
                    if sentence not in calculated_sentence:
                        calculated_sentence[sentence] = counter
                        counter += 1
                    code_stack.clear()
                    seen_codes[row[ICD9_CODE]] = 'seen'
        self.__file.seek(0)
        return calculated_sentence

    def generate_diagnosis_icd(self, icd9_dict):
        HEADERS = ['subject_id', 'hadm_id', 'seq_num', 'icd9_code', 'high_level_code']
        ICD9_CODE = 3
        list = [HEADERS]
        next(self.__reader)
        stack = deque()
        for row in self.__reader:
            if row[ICD9_CODE] and row[ICD9_CODE] != '71970':
                stack = self.create_high_level_classification(search(row[ICD9_CODE]), stack)
                value = icd9_dict[stack.pop()]
                list.append(
                    [row[0], row[1], row[2], row[3], value]
                )
        return list

    def convert_icd9_dict_to_list(self, dict):
        HEADERS = ['primary_key', 'high_level_classification']
        list = [HEADERS]
        sentence = None
        for key, value in dict.items():
            sentence = str(key)
            sentence = sentence.replace(',', '-')
            list.append([value, sentence])
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
    csv_obj = CSVReader('data/admissions.csv')
    event_log = csv_obj.create_event_log()
    # csv_obj.save_to_path('celonis/event_log.csv', event_log)
    print(len(event_log))

    csv_obj = CSVReader('data/diagnosis_icd.csv')

    code_dict = csv_obj.create_dict_of_codes()
    code_table = csv_obj.convert_icd9_dict_to_list(code_dict)
    # csv_obj.save_to_path('celonis/icd9_codes.csv', code_table)

    diagnosis_icd_table = csv_obj.generate_diagnosis_icd(code_dict)
    # csv_obj.save_to_path('celonis/diagnosis_icd_table.csv', diagnosis_icd_table)

    print(len(code_table))
    print(len(diagnosis_icd_table))
