import csv
from collections import deque
from icd9cms.icd9 import search
import numpy as np
from scipy.stats import ttest_ind, levene


class CSVReader(object):

    def __init__(self, path) -> None:
        self.__file = open(path)
        self.__reader = csv.reader(self.__file)

    def __del__(self):
        self.__file.close()

    '''
    A recursive method to generate the ICD9 hierarchy given a code and
    store the hierarchy into a stack.
    '''
    def generate_classifications(self, object, stack):
        if object.parent is None:
            stack.append(object)
            return
        stack.append(object)
        self.generate_classifications(object.parent, stack)
        return stack

    '''
    A method to create the first level of ICD9 codes.
    '''
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

    '''
    A method to create the second level of ICD9 codes.
    '''
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

    '''
    A method to create the third level of ICD9 codes.
    '''
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

    '''
    A method to create create the new diagnosis_icd table linked to
    the third level ICD9 table.
    '''
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

    '''
    A method to connect the third ICD9 level to the second ICD9 level.
    '''
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

    '''
    A method to connect the second ICD9 level to the first ICD9 level.
    '''
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

    '''
    A method to save a list of items in a CSV format.
    '''
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

    '''
    A method to save a dictionary of items in a CSV format.
    '''
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

    '''
    A method to return a vector of rows if the rows contain a specified
    attribute.
    '''
    def grab_rows_via_attribute(self, attribute):
        vector = list()
        for row in self.__reader:
            if attribute in row:
                vector.append(row)
        self.__file.seek(0)
        return np.asarray(vector)

    '''
    A method to return a vector of rows if the rows contain a specified
    attribute that can be represented as a float for a given index.
    '''
    def get_array_slice(self, a, index):
        vector = list()
        for row in a:
            try:
                vector.append(float(row[index]))
            except Exception:
                pass
        return np.asarray(vector)

    '''
    A method to combine two one-dimensional vectors into a two dimensional
    vector where each column consists of the original vector paramters
    that can differ in size with respect to each other.
    '''
    def combine(self, a, b, headers):
        a = a.tolist()
        b = b.tolist()
        vector = list(headers)
        size = max(len(a), len(b))
        index = 0
        item_a = None
        item_b = None
        while (len(vector) < size):
            try:
                item_a = str(a[index])
                item_b = str(b[index])
                vector.append([item_a, item_b])
            except Exception:
                try:
                    item_a = str(a[index])
                    vector.append([item_a])
                except Exception:
                    try:
                        item_b = str(b[index])
                        vector.append([item_b])
                    except Exception:
                        pass
            index += 1
        return vector

    '''
    A method to perform the Levene test and print the values if told to.
    '''
    def levene(self, a, b, describe=True):
        test, p_val = levene(a, b)
        if describe:
            # Print decision.
            if p_val < 0.05:
                print('Decision: Reject the null hypothesis')
            else:
                print('Decision: Fail to reject the null hypothesis')
        return test, p_val

    '''
    A method to perform the Welch t-test and print the values if told to.
    '''
    def welch_t(self, a, b, equal_var=False, describe=True):
        # Perform Welch's t-test
        test, p_val = ttest_ind(a, b, equal_var=equal_var)
        if describe:
            # Print decision.
            if p_val < 0.05:
                print('Decision: Reject the null hypothesis')
            else:
                print('Decision: Fail to reject the null hypothesis')
        return test, p_val

    '''
    A method to perform the Cohen d test and print the values if told to.
    '''
    def cohen_d(self, a, b, describe=True):
        a_n, b_n = len(a), len(b)
        # Calculate pooled standard deviation.
        pv_num = ((a_n-1)*a.var())+((b_n-1)*b.var())
        pv_den = a_n+b_n
        pooled_sd = np.sqrt(pv_num/pv_den)
        d = (a.mean()-b.mean())/pooled_sd
        if describe:
            if d < 0.20:
                print('Effect Size: Very Small')
            elif d < 0.50:
                print('Effect Size: Small')
            elif d < 0.80:
                print('Effect Size: Medium')
            else:
                print('Effect Size: Large')
        return d


if __name__ == '__main__':
    '''
    This block of code reads the statistics from an example diagnosis and
    prints out the results.
    '''
    csv_obj = CSVReader(
        'statistics/'
        + 'alcohol_dependence_syndrome/avg_wait_time_admit_to_discharge.csv'
    )

    private_patients = csv_obj.grab_rows_via_attribute('Private')
    medicare_patients = csv_obj.grab_rows_via_attribute('Medicare')

    private_patients_avg_wait_time = csv_obj.get_array_slice(
        private_patients, 3
    )
    medicare_patients_avg_wait_time = csv_obj.get_array_slice(
        medicare_patients, 3
    )

    t_stat, p_val = csv_obj.levene(
        private_patients_avg_wait_time, medicare_patients_avg_wait_time
    )
    print(
        'Levene test reveals: T-stat: {} and P-val: {}'.format(t_stat, p_val)
    )
    print()

    t_stat, p_val = csv_obj.welch_t(
        private_patients_avg_wait_time, medicare_patients_avg_wait_time
    )
    print(
        'Welch t-test reveals: T-stat: {} and P-val: {}'.format(t_stat, p_val)
    )
    print()

    cohen_d = csv_obj.cohen_d(
        private_patients_avg_wait_time, medicare_patients_avg_wait_time
    )
    print('Cohen-d test reveals: {}'.format(cohen_d))

    print()
    print('Size of private cohort: {}'.format(
        len(private_patients_avg_wait_time))
    )
    print('Size of Medicare cohort: {}'.format(
        len(medicare_patients_avg_wait_time))
    )

    '''
    This block of code reads generates the three-level ICD9 hierarchy system
    and links them together with the diagnosis_icd table in a relational
    database format.
    '''
    csv_obj = CSVReader(
        'old_tables_from_big_query/diagnosis_icd.csv'
    )
    first_level_class = csv_obj.create_first_level_classifier()
    second_level_class = csv_obj.create_second_level_classifier()
    third_level_class = csv_obj.create_third_level_classifier()
    csv_obj.connect_second_lvl_to_first(first_level_class, second_level_class)
    csv_obj.connect_third_lvl_to_second(second_level_class, third_level_class)

    diagnosis_icd = csv_obj.generate_diagnosis_icd(third_level_class)
    csv_obj.save_to_path('new_tables_output/diagnosis_icd.csv', diagnosis_icd)

    csv_obj.save_dict_to_file('new_tables_output/first_level_icd9_codes.csv',
                              first_level_class,
                              ['primary_key', 'first_level_class'])
    csv_obj.save_dict_to_file('new_tables_output/second_level_icd9_codes.csv',
                              second_level_class,
                              ['primary_key',
                               'second_level_class', 'fk_first_level_class'])
    csv_obj.save_dict_to_file('new_tables_output/third_level_icd9_codes.csv',
                              third_level_class,
                              ['primary_key', 'third_level_class',
                               'fk_second_level_class'])
