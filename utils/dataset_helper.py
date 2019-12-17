import os
import pickle
import numpy as np
from math import ceil
import tensorflow as tf


def get_fashion_mnist(hparams):
  (x_train, _), (x_test, _) = tf.keras.datasets.fashion_mnist.load_data()

  def preprocess(images):
    images = np.reshape(images, newshape=(images.shape[0], 28, 28, 1))
    return images.astype('float32') / 255.0

  x_train = preprocess(x_train)
  x_test = preprocess(x_test)

  hparams.train_size = len(x_train)
  hparams.eval_size = len(x_test)

  train_ds = tf.data.Dataset.from_tensor_slices(x_train)
  train_ds = train_ds.shuffle(buffer_size=2048)
  train_ds = train_ds.batch(hparams.batch_size)
  train_ds = train_ds.prefetch(tf.data.experimental.AUTOTUNE)

  eval_ds = tf.data.Dataset.from_tensor_slices(x_test)
  eval_ds = eval_ds.batch(hparams.batch_size)

  return train_ds, eval_ds


def get_dataset_info(hparams):
  """ Get dataset information """
  with open(os.path.join(hparams.input, 'info.pkl'), 'rb') as file:
    info = pickle.load(file)
  hparams.train_size = info['train_size']
  hparams.validation_size = info['validation_size']
  hparams.signal_shape = info['signal_shape']
  hparams.spike_shape = info['spike_shape']
  hparams.num_train_shards = info['num_train_shards']
  hparams.num_validation_shards = info['num_validation_shards']
  hparams.buffer_size = info['num_per_shard']
  hparams.normalize = info['normalize']


def get_calcium_signals(hparams):
  if not os.path.exists(hparams.input):
    print('input directory {} cannot be found'.format(hparams.input))
    exit()

  get_dataset_info(hparams)

  features_description = {
      'signal': tf.io.FixedLenFeature([], tf.string),
      'spike': tf.io.FixedLenFeature([], tf.string)
  }

  def _parse_example(example):
    parsed = tf.io.parse_single_example(example, features_description)
    signal = tf.io.decode_raw(parsed['signal'], out_type=tf.float32)
    signal = tf.reshape(signal, shape=hparams.signal_shape)
    spike = tf.io.decode_raw(parsed['spike'], out_type=tf.float32)
    spike = tf.reshape(spike, shape=hparams.spike_shape)
    return signal, spike

  train_files = tf.data.Dataset.list_files(
      os.path.join(hparams.input, 'train-*.record'))
  train_ds = train_files.interleave(tf.data.TFRecordDataset, cycle_length=4)
  train_ds = train_ds.map(
      _parse_example, num_parallel_calls=tf.data.experimental.AUTOTUNE)
  train_ds = train_ds.shuffle(buffer_size=hparams.buffer_size)
  train_ds = train_ds.batch(hparams.batch_size)
  train_ds = train_ds.prefetch(tf.data.experimental.AUTOTUNE)

  validation_files = tf.data.Dataset.list_files(
      os.path.join(hparams.input, 'validation-*.record'))
  validation_ds = validation_files.interleave(
      tf.data.TFRecordDataset, cycle_length=4)
  validation_ds = validation_ds.map(
      _parse_example, num_parallel_calls=tf.data.experimental.AUTOTUNE)
  validation_ds = validation_ds.batch(hparams.batch_size)

  return train_ds, validation_ds


def get_dataset(hparams):
  if hparams.input == 'fashion_mnist':
    train_ds, validation_ds = get_fashion_mnist(hparams)
    hparams.generator_input_shape = (hparams.noise_dim,)
  else:
    train_ds, validation_ds = get_calcium_signals(hparams)
    hparams.num_neurons = hparams.signal_shape[0]
    hparams.generator_input_shape = (hparams.num_neurons, hparams.noise_dim)

  hparams.steps_per_epoch = ceil(hparams.train_size / hparams.batch_size)

  return train_ds, validation_ds