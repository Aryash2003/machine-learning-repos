from functions import *
import pandas as pd
import numpy as np
import re
import nltk
from sklearn.metrics import accuracy_score,precision_score,f1_score,plot_confusion_matrix,recall_score
import matplotlib.pyplot as plt
import seaborn as sns
from nltk.tokenize import word_tokenize 
from numpy import array
from sklearn.metrics import confusion_matrix,plot_confusion_matrix
from keras.preprocessing.text import one_hot
from keras.preprocessing.sequence import pad_sequences
from sklearn.model_selection import train_test_split
from keras.preprocessing.text import Tokenizer
import tensorflow as tf
from tensorflow.keras.models import Sequential
from keras.layers import Conv1D, MaxPooling1D,Dropout,Dense,Flatten,Reshape,Concatenate,MaxPool1D,LSTM,Embedding,Bidirectional
from keras.engine.input_layer import Input
from keras.models import Model
import gensim

#Reading data from CSV
extract_zip()
train_data1 = pd.read_csv("/content/train-balanced-sarcasm.csv")     
train_data1.isnull().values.any()
train_data1.shape
print(train_data1.head())
test_data1 = pd.read_csv("/content/drive/My Drive/Amazon dataset/finalAmazonDataset.csv")
test_data1.isnull().values.any()
test_data1.shape
print(test_data1.head())

#Data Preprocessing
new = []
for parent_comment, comment in zip(train_data1['parent_comment'],train_data1['comment']):
  new.append(str(parent_comment)+str(comment))
ser = pd.Series(new)
train_data1['comment'] = ser
train_data1.info()
train_data = train_data1[['label', 'comment']].dropna()
train_data
training_size = int(round(train_data['label'].count(), -1) * 0.8)
print(training_size)   
print('total size of whole dataset',train_data['label'].count())
X = []
sentences = list(train_data['comment'])
for sen in sentences:
    
    sen_processed = preprocess_text(sen)
    X.append(sen_processed)
ama_comm = []
sentences = list(test_data1['review'])
for sen in sentences:
    sen_processed = preprocess_text(sen)
    ama_comm.append(sen_processed)
#Building vocabulary using Word2vec
EMBEDDING_DIM = 100
model_wv = gensim.models.Word2Vec( size = EMBEDDING_DIM, window = 5, workers = 4, min_count = 1)
documents = [_text.split() for _text in X[:training_size]] 
model_wv.build_vocab(documents)
words = model_wv.wv.vocab.keys()
vocab_size = len(words)
print("Vocab size", vocab_size)
model_wv.train(documents, total_examples=len(documents), epochs=5)
comment = train_data['comment']
labels = train_data['label']
X_train = X[0:training_size]
y_train = labels[0:training_size]
X_test = X[training_size:]
y_test = labels[training_size:]
ama_comment=test_data1['review']
ama_label = test_data1['label']
#Tokenization
tokenizer = Tokenizer(num_words=10000)
tokenizer.fit_on_texts(X_train)
X_train = tokenizer.texts_to_sequences(X_train)
X_test = tokenizer.texts_to_sequences(X_test)
#Adding 1 because of reserved 0 index
vocab_size = len(tokenizer.word_index) + 1
maxlen = 100
X_train = pad_sequences(X_train, padding='post', maxlen=maxlen)
X_test = pad_sequences(X_test, padding='post', maxlen=maxlen)
ama_comm = tokenizer.texts_to_sequences(ama_comm)
ama_comm = pad_sequences(ama_comm, padding='post', maxlen=maxlen)
#Creating embedding matrix
embedding_matrix = np.zeros((vocab_size, 100))
for word, i in tokenizer.word_index.items():
  if word in model_wv.wv:
    embedding_matrix[i] = model_wv.wv[word]
print(embedding_matrix.shape)
#Bilstm-cnn architecture
filter_sizes = [2,4,5]
num_filters = 100
inp =Input(shape=(maxlen,))
x = Embedding(vocab_size, 100, weights=[embedding_matrix])(inp)
x = Bidirectional(LSTM(128,return_sequences=True))(x)
maxpool_pool = []
for i in range(len(filter_sizes)):
  conv = Conv1D(num_filters, kernel_size=filter_sizes[i],kernel_initializer='he_normal', activation='relu')(x)
  maxpool_pool.append(MaxPool1D(pool_size=maxlen - filter_sizes[i] + 1)(conv))
z = Concatenate(axis=1)(maxpool_pool)
z = Flatten()(z)
z = Dropout(0.5)(z)
out = Dense(100,activation='relu',name='feature_dense')(z)
outp = Dense(1, activation="sigmoid")(out)
model = Model(inputs=inp, outputs=outp)
callbacks = [ tf.keras.callbacks.ReduceLROnPlateau(monitor='val_loss', patience=3, cooldown=0),
              tf.keras.callbacks.EarlyStopping(monitor='val_loss', min_delta=1e-4, patience=3)]

model.compile(loss='binary_crossentropy',optimizer='adam',metrics=['accuracy'])
history = model.fit(X_train, y_train, batch_size=128, epochs=20, verbose=1,validation_split=0.1,callbacks = callbacks)
score = model.evaluate(X_test, y_test, verbose=1)
score = model.evaluate(X_test, y_test, verbose=1) 
score
score = model.evaluate(ama_comm, ama_label, verbose=1) 
score
yhat_probs = model.predict(X_test, verbose=0)
# reduce to 1d array
yhat_probs = yhat_probs[:, 0]
# predict crisp classes for test set
yhat_classes = Crisp_class(yhat_probs)
#Plotting Confusion Matrix
results = confusion_matrix(y_test, yhat_classes) 
print(results)
print("\n")
# Plotting confusion matrix
ax= plt.subplot()
sns.heatmap(results, annot=True, ax = ax, fmt = 'd'); #annot=True to annotate cells
# labels, title and ticks
ax.set_xlabel('Predicted labels');ax.set_ylabel('True labels'); 
ax.set_title('Confusion Matrix of CNN+BiLSTM'); 
ax.xaxis.set_ticklabels(['Non - Sarcastic', 'Sarcastic']); ax.yaxis.set_ticklabels(['Non - Sarcastic', 'Sarcastic']);
# accuracy: (tp + tn) / (p + n)
accuracy = accuracy_score(y_test, yhat_classes)
print('Accuracy: %f' % accuracy)
# precision tp / (tp + fp)
precision = precision_score(y_test, yhat_classes)
print('Precision: %f' % precision)
# recall: tp / (tp + fn)
recall = recall_score(y_test, yhat_classes)
print('Recall: %f' % recall)
# f1: 2 tp / (2 tp + fp + fn)
f1 = f1_score(y_test, yhat_classes)
print('F1 score: %f' % f1)

yhat_probs = model.predict(ama_comm, verbose=0)
# reduce to 1d array
yhat_probs = yhat_probs[:, 0]
# predict crisp classes for test set
yhat_classes = Crisp_class(yhat_probs)
#Plotting Confusion Matrix
results = confusion_matrix(ama_label, yhat_classes) 
print(results)
print("\n")
# Plotting confusion matrix
ax= plt.subplot()
sns.heatmap(results, annot=True, ax = ax, fmt = 'd'); #annot=True to annotate cells
# labels, title and ticks
ax.set_xlabel('Predicted labels');ax.set_ylabel('True labels'); 
ax.set_title('Confusion Matrix of CNN+BiLSTM'); 
ax.xaxis.set_ticklabels(['Non - Sarcastic', 'Sarcastic']); ax.yaxis.set_ticklabels(['Non - Sarcastic', 'Sarcastic']);


# accuracy: (tp + tn) / (p + n)
accuracy = accuracy_score(ama_label, yhat_classes)
print('Accuracy: %f' % accuracy)
# precision tp / (tp + fp)
precision = precision_score(ama_label, yhat_classes)
print('Precision: %f' % precision)
# recall: tp / (tp + fn)
recall = recall_score(ama_label, yhat_classes)
print('Recall: %f' % recall)
# f1: 2 tp / (2 tp + fp + fn)
f1 = f1_score(ama_label, yhat_classes)
print('F1 score: %f' % f1)
