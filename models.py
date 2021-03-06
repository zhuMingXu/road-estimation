#!/usr/bin/env python2.7
# -*- coding: utf8 -*-
from __future__ import absolute_import, print_function, unicode_literals
"""Defines classes that encapsulates the scikit-learn ML algorithms"""

#general
import numpy as np
from sklearn.externals import joblib

#model implementations
from sknn import mlp
from sklearn import svm, linear_model, tree
from sklearn.neighbors import KNeighborsClassifier
from sklearn.ensemble import AdaBoostClassifier, BaggingClassifier, RandomForestClassifier, ExtraTreesClassifier
from sklearn.mixture import GMM

# Model Class:
class Model(object):
	"""Abstract model class"""
	def __init__(self, hyperparameters):
		"""
		Attributes:
			- hyperparameters:	hyperparameters stored as a dictionary (eg. {'k': 3})

		"""
		self.hyperparameters = hyperparameters

	def train(self, train_inputs, train_targets, model_name):
		"""
		Inputs:
			- train inputs:		N x M matrix of input features (training set)
			- train targets:	1 x N array of target outputs (training set)
			- model name:		string identifying where to save the model

		Outputs:
			- None
		"""

		raise NotImplementedError

	def predict(self, test_inputs, model_name):
		"""
		Inputs:
			- test_inputs:		N x M matrix of input features (test set)
			- model name:		string identifying where to load the model

		Outputs:
			- test_pred:		1 x N array of predicted target (test set)
		"""

		raise NotImplementedError

	def evaluate(self, targets, predictions, cross_entropy_flag=False):
		"""
		Inputs:
			- targets:		1 x N array of target outputs
			- predicitions:	1 x N array of predicted target outputs

		Outputs:
			- class_rate:	scalar rate of correct responses
			- ce:			scalar cross entropy if the the cross entropy flag is true (appropriate if the test predictions are probabilities)
		"""
		targets = np.array(targets).ravel()
		predictions = np.array(predictions).ravel()

		# Cross entropy
		if (cross_entropy_flag == True):
			predictions_t1 = 0.5*np.ones(predictions.shape)
			predictions_t0 = 0.5*np.ones(predictions.shape)
			predictions_t1[targets == 1] = predictions[targets == 1]
			predictions_t0[targets == 0] = predictions[targets == 0]
			ce = -(np.dot(targets, np.log(predictions_t1)) + np.dot((1-targets), np.log(1-predictions_t0)))/float(len(targets))
		else:
			ce = None

		# Calculate the fraction of correct predictions (with y_i < 0.5 being class 0 and y_i >= 0.5 being class 1)
		predicted_class = np.zeros(predictions.shape)
		#thresholding
		predicted_class[predictions >=0.5] = 1
		class_rate = np.sum(np.equal(targets, predicted_class))/float(len(targets))


		#compute precision and recall
		true_pos = np.sum(np.logical_and(targets == 1, predicted_class == 1))
		true_neg = np.sum(np.logical_and(targets == 0, predicted_class == 0))
		false_pos = np.sum(np.logical_and(targets == 0, predicted_class == 1))
		false_neg = np.sum(np.logical_and(targets == 1, predicted_class == 0))

		precision = true_pos/float(true_pos+false_pos)
		recall = true_pos/float(true_pos+false_neg)
		f1_score = (precision*recall)/float(precision+recall)

		class_rate2 = (true_pos+true_neg)/float(true_pos+true_neg+false_pos+false_neg)

		#print("true pos: {0}; true_neg {1}; false pos {2}; false neg {3}; class rate {4}\n".format(true_pos, true_neg, false_pos, false_neg, class_rate2))

		return ce, class_rate, precision, recall, f1_score

# KNN
class KNNModel(Model):
	def train(self, train_inputs, train_targets, model_name):
		train_inputs = np.array(train_inputs)
		train_targets = np.array(train_targets)
		np.savez(model_name, train_inputs = train_inputs, train_targets = train_targets)

	def predict(self, test_inputs, model_name):
		#force test inputs to be np arrays:
		test_inputs = np.array(test_inputs)

		#unpack hyperparameters
		k = self.hyperparameters['k'] #value of k - integer

		#load model
		model_data = np.load(model_name)
		train_inputs = model_data['train_inputs']
		train_targets = model_data['train_targets'].ravel()

		#fit model
		neigh = KNeighborsClassifier(n_neighbors=k)
		neigh.fit(train_inputs, train_targets)

		#make predictions
		test_pred = np.array(neigh.predict_proba(test_inputs))
		return test_pred[:,1]

# SVM
class SVMModel(Model):
	def train(self, train_inputs, train_targets, model_name):
		#force our train inputs and targets to be np arrays
		train_inputs = np.array(train_inputs)
		train_targets = np.array(train_targets).ravel()

		#unpack hyperparameters
		kernel = self.hyperparameters['kernel'] #str: eg. 'rbf', 'poly', 'linear', 'sigmoid'
		probability_flag = self.hyperparameters['probability_flag'] #True - returns a probability; False - return a hard assignment

		#fit model
		svm_mod = svm.SVC(probability = probability_flag)
		svm_mod.fit(train_inputs, train_targets)

		#save model
		joblib.dump(svm_mod, (model_name+'.pkl'))

	def predict(self, test_inputs, model_name):
		#force test inputs to be np arrays:
		test_inputs = np.array(test_inputs)

		#unpack hyperparameters
		kernel = self.hyperparameters['kernel'] #eg. rbf
		probability_flag = self.hyperparameters['probability_flag']

		#load model
		svm_mod = joblib.load((model_name+'.pkl'))

		#make predictions
		if (probability_flag == True):
		 	test_pred = np.array(svm_mod.predict_proba(test_inputs))[:, 1]
		else:
			test_pred = np.array(svm_mod.predict(test_inputs))

		return test_pred

# Logistic Regression
class LogisticRegressionModel(Model):
	def train(self, train_inputs, train_targets, model_name):
		#force our train inputs and targets to be np arrays
		train_inputs = np.array(train_inputs)
		train_targets = np.array(train_targets).ravel()

		#unpack hyperparameters:
		penalty = self.hyperparameters['penalty'] #str 'l1' or 'l2'
		C = self.hyperparameters['C'] #float value

		#fit model
		logistic = linear_model.LogisticRegression(penalty= penalty, C=C)
		logistic.fit(train_inputs, train_targets)

		#save model
		joblib.dump(logistic, (model_name+'.pkl'))

	def predict(self, test_inputs, model_name):
		#force test inputs to be np arrays:
		test_inputs = np.array(test_inputs)

		#load model
		logistic = joblib.load((model_name+'.pkl'))

		#make predictions
		test_pred = np.array(logistic.predict_proba(test_inputs))
		return test_pred[:, 1]

# Neural networks (aka multilayer perceptron - mlp)
class NeuralNetworkModel(Model):
	def train(self, train_inputs, train_targets, model_name):
		#force our train inputs and targets to be np arrays
		train_inputs = np.array(train_inputs)
		train_targets = np.array(train_targets)

		#unpack hyperparameters:
		list_of_layers = []
		list_of_layers_params = self.hyperparameters['list_of_layers_params']
		for curr_layer_params in list_of_layers_params:
			if (curr_layer_params['role'] == 'hidden'):
				curr_layer_type = curr_layer_params['type']
				curr_layer_units = curr_layer_params['units']
				curr_layer_weight_decay = curr_layer_params['weight_decay']
				curr_layer = mlp.Layer(type = curr_layer_type, units = curr_layer_units, weight_decay = curr_layer_weight_decay)

			elif (curr_layer_params['role'] == 'output'):
				curr_layer_type = curr_layer_params['type']
				curr_layer = mlp.Layer(type = 'Softmax')


			else:
				raise NotImplementedError, "Neural Net - unknown layer type"

			list_of_layers.append(curr_layer)



		mlp_model = mlp.Classifier(layers = list_of_layers)
		mlp_model.fit(train_inputs, train_targets)

		#save model
		joblib.dump(mlp_model, (model_name+'.pkl'))


	def predict(self, test_inputs, model_name):
		#force test inputs to be np arrays:
		test_inputs = np.array(test_inputs)

		#load model
		mlp_model = joblib.load((model_name+'.pkl'))

		#make predictions
		test_pred = np.array(mlp_model.predict_proba(test_inputs))
		return test_pred[:, 1]

# Mixture of Gaussian Classifier
class MOGModel(Model):
	def train(self, train_inputs, train_targets, model_name):
		#force our train inputs and targets to be np arrays
		train_inputs = np.array(train_inputs)
		train_targets = np.array(train_targets).ravel()

		#unpack hyperparameters:
		n_components = self.hyperparameters['n_components']


		#fit model
		mog_class_0 = GMM(n_components = n_components)
		mog_class_1 = GMM(n_components = n_components)

		train_targets_ravel=train_targets.ravel()

		mog_class_0.fit(train_inputs[train_targets_ravel == 0])
		mog_class_1.fit(train_inputs[train_targets_ravel == 1])

		prior_class_1 = np.array(sum(train_targets))/float(train_targets.shape[0])

		mog_classifier = {'mog_class_0': mog_class_0, 'mog_class_1': mog_class_1, 'prior_class_1': prior_class_1}
		
		#save model
		joblib.dump(mog_classifier, (model_name+'.pkl'))

	def predict(self, test_inputs, model_name):
		#force test inputs to be np arrays:
		test_inputs = np.array(test_inputs)

		#unpack hyperparameters:
		n_components = self.hyperparameters['n_components']

		#load model
		mog_classifier = joblib.load((model_name+'.pkl'))
		mog_class_0 = mog_classifier['mog_class_0']
		mog_class_1 = mog_classifier['mog_class_1']
		prior_class_1 = mog_classifier['prior_class_1']

		#make predictions
		class_0_logp = np.array(mog_class_0.score(test_inputs))
		class_1_logp = np.array(mog_class_1.score(test_inputs))


		p_x_cond_class0 = np.exp(class_0_logp)
		p_x_cond_class1 = np.exp(class_1_logp)

		p_class1_cond_x = np.divide((p_x_cond_class1)*prior_class_1, (p_x_cond_class1)*prior_class_1+(p_x_cond_class0)*(1-prior_class_1))
		p_class0_cond_x = np.divide((p_x_cond_class0)*(1-prior_class_1), (p_x_cond_class1)*prior_class_1+(p_x_cond_class0)*(1-prior_class_1))

		#assert(np.sum(p_class1_cond_x+p_class0_cond_x) = p_class1_cond_x.shape[0])

		return p_class1_cond_x

# Decision Tree
class DecisionTreeModel(Model):
	def train(self, train_inputs, train_targets, model_name):
		#force our train inputs and targets to be np arrays
		train_inputs = np.array(train_inputs)
		train_targets = np.array(train_targets).ravel()

		#unpack hyperparamters
		criterion = self.hyperparameters['criterion']
		max_depth = self.hyperparameters['max_depth']
		min_samples_split = self.hyperparameters['min_samples_split']

		#fit decision tree
		dt_classifier = tree.DecisionTreeClassifier(criterion = criterion, max_depth = max_depth, min_samples_split = min_samples_split)
		dt_classifier.fit(train_inputs, train_targets)

		#save model
		joblib.dump(dt_classifier, (model_name+'.pkl'))

	def predict(self, test_inputs, model_name):
		#force test inputs to be np arrays:
		test_inputs = np.array(test_inputs)

		#load model
		dt_classifier = joblib.load((model_name+'.pkl'))

		#make predictions
		test_pred = dt_classifier.predict_proba(test_inputs)

		return test_pred[:, 1]

# Ensemble Methods
class EnsembleModel(Model):
	"""Abstract ensemble model class"""
	#ensemble method base classifier initialization functions
	def decision_tree_init(self):
		#unpack hyperparamters
		criterion = self.hyperparameters['criterion']
		max_depth = self.hyperparameters['max_depth']
		min_samples_split = self.hyperparameters['min_samples_split']

		#fit decision tree
		dt_classifier = tree.DecisionTreeClassifier(criterion = criterion, max_depth = max_depth, min_samples_split = min_samples_split)

		return dt_classifier

	def logistic_init(self):
		#unpack hyperparameters:
		penalty = self.hyperparameters['penalty'] #str 'l1' or 'l2'
		C = self.hyperparameters['C'] #float value

		#fit model
		logistic_classifier = linear_model.LogisticRegression(penalty= penalty, C=C)

		return logistic_classifier

# Adaboost
class AdaboostModel(EnsembleModel):
	def train(self, train_inputs, train_targets, model_name):
		#force our train inputs and targets to be np arrays
		train_inputs = np.array(train_inputs)
		train_targets = np.array(train_targets).ravel()

		#unpack hyperparamters
		algorithm_name = self.hyperparameters['algorithm_name']
		n_estimators = self.hyperparameters['n_estimators']

		if (algorithm_name == 'decision_tree'):
			base_classifier = self.decision_tree_init()

		elif (algorithm_name == 'logistic'):
			base_classifier = self.logistic_init()

		else:
			raise NotImplementedError, 'Error: Unexpected base classifier name.'

		#fit model
		adaboost_classifier = AdaBoostClassifier(base_classifier, n_estimators)
		adaboost_classifier.fit(train_inputs, train_targets)

		#save model
		joblib.dump(adaboost_classifier, (model_name+'.pkl'))

	def predict(self, test_inputs, model_name):
		#force test inputs to be np arrays:
		test_inputs = np.array(test_inputs)

		#load model
		adaboost_classifier = joblib.load((model_name+'.pkl'))

		#make predictions
		test_pred = adaboost_classifier.predict_proba(test_inputs)

		return test_pred[:, 1]

# Bagging
class BaggingModel(EnsembleModel):
	def train(self, train_inputs, train_targets, model_name):
		#force our train inputs and targets to be np arrays
		train_inputs = np.array(train_inputs)
		train_targets = np.array(train_targets).ravel()

		#unpack hyperparamters
		algorithm_name = self.hyperparameters['algorithm_name']
		n_estimators = self.hyperparameters['n_estimators']

		if (algorithm_name == 'decision_tree'):
			base_classifier = self.decision_tree_init()

		elif (algorithm_name == 'logistic'):
			base_classifier = self.logistic_init()

		else:
			raise NotImplementedError, 'Error: Unexpected base classifier name.'

		#fit model
		bagging_classifier = BaggingClassifier(base_classifier, n_estimators)
		bagging_classifier.fit(train_inputs, train_targets)

		#save model
		joblib.dump(bagging_classifier, (model_name+'.pkl'))

	def predict(self, test_inputs, model_name):
		#force test inputs to be np arrays:
		test_inputs = np.array(test_inputs)

		#load model
		bagging_classifier = joblib.load((model_name+'.pkl'))

		#make predictions
		test_pred = bagging_classifier.predict_proba(test_inputs)

		return test_pred[:, 1]

# Random Forest
class RandomForestModel(EnsembleModel):
	def train(self, train_inputs, train_targets, model_name):
		#force our train inputs and targets to be np arrays
		train_inputs = np.array(train_inputs)
		train_targets = np.array(train_targets).ravel()

		#unpack hyperparamters
		n_estimators = self.hyperparameters['n_estimators']
		criterion = self.hyperparameters['criterion']
		max_depth = self.hyperparameters['max_depth']
		min_samples_split = self.hyperparameters['min_samples_split']

		#fit model
		randomforest_classifier = RandomForestClassifier(n_estimators = n_estimators, criterion = criterion, max_depth = max_depth, min_samples_split = min_samples_split)
		randomforest_classifier.fit(train_inputs, train_targets)

		#save model
		joblib.dump(randomforest_classifier, (model_name+'.pkl'))

	def predict(self, test_inputs, model_name):
		#force test inputs to be np arrays:
		test_inputs = np.array(test_inputs)

		#load model
		randomforest_classifier = joblib.load((model_name+'.pkl'))

		#make predictions
		test_pred = randomforest_classifier.predict_proba(test_inputs)

		return test_pred[:, 1]


# Extra Trees
class ExtraTreesModel(EnsembleModel):
	def train(self, train_inputs, train_targets, model_name):
		#force our train inputs and targets to be np arrays
		train_inputs = np.array(train_inputs)
		train_targets = np.array(train_targets).ravel()

		#unpack hyperparamters
		n_estimators = self.hyperparameters['n_estimators']
		criterion = self.hyperparameters['criterion']
		max_depth = self.hyperparameters['max_depth']
		min_samples_split = self.hyperparameters['min_samples_split']

		#fit model
		extra_tree_classifier = ExtraTreesClassifier(n_estimators = n_estimators, criterion = criterion, max_depth = max_depth, min_samples_split = min_samples_split)
		extra_tree_classifier.fit(train_inputs, train_targets)

		#save model
		joblib.dump(extra_tree_classifier, (model_name+'.pkl'))

	def predict(self, test_inputs, model_name):
		#force test inputs to be np arrays:
		test_inputs = np.array(test_inputs)

		#load model
		extra_tree_classifier = joblib.load((model_name+'.pkl'))

		#make predictions
		test_pred = extra_tree_classifier.predict_proba(test_inputs)

		return test_pred[:, 1]
