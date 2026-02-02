from sklearn.metrics import mean_squared_error

import numpy as np
# Creation of a random generator:


def calculate_rmse(predictions, actual_values):
    mse = mean_squared_error(actual_values, predictions)
    rmse = np.sqrt(mse)
    return rmse


#EXAM:

#why is line above data? = awnser because we are plotting 3D data