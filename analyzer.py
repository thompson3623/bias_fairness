import pandas as pd
import numpy as np
import multiprocessing as mp

from fairlearn.reductions import DemographicParity, ExponentiatedGradient
from fairlearn.metrics import demographic_parity_ratio
from functools import partial
from multiprocessing import Pool
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score

from data_reader import DataReader


result_columns = ['Flip Rate',
                  'Confidence Threshold', 
                  'Unconstrained Accuracy', 
                  'Unconstrained DP Ratio', 
                  'DP Constrained Accuracy', 
                  'DP Constrained DP Ratio']

def analyze_label_bias(dataReader: DataReader, flip_interval: float, cpu_count: int = mp.cpu_count()):    
    if __name__ == '__main__':
        __label_bias_trial(dataReader, flip_interval, cpu_count)

def __label_bias_trial(dataReader: DataReader, flip_interval: float, cpu_count: int = mp.cpu_count()):
    initial_data, initial_labels = dataReader.training_data()
    test_data, test_labels = dataReader.test_data()
    
    print('Training initial model')
    initial_estimator = LogisticRegression(max_iter = 10000, n_jobs = -1)
    initial_estimator.fit(X = initial_data, y = initial_labels)
    print('Initial model trained')
    
    pool: Pool = Pool(cpu_count)
    variable_args = [(flip_rate, 1) for flip_rate in np.arange(0, 1 + flip_interval, flip_interval).tolist()]
    dfs = pool.starmap(partial(__label_bias_fetch_train_constrain,
                               dataReader=dataReader,
                               initial_data=initial_data,
                               initial_labels=initial_labels, 
                               initial_estimator=initial_estimator,
                               training_sensitive_attributes=dataReader.training_sensitive_attributes(),
                               test_data=test_data,
                               test_labels=test_labels,
                               test_sensitive_attributes=dataReader.test_sensitive_attributes()),
                       variable_args)
    results: pd.DataFrame = pd.concat(dfs, ignore_index=True)
    print('Writing results to file')
    results.to_csv('./Results/results.csv')
    
def __label_bias_fetch_train_constrain(flip_rate: float, 
                                       confidence_threshold: float, 
                                       dataReader: DataReader, 
                                       initial_data: pd.DataFrame, 
                                       initial_labels: pd.Series, 
                                       initial_estimator: LogisticRegression, 
                                       training_sensitive_attributes: pd.DataFrame, 
                                       test_data: pd.DataFrame, 
                                       test_labels: pd.Series, 
                                       test_sensitive_attributes: pd.DataFrame):
    print(f'Flip rate {flip_rate:.2f}: start')
    if flip_rate == 0:
        training_data, training_labels = initial_data, initial_labels
        estimator = initial_estimator
    else:
        training_data, training_labels = dataReader.training_data_label_bias(flip_rate, confidence_threshold, initial_estimator)
        estimator = LogisticRegression(max_iter = 10000)
        estimator.fit(X = training_data, y = training_labels)
    
    constraint = DemographicParity(difference_bound = 0.01)
    mitigator_dp = ExponentiatedGradient(estimator = estimator, constraints = constraint)
    mitigator_dp.fit(X = training_data, y = training_labels, sensitive_features = training_sensitive_attributes)    
    
    prediction_unc = estimator.predict(X = test_data)
    prediction_dp = mitigator_dp.predict(X = test_data)
    
    result: pd.DataFrame = pd.DataFrame(columns=result_columns)
    result.loc[0] = [flip_rate,
                     confidence_threshold, 
                     accuracy_score(test_labels, prediction_unc),
                     demographic_parity_ratio(y_true = test_labels, 
                                              y_pred = prediction_unc, 
                                              sensitive_features = test_sensitive_attributes),
                     accuracy_score(test_labels, prediction_dp),
                     demographic_parity_ratio(y_true = test_labels, 
                                              y_pred = prediction_dp, 
                                              sensitive_features = test_sensitive_attributes)]
    print(f'Flip rate {flip_rate:.2f}: done')
    return result