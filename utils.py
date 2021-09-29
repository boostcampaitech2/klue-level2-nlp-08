import ast
import pickle

import torch
from torch.utils.data import Dataset, WeightedRandomSampler

from sklearn.model_selection import train_test_split
import pandas as pd
import numpy as np


class RelationExtractionDataset(Dataset):
    """
    A dataset class for loading Relation Extraction data
    """

    def __init__(self, pair_dataset, labels, phase, split_ratio=0.2):
        self.labels = labels
        self.phase = phase
        self.split_ratio = split_ratio
        self.data_inven = self.get_data(pair_dataset)

        torch.manual_seed(42)

    def get_data(self, pair_dataset):
        submission_counts = get_submission_counts()

        valid_idx = list(WeightedRandomSampler([submission_counts[label] for label in self.labels],
                                               replacement=False, num_samples=int(len(self.labels)*self.split_ratio)))
        train_idx = set(range(len(self.labels))) - set(valid_idx)
        # train_idx, valid_idx = train_test_split(np.arange(len(
        #     self.labels)), test_size=self.split_ratio, random_state=42, shuffle=True, stratify=self.labels)
        pd_pair_dataset = pd.DataFrame()

        for key, val in pair_dataset.items():
            pd_pair_dataset[key] = val

        pd_pair_dataset['labels'] = torch.tensor(self.labels)

        if self.phase == 'train':
            index = train_idx
        elif self.phase == 'validation':
            index = valid_idx

        temp_df = pd.DataFrame(pd_pair_dataset, index=index)
        temp_df.reset_index(inplace=True, drop=True)

        return temp_df

    def __getitem__(self, idx):
        return dict(self.data_inven.iloc[idx])

    def __len__(self):
        return len(self.data_inven)


class DataHelper:
    """
    A helper class for data loading and processing
    """

    def __init__(self, data_dir):
        self._raw = pd.read_csv(data_dir)

    def preprocess(self, data=None, mode='train'):
        if data is None:
            data = self._raw

        def extract(data): return ast.literal_eval(data)['word']

        subjects = list(map(extract, data['subject_entity']))
        objects = list(map(extract, data['object_entity']))

        preprocessed = pd.DataFrame({
            'id': data['id'],
            'sentence': data['sentence'],
            'subject_entity': subjects,
            'object_entity': objects,
            'label': data['label']
        })
        if mode == 'train':
            labels = self.convert_labels_by_dict(labels=data['label'])
        elif mode == 'inference':
            labels = data['label']

        return preprocessed, labels

    def tokenize(self, data, tokenizer):
        concated_entities = [
            sub + '[SEP]' + obj for sub, obj in zip(data['subject_entity'], data['object_entity'])
        ]
        tokenized = tokenizer(
            concated_entities,
            data['sentence'].tolist(),
            truncation=True,
        )
        return tokenized

    def convert_labels_by_dict(self, labels, dictionary='data/dict_label_to_num.pkl'):
        with open(dictionary, 'rb') as f:
            dictionary = pickle.load(f)
        return [dictionary[label] for label in labels]


def get_submission_counts():
    with open('data/dict_label_to_num.pkl', 'rb') as f:
        dict_label_to_num = pickle.load(f)

    count_dict = {label: 0 for label in dict_label_to_num.keys()}

    for submission_idx in range(1, 11):
        submission_df = pd.read_csv(
            f'./submissions/output ({submission_idx}).csv')
        value_counts = submission_df['pred_label'].value_counts()

        for label, counts in value_counts.items():
            count_dict[label] += counts

    return {dict_label_to_num[label]: count for label, count in count_dict.items()}
