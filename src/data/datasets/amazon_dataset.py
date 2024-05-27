from __future__ import annotations
import gzip
import itertools
import json
import os
import pickle
import random
import zipfile
from collections import Counter
from functools import cached_property
from typing import Literal, Dict

import datasets
import gdown
import pandas as pd
from datasets import Dataset
from gdown.exceptions import FileURLRetrievalError

from src import RAW_DATA_DIR
from src.data.abstract_dataset import AnonDataset
from src.utils import dict_list2list_dict, list_dict2dict_list, PrintWithSpin


def parse(path):
    with gzip.open(path, 'r') as g:
        for raw_meta_dict in g:
            yield eval(raw_meta_dict)


class AmazonDataset(AnonDataset):

    def __init__(self,
                 dataset_name: Literal['beauty', 'toys', 'sport'],
                 add_prefix_items_users: bool = True,
                 items_start_from_1001: bool = False):

        # this will download and extract raw data zip
        super().__init__()

        self.dataset_name = dataset_name
        self.add_prefix = add_prefix_items_users
        self.items_start_from_1001 = items_start_from_1001

        # read mapping between user/item string id (ABXMSBDSI) and user/item int id (331)
        with open(os.path.join(RAW_DATA_DIR, "AmazonDataset", self.dataset_name, 'datamaps.json'), "r") as f:
            datamaps = json.load(f)

        self.user2id = {str(key): str(val) for key, val in datamaps['user2id'].items()}
        self.item2id = {str(key): str(val) for key, val in datamaps['item2id'].items()}
        self.id2user = {str(key): str(val) for key, val in datamaps['id2user'].items()}
        self.id2item = {str(key): str(val) for key, val in datamaps['id2item'].items()}

        # read mapping between user int id (331) and username (Melissa)
        with open(os.path.join(RAW_DATA_DIR, "AmazonDataset", self.dataset_name, "user_id2name.pkl"), "rb") as f:
            self.user_id2name = pickle.load(f)

        with PrintWithSpin("Reading sequential data"):
            user_items, _ = self._read_sequential()

        with PrintWithSpin("Reading ratings data"):
            user_items = self._read_ratings(user_items)

        # here we save meta information (the "content") about items.
        # We only save info about items which appear in the user profiles
        relevant_items = set(self.item2id.keys())
        self.meta_dict = {}
        with PrintWithSpin("Extracting side-information"):
            for meta_content in parse(os.path.join(RAW_DATA_DIR, "AmazonDataset", self.dataset_name, 'meta.json.gz')):
                item = meta_content.pop("asin")
                if item in relevant_items:
                    item_id = self.item2id[item]

                    # categories are list of lists for no reason
                    meta_content["categories"] = meta_content["categories"][0]
                    self.meta_dict[item_id] = meta_content

        df_dict = {
            "user_id": [],
            "user_name": [],
            "user_asin": [],
            "item_sequence": [],
            "rating_sequence": [],
            "title_sequence": [],
            "description_sequence": [],
            "categories_sequence": [],
            "price_sequence": [],
            "imurl_sequence": [],
            "brand_sequence": []
        }

        with PrintWithSpin("Creating tabular data"):
            for user_id, item_list_ids in user_items.items():

                user_col_repeated = [user_id for _ in range(len(item_list_ids))]
                user_name_col_repeated = [self.user_id2name.get(user_id, "") for _ in range(len(item_list_ids))]
                user_asin_col_repeated = [self.id2user.get(user_id, "") for _ in range(len(item_list_ids))]
                [item_col_value, ratings_col_value] = list(zip(*item_list_ids))

                df_dict["user_id"].extend(user_col_repeated)
                df_dict["user_name"].extend(user_name_col_repeated)
                df_dict["user_asin"].extend(user_asin_col_repeated)
                df_dict["item_sequence"].extend(item_col_value)
                df_dict["rating_sequence"].extend(map(str, ratings_col_value))

                for item_id in item_col_value:
                    desc = self.meta_dict[item_id].get("description", "")
                    item_categories = self.meta_dict[item_id].get("categories", [])
                    title = self.meta_dict[item_id].get("title", "")
                    price = self.meta_dict[item_id].get("price", "")
                    imurl = self.meta_dict[item_id].get("imUrl", "")
                    brand = self.meta_dict[item_id].get("brand", "")

                    df_dict["description_sequence"].append(str(desc))
                    df_dict["categories_sequence"].append(item_categories)
                    df_dict["title_sequence"].append(str(title))
                    df_dict["price_sequence"].append(str(price))
                    df_dict["imurl_sequence"].append(str(imurl))
                    df_dict["brand_sequence"].append(str(brand))

            data_df = pd.DataFrame.from_dict(df_dict)

        # start indexing from 1001 for better tokenization sentencepiece
        if self.items_start_from_1001:
            data_df["item_sequence"] = data_df["item_sequence"].astype(int) + 1000
            data_df["item_sequence"] = data_df["item_sequence"].astype(str)

        if self.add_prefix:
            data_df["user_id"] = "user_" + data_df["user_id"]
            data_df["item_sequence"] = "item_" + data_df["item_sequence"]

        self.original_df = data_df

        with PrintWithSpin("Splitting data with Leave One Out protocol"):
            self.train_df, self.val_df, self.test_df = self.split_data(data_df)

    @cached_property
    def all_users(self):
        return pd.unique(self.original_df["user_id"])

    @cached_property
    def all_items(self):
        return pd.unique(self.original_df["item_sequence"].explode())

    @property
    def items_meta_dict(self):
        return self.meta_dict

    def download_extract_raw_dataset(self):

        # url of dataset is https://drive.google.com/uc?id=1qGxgmx7G_WB7JE4Cn_bEcZ_o_NAJLE3G
        id_gdrive_dataset = "1qGxgmx7G_WB7JE4Cn_bEcZ_o_NAJLE3G&confirm=t"
        raw_data_folder_out = os.path.join(RAW_DATA_DIR, "AmazonDataset")
        raw_data_zip_path = os.path.join(RAW_DATA_DIR, "P5_data.zip")

        if not os.path.isdir(raw_data_folder_out):

            if not os.path.isfile(raw_data_zip_path):
                print("# Downloading raw Amazon Dataset:")

                try:
                    gdown.download(id=id_gdrive_dataset, output=raw_data_zip_path)
                except FileURLRetrievalError:
                    raise FileURLRetrievalError("Permission denied to download the dataset or dataset removed!\n"
                                                "Please check if you the dataset still exists here: "
                                                "https://drive.google.com/uc?id=1qGxgmx7G_WB7JE4Cn_bEcZ_o_NAJLE3G\n"
                                                "If yes, try to upgrade the gdown library with 'pip install -U gdown' "
                                                "(or any other package manager you use) or download the .zip manually "
                                                "from the link above and move it into 'data/raw' folder!") from None

                print("Done!")
            else:
                print("# ZIP file found, skipping download phase")

            # create AmazonDataset folder inside raw
            os.makedirs(raw_data_folder_out)

            with PrintWithSpin("Extracting datasets from zip"):

                # process output path of zip file to extract, in order to not have
                # "AmazonDataset/data/beauty/**" but simply "AmazonDataset/beauty/**"
                subfolder_to_extract = ["beauty", "sports", "toys"]
                with zipfile.ZipFile(raw_data_zip_path, 'r') as zip_ref:

                    for subfolder in subfolder_to_extract:
                        dir_to_extract = f"data/{subfolder}/"

                        for path_in_zip in zip_ref.namelist():
                            if path_in_zip.startswith(dir_to_extract):
                                zip_ref.getinfo(path_in_zip).filename = "/".join(path_in_zip.split("/")[1:])
                                zip_ref.extract(member=path_in_zip, path=raw_data_folder_out)

            # remove zip once we are done
            os.remove(raw_data_zip_path)
        else:
            print("# Amazon Dataset found, skipping download and extraction part")

    def split_data(self, exploded_data_df: pd.DataFrame):

        # For Amazon Dataset, Leave One Out is performed following P5 paper

        groupby_obj = exploded_data_df.groupby(by=["user_id", "user_name", "user_asin"])

        # train set will be divided into input and target at each epoch: we will sample
        # each time a different input sequence and target item for each user so to reduce chances of
        # overfitting and performing a sort of augmentation in real time
        train_set = groupby_obj.nth[:-2].groupby(by=["user_id", "user_name", "user_asin"]).agg(list).reset_index()

        # since validation set and test set do not need sampling (they must remain constant in order to validate
        # and evaluate the model fairly across epochs), we split directly here data in input and target.
        # It would be better to validate and test using entirely unknown users, but
        # in this phase we adhere to evaluation protocol of authors

        # if sequence is -> [1 2 3 4 5 6 7 8], VAL SET will have
        # input_sequence: [1 2 3 4 5 6]
        # gt_item: [7]
        input_val_set = groupby_obj.nth[:-2].rename(columns={
            "item_sequence": "input_item_seq",
            "rating_sequence": "input_rating_seq",
            "description_sequence": "input_description_seq",
            "categories_sequence": "input_categories_seq",
            "title_sequence": "input_title_seq",
            "price_sequence": "input_price_seq",
            "imurl_sequence": "input_imurl_seq",
            "brand_sequence": "input_brand_seq"
        })
        input_val_set = input_val_set.groupby(by=["user_id", "user_name", "user_asin"]).agg(list).reset_index()

        gt_val_set = groupby_obj.nth[-2].rename(columns={
            "item_sequence": "gt_item",
            "rating_sequence": "gt_rating",
            "description_sequence": "gt_description",
            "categories_sequence": "gt_categories",
            "title_sequence": "gt_title",
            "price_sequence": "gt_price",
            "imurl_sequence": "gt_imurl",
            "brand_sequence": "gt_brand"})
        # this is done only for generality purpose, in order to have a list wrapping all target item
        # features. We are performing Leave One Out, so we are sure there is only one item
        gt_val_set = gt_val_set.groupby(by=["user_id", "user_name", "user_asin"]).agg(list).reset_index()

        val_set = input_val_set.merge(gt_val_set, on=["user_id", "user_name", "user_asin"])

        # if sequence is -> [1 2 3 4 5 6 7 8], TEST SET will have
        # input_sequence: [1 2 3 4 5 6 7]
        # gt_item: [8]
        input_test_set = groupby_obj.nth[:-1].rename(columns={
            "item_sequence": "input_item_seq",
            "rating_sequence": "input_rating_seq",
            "description_sequence": "input_description_seq",
            "categories_sequence": "input_categories_seq",
            "title_sequence": "input_title_seq",
            "price_sequence": "input_price_seq",
            "imurl_sequence": "input_imurl_seq",
            "brand_sequence": "input_brand_seq"})
        input_test_set = input_test_set.groupby(by=["user_id", "user_name", "user_asin"]).agg(list).reset_index()

        gt_test_set = groupby_obj.nth[-1].rename(columns={
            "item_sequence": "gt_item",
            "rating_sequence": "gt_rating",
            "description_sequence": "gt_description",
            "categories_sequence": "gt_categories",
            "title_sequence": "gt_title",
            "price_sequence": "gt_price",
            "imurl_sequence": "gt_imurl",
            "brand_sequence": "gt_brand"})
        # this is done only for generality purpose, in order to have a list wrapping all target item
        # features. We are performing Leave One Out, so we are sure there is only one item
        gt_test_set = gt_test_set.groupby(by=["user_id", "user_name", "user_asin"]).agg(list).reset_index()

        test_set = input_test_set.merge(gt_test_set, on=["user_id", "user_name", "user_asin"])

        return train_set, val_set, test_set

    @staticmethod
    def sample_train_sequence(batch: Dict[str, list]) -> Dict[str, list]:

        batch = dict_list2list_dict(batch)

        out_dict_list = []
        for sample in batch:
            single_out_dict = {}

            if len(sample["item_sequence"]) < 2:
                raise ValueError(f"{sample['user_id']} has less than 2 items in its order history, can't divide "
                                 "in input and ground truth!")

            elif len(sample["item_sequence"]) == 2:
                # if we have only two data points, then we have no choice and consider only a sequence of
                # one data point as input
                minimum_sliding_size = 1
            else:
                # if the sequence 3 or more data points, then we prefer to have input sequences of
                # at least 2 data points
                minimum_sliding_size = 2

            # a training sequence has at least 1 data point (2 if the sequence has at least 3 data points),
            # but it can have more depending on the length of the sequence
            # We must ensure that at least an element can be used as ground truth (that's why -1).
            # In the "sliding_size" is included the ground truth item
            sliding_size = random.randint(minimum_sliding_size, len(sample["item_sequence"]) - 1)

            start_index = random.randint(0, len(sample["item_sequence"]) - sliding_size - 1)  # -1 since we start from 0
            end_index = start_index + sliding_size

            single_out_dict["user_id"] = sample["user_id"]
            single_out_dict["user_name"] = sample["user_name"]
            single_out_dict["user_asin"] = sample["user_asin"]
            single_out_dict["input_item_seq"] = sample["item_sequence"][start_index:end_index]
            single_out_dict["input_rating_seq"] = sample["rating_sequence"][start_index:end_index]
            single_out_dict["input_description_seq"] = sample["description_sequence"][start_index:end_index]
            single_out_dict["input_categories_seq"] = sample["categories_sequence"][start_index:end_index]
            single_out_dict["input_title_seq"] = sample["title_sequence"][start_index:end_index]
            single_out_dict["input_price_seq"] = sample["price_sequence"][start_index:end_index]
            single_out_dict["input_imurl_seq"] = sample["imurl_sequence"][start_index:end_index]
            single_out_dict["input_brand_seq"] = sample["brand_sequence"][start_index:end_index]

            single_out_dict["gt_item"] = [sample["item_sequence"][end_index]]
            single_out_dict["gt_rating"] = [sample["rating_sequence"][end_index]]
            single_out_dict["gt_description"] = [sample["description_sequence"][end_index]]
            single_out_dict["gt_categories"] = [sample["categories_sequence"][end_index]]
            single_out_dict["gt_title"] = [sample["title_sequence"][end_index]]
            single_out_dict["gt_price"] = [sample["price_sequence"][end_index]]
            single_out_dict["gt_imurl"] = [sample["imurl_sequence"][end_index]]
            single_out_dict["gt_brand"] = [sample["brand_sequence"][end_index]]

            out_dict_list.append(single_out_dict)

        return list_dict2dict_list(out_dict_list)

    def _read_sequential(self):

        user_items = dict()

        with open(os.path.join(RAW_DATA_DIR, "AmazonDataset", self.dataset_name, "sequential_data.txt")) as f:
            for user_item_sequence in f:
                # user_item sequence is in the form {user_id}, {item_id}, {item_id}, ... {item_id}
                item_sequence = [str(item_id) for item_id in user_item_sequence.split()]
                user_id = str(item_sequence.pop(0))
                user_items[user_id] = item_sequence

        # count occurrences of each time (we must flatten) the item sequences first
        item_count = dict(Counter(itertools.chain.from_iterable(user_items.values())))

        return user_items, item_count

    def _read_ratings(self, user_items: dict):

        with open(os.path.join(RAW_DATA_DIR, "AmazonDataset", self.dataset_name,
                               "rating_splits_augmented.pkl"), "rb") as f:
            ratings_list = pickle.load(f)

        # here we use data from all splits because these splits originally are different
        # from the splits used for sequential data (i.e., the test item is different
        # from the test item in the sequential data), which does not make a lot of sense.
        # That's why we fix this by considering the splits defined for the sequential data.
        # This also gives us more flexibility: if another split protocol should be used,
        # in split_data() method you fully control how ALL data is split, rather than
        # controlling how data is split for each task independently

        for rating_dict in ratings_list["train"] + ratings_list["val"] + ratings_list["test"]:
            user_id = self.user2id[rating_dict["reviewerID"]]
            item_id = self.item2id[rating_dict["asin"]]
            # rating is an integer number between 1 and 5 (included)
            rating = int(rating_dict["overall"])

            item_sequence = user_items[user_id]

            # if the rating is for an item id which is not present in the sequence of items rated by the user,
            # we don't consider it
            try:
                item_index = item_sequence.index(item_id)

                user_items[user_id][item_index] = (item_id, rating)
            except ValueError:
                pass

        return user_items

    def get_hf_datasets(self, merge_train_val: bool = False) -> Dict[str, datasets.Dataset]:

        train_df = self.train_df
        val_df = self.val_df
        test_df = self.test_df

        # we create a dataset dict containing each split
        dataset_dict = {}

        if merge_train_val is True:
            groupby_obj = self.original_df.groupby(by=["user_id"])

            # if we don't use val, and we must merge, basically only the last item of each sequence should be unknown
            train_df = groupby_obj.nth[:-1].groupby(by=["user_id"]).agg(list).reset_index()
            train_hf_ds = Dataset.from_pandas(train_df, split=datasets.Split.TRAIN, preserve_index=False)
            dataset_dict["train"] = train_hf_ds
        else:
            train_hf_ds = Dataset.from_pandas(train_df, split=datasets.Split.TRAIN, preserve_index=False)
            val_hf_ds = Dataset.from_pandas(val_df, split=datasets.Split.VALIDATION, preserve_index=False)
            dataset_dict["train"] = train_hf_ds
            dataset_dict["validation"] = val_hf_ds

        test_hf_ds = Dataset.from_pandas(test_df, split=datasets.Split.TEST, preserve_index=False)
        dataset_dict["test"] = test_hf_ds

        return dataset_dict

    def save(self, output_dir: str):

        output_path = os.path.join(output_dir, "amzn_dat.pkl")
        with open(output_path, "wb") as f:
            pickle.dump(self, f)

    @classmethod
    def load(cls, dir_path: str) -> AmazonDataset:

        dat_path = os.path.join(dir_path, "amzn_dat.pkl")
        with open(dat_path, "rb") as f:
            obj = pickle.load(f)

        return obj
