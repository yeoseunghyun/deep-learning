from __future__ import absolute_import
from __future__ import print_function

from keras.datasets import mnist
from keras.models import Sequential
from keras.layers.core import Dense, Dropout, Activation
from keras.optimizers import SGD
from keras.utils import np_utils

from elephas.spark_model import SparkModel
from elephas.utils.rdd_utils import to_simple_rdd
from elephas import optimizers as elephas_optimizers

from pyspark import SparkContext, SparkConf

# Define basic parameters
batch_size = 32
nb_classes = 10
nb_epoch = 30

import os

if __name__ == "__main__":
	#os.environ["PYSPARK_PYTHON"] = "/home/spark/anaconda2/bin/python"
	
	# Create Spark context
	conf = SparkConf().setAppName('Mnist_Spark_MLP_cloud')#.setMaster('local[6]')
	sc = SparkContext(conf=conf)

	# Load data
	(x_train, y_train), (x_test, y_test) = mnist.load_data()

	x_train = x_train.reshape(60000, 784)
	x_test = x_test.reshape(10000, 784)
	x_train = x_train.astype("float32")
	x_test = x_test.astype("float32")
	x_train /= 255
	x_test /= 255
	print(x_train.shape[0], 'train samples')
	print(x_test.shape[0], 'test samples')

	# Convert class vectors to binary class matrices
	y_train = np_utils.to_categorical(y_train, nb_classes)
	y_test = np_utils.to_categorical(y_test, nb_classes)

	model = Sequential()
	model.add(Dense(128, input_dim=784))
	model.add(Activation('relu'))
	model.add(Dropout(0.2))
	model.add(Dense(128))
	model.add(Activation('relu'))
	model.add(Dropout(0.2))
	model.add(Dense(10))
	model.add(Activation('softmax'))

	# Compile model
	sgd = SGD(lr=0.1)
	model.compile(loss='categorical_crossentropy', optimizer=sgd)
	# Build RDD from numpy features and labels
	rdd = to_simple_rdd(sc, x_train, y_train)

	# Initialize SparkModel from Keras model and Spark context
	print(model.to_yaml())
	adagrad = elephas_optimizers.Adagrad()
	spark_model = SparkModel(sc,
	                         model,
	                         optimizer=adagrad,
	                         frequency='epoch',
	                         mode='synchronous',
	                         num_workers=4)

	# Train Spark model
	#try :
	#	spark_model.train(rdd, nb_epoch=nb_epoch, batch_size=batch_size, verbose=2, validation_split=0.1)
	#except Exception, err:
	#	print Exception, err

	spark_model.train(rdd, nb_epoch=nb_epoch, batch_size=batch_size, verbose=2, validation_split=0.1)

	# Evaluate Spark model by evaluating the underlying model
	score = spark_model.master_network.evaluate(x_test, y_test, show_accuracy=True, verbose=2)
	print(score)
