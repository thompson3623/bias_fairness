"""Allows users to automatically import datasets and introduce bias into them, through custom datasets and pre-configured ones.

Classes
-------
DataReader
    Reads data from training and test data sets and encodes them. Data in the training set can be manipulated to introduce bias before returning.

Objects
-------
Adult
    The Adult dataset (https://archive.ics.uci.edu/ml/datasets/adult)
"""

from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd
from sklearn.preprocessing import LabelEncoder


class DataReader:
    """Reads data from training and test data sets and encodes them. Data in the training set can be manipulated to introduce bias.
    
    Methods
    -------
    training_data() -> Tuple[pandas.DataFrame, pandas.DataFrame, pandas.DataFrame]
        Gets and encodes the training data, the label column(s), and the sensitive attribute(s).
        
    training_data_historical_bias(TBD) -> Tuple[pandas.DataFrame, pandas.DataFrame, pandas.DataFrame]
        TBD
        
    training_data_representation_bias(TBD) -> Tuple[pandas.DataFrame, pandas.DataFrame, pandas.DataFrame]
        TBD
    
    training_data_feature_bias(TBD) -> Tuple[pandas.DataFrame, pandas.DataFrame, pandas.DataFrame]
        TBD
    
    training_data_label_bias(flip_rate: float) -> Tuple[pandas.DataFrame, pandas.DataFrame, pandas.DataFrame]
        Gets and encodes the training data, the label column(s), and the sensitive attribute(s). Flips the values of the label column(s) at the rate specified.
    
    test_data() -> Tuple[pandas.DataFrame, pandas.DataFrame, pandas.DataFrame]
        Gets and encodes the test data, the label column(s), and the sensitive attribute(s).
    """
    
    def __init__(self, 
                 types: Dict[str, Any], 
                 training_data_path: str, 
                 test_data_path: str, 
                 label_column_names: List[str], 
                 sensitive_attribute_column_names: List[str]) -> None:
        """
        Parameters
        ----------
        types: Dict[str, Any]
            Dict object that has the names of each column in the data and the data type of the column
        training_data_path: str
            Filepath to the training data file.
        test_data_path: str
            Filepath to the test data file.
        label_column_names: List[str]
            Names of each of the columns to be considered as labels. Must be a subset of the column names provided in types.
        sensitive_attribute_column_names:
            Names of each of the columns to be considered sensitive attributes. Must be a subset of the column names provided in types.
        
        Raises
        ------
        ValueError
            If the file path to the training or test data does not exist, or the column names provided in label_column_names or sensitive_attribute_column_names are not a subset of the column names provided in types.
        """
        
        self.__encoder: LabelEncoder = LabelEncoder()
        self.__types: Dict[str, Any] = types
        self.__features: list = list(types.keys())
        
        self.__training_path: Path = Path(training_data_path)
        if not (self.__training_path.is_file()):
            raise ValueError("Path to training data file does not exist.")
        
        self.__test_path: Path = Path(test_data_path)
        if not (self.__test_path.is_file()):
            raise ValueError("Path to test data file does not exist.")
        
        for label_name in label_column_names:
            if label_name not in self.__features:
                raise ValueError("Label column names must be a subset of the column names provided in types.")
        self.__label_column_names: List[str] = label_column_names
        
        for sensitive_attribute in sensitive_attribute_column_names:
            if sensitive_attribute not in self.__features:
                raise ValueError("Sensitive attribute column names must be a subset of the column names provided in types.")
        self.__sensitive_attribute_column_names: List = sensitive_attribute_column_names
        
    def __read_file(self, is_test: bool) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """Reads the data file at the location of either the training data or test data.
        
        Parameters
        ----------
        is_test: bool
            Determines where the data should be read from. True denotes test data file and False denotes training data file.
            
        Returns
        -------
        Tuple[pandas.DataFrame, pandas.DataFrame, pandas.DataFrame]
            The data, the label column(s) of the data, and the sensitive attribute(s) of the data.
        
        Raises
        ------
        IOError
            If the file being read cannot be found.
        """
        try:
            df = pd.read_csv(self.__test_path if is_test else self.__training_path, 
                            names = self.__features, 
                            dtype = self.__types, 
                            sep=r'\s*,\s*', 
                            engine='python', 
                            skiprows = 1 if is_test else 0)
        except IOError as e:
            t: str = 'Test' if is_test else 'Training'
            raise IOError('{t} file not found at the location specified')
        labels = df[self.__label_column_names]
        sensitive_attributes = df[self.__sensitive_attribute_column_names]
        
        return df, labels, sensitive_attributes
    
    def __encode_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Encodes all non-numerical columns in the given Dataframe. 
        
        Parameters
        ----------
        df: pandas.DataFrame
            The DataFrame to be encoded.
        
        Returns
        -------
        pandas.DataFrame
            The encoded DataFrame.
        """
        
        for colName in df.columns:
            if not pd.api.types.is_numeric_dtype(df[colName]):
                df[colName] = self.__encoder.fit_transform(y = df[colName])
        return df
    
    def __read_encoded_dataframe(self, is_test: bool) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """Gets the training or test data, and encodes all non-numeric columns.
        
        Parameters
        ----------
        is_test: bool
            Determines where the data should be read from. True denotes test data file and False denotes training data file.
        
        Returns
        -------
        Tuple[pandas.DataFrame, pandas.DataFrame, pandas.DataFrame]
            The encoded data, the encoded label column(s) of the data, and the encoded sensitive attribute(s) of the data.
        """
        
        data, labels, sensitive_attributes = self.__read_file(is_test = is_test)
        
        data = self.__encode_dataframe(data)
        labels = self.__encode_dataframe(labels)
        sensitive_attributes = self.__encode_dataframe(sensitive_attributes)
        
        return data, labels, sensitive_attributes
    
    def training_data(self) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """Gets and encodes the training data, the label column(s), and the sensitive attribute(s).
        
        Returns
        -------
        Tuple[pandas.DataFrame, pandas.DataFrame, pandas.DataFrame]
            The encoded training data, the encoded label column(s) of the data, and the encoded sensitive attribute(s) of the data.
        """
        
        return self.__read_encoded_dataframe(is_test = False)
    
    def training_data_label_bias(self, flip_rate: float) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """Gets and encodes the training data, the label column(s), and the sensitive attribute(s), then flips the values in the label column(s) at the rate specified.
        
        Parameters
        ----------
        flip_rate: float
            Rate at which values in the label column(s) should be flipped. Valid values range from 0.00 (0% flip rate) to 1.00 (100% flip rate).
        
        Returns
        -------
        Tuple[pandas.DataFrame, pandas.DataFrame, pandas.DataFrame]
            The encoded training data, the encoded label column(s) of the data, and the encoded sensitive attribute(s) of the data.
            
        Raises
        ------
        ValueError
            If flip_rate is not between 0 and 1, inclusive.
        """
        
        if flip_rate > 1 or flip_rate < 0:
            raise ValueError('flip_rate must be between 0 and 1 inclusive')
        data, labels, sensitive_attributes = self.__read_encoded_dataframe(is_test = False)
        
        # randomly flip labels
        
        return data, labels, sensitive_attributes
    
    def test_data(self) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """Gets and encodes the test data, the label column(s), and the sensitive attribute(s).
        
        Returns
        -------
        Tuple[pandas.DataFrame, pandas.DataFrame, pandas.DataFrame]
            The encoded test data, the encoded label column(s) of the data, and the encoded sensitive attribute(s) of the data.
        """
        
        return self.__read_encoded_dataframe(is_test = True)
        
Adult = DataReader(
    types = {
        'Age': np.int64, 
        'Workclass': 'string',
        'fnlwgt': np.int64,
        'Education': 'string',
        'Education-Num': np.int64,
        'Marital Status': 'string',
        'Occupation': 'string',
        'Relationship': 'string',
        'Race': 'string',
        'Sex': 'string',
        'Capital Gain': np.int64,
        'Capital Loss': np.int64,
        'Hours per week': np.int64,
        'Country': 'string',
        'Target': 'string' },
    training_data_path = './Data/Adult/adult.data',
    test_data_path = './Data/Adult/adult.test',
    label_column_names = ['Target'],
    sensitive_attribute_column_names = ['Race', 'Sex'])