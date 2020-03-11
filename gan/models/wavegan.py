from .registry import register

import numpy as np
import tensorflow as tf
from tensorflow.keras import layers

from .utils import activation_fn, calculate_input_config, Conv1DTranspose


@register('wavegan')
def get_wavegan(hparams):
  return generator(hparams), discriminator(hparams)


def generator(hparams, filters=32, kernel_size=25, strides=2, padding='same'):
  inputs = tf.keras.Input(shape=hparams.noise_shape, name='inputs')

  shape, num_units = calculate_input_config(
      output=hparams.sequence_length,
      noise_dim=hparams.noise_dim,
      num_convolution=5,
      kernel_size=kernel_size,
      strides=strides,
      padding=padding)

  outputs = layers.Dense(num_units)(inputs)
  outputs = activation_fn(hparams.activation)(outputs)
  outputs = layers.Reshape(shape)(outputs)

  # Layer 1
  outputs = Conv1DTranspose(
      filters * 5, kernel_size, strides, padding=padding)(outputs)
  if hparams.batch_norm:
    outputs = layers.BatchNormalization()(outputs)
  outputs = activation_fn(hparams.activation)(outputs)

  # Layer 2
  outputs = Conv1DTranspose(
      filters * 4, kernel_size, strides, padding=padding)(outputs)
  if hparams.batch_norm:
    outputs = layers.BatchNormalization()(outputs)
  outputs = activation_fn(hparams.activation)(outputs)

  # Layer 3
  outputs = Conv1DTranspose(
      filters * 3, kernel_size, strides, padding=padding)(outputs)
  if hparams.batch_norm:
    outputs = layers.BatchNormalization()(outputs)
  outputs = activation_fn(hparams.activation)(outputs)

  # Layer 4
  outputs = Conv1DTranspose(
      filters * 2, kernel_size, strides, padding=padding)(outputs)
  if hparams.batch_norm:
    outputs = layers.BatchNormalization()(outputs)
  outputs = activation_fn(hparams.activation)(outputs)

  # Layer 5
  outputs = Conv1DTranspose(
      hparams.num_neurons, kernel_size, strides, padding=padding)(outputs)
  if hparams.batch_norm:
    outputs = layers.BatchNormalization()(outputs)
  outputs = activation_fn(hparams.activation)(outputs)

  outputs = layers.Dense(hparams.num_neurons)(outputs)

  if hparams.normalize:
    outputs = activation_fn('sigmoid', dtype=tf.float32)(outputs)
  else:
    outputs = activation_fn('linear', dtype=tf.float32)(outputs)

  return tf.keras.Model(inputs=inputs, outputs=outputs, name='generator')


class PhaseShuffle(layers.Layer):
  ''' Phase Shuffle introduced in the WaveGAN paper so that the discriminator 
  are less sensitive toward periodic patterns which occurs quite frequently in
  signal data '''

  def __init__(self, input_shape, shuffle=0, mode='reflect'):
    super().__init__()
    self.shape = input_shape
    self.shuffle = shuffle
    self.mode = mode

  def call(self, inputs):
    if self.shuffle == 0:
      return inputs

    phase = tf.random.uniform([],
                              minval=-self.shuffle,
                              maxval=self.shuffle + 1,
                              dtype=tf.int32)
    left_pad = tf.maximum(phase, 0)
    right_pad = tf.maximum(-phase, 0)

    outputs = tf.pad(
        inputs,
        paddings=[[0, 0], [left_pad, right_pad], [0, 0]],
        mode=self.mode)

    outputs = outputs[:, right_pad:right_pad + self.shape[1]]
    return tf.ensure_shape(outputs, shape=self.shape)


def discriminator(hparams,
                  filters=32,
                  kernel_size=25,
                  strides=2,
                  padding='same'):
  inputs = tf.keras.Input(hparams.signal_shape, name='signals')

  # Layer 1
  outputs = layers.Conv1D(
      filters, kernel_size=kernel_size, strides=strides,
      padding=padding)(inputs)
  outputs = activation_fn(hparams.activation)(outputs)
  outputs = PhaseShuffle(outputs.shape, shuffle=2)(outputs)

  # Layer 2
  outputs = layers.Conv1D(
      filters * 2, kernel_size=kernel_size, strides=strides,
      padding=padding)(outputs)
  outputs = activation_fn(hparams.activation)(outputs)
  outputs = PhaseShuffle(outputs.shape, shuffle=2)(outputs)

  # Layer 3
  outputs = layers.Conv1D(
      filters * 3, kernel_size=kernel_size, strides=strides,
      padding=padding)(outputs)
  outputs = activation_fn(hparams.activation)(outputs)
  outputs = PhaseShuffle(outputs.shape, shuffle=2)(outputs)

  # Layer 4
  outputs = layers.Conv1D(
      filters * 4, kernel_size=kernel_size, strides=strides,
      padding=padding)(outputs)
  outputs = activation_fn(hparams.activation)(outputs)
  outputs = PhaseShuffle(outputs.shape, shuffle=2)(outputs)

  # Layer 5
  outputs = layers.Conv1D(
      filters * 5, kernel_size=kernel_size, strides=strides,
      padding=padding)(outputs)
  outputs = activation_fn(hparams.activation)(outputs)

  outputs = layers.Flatten()(outputs)
  outputs = layers.Dense(1)(outputs)
  outputs = activation_fn('linear', dtype=tf.float32)(outputs)

  return tf.keras.Model(inputs=inputs, outputs=outputs, name='discriminator')