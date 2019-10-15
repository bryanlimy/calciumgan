import os
import io
import pickle
import numpy as np
import tensorflow as tf

import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt


def get_dataset(hparams, summary):
  if not os.path.exists(hparams.input):
    print('input pickle {} cannot be found'.format(hparams.input))
    exit()

  with open(hparams.input, 'rb') as file:
    segments = pickle.load(file)

  np.random.shuffle(segments)

  # plot first 5 activities
  summary.plot('real_activities', segments[:5], training=False)

  hparams.sequence_length = segments.shape[-1]

  # 70% training data
  train_size = int(len(segments) * 0.7)

  # train set
  train_ds = tf.data.Dataset.from_tensor_slices(segments[:train_size])
  train_ds = train_ds.cache()
  train_ds = train_ds.shuffle(buffer_size=512)
  train_ds = train_ds.batch(hparams.batch_size)
  train_ds = train_ds.prefetch(tf.data.experimental.AUTOTUNE)

  # validation set
  validation_ds = tf.data.Dataset.from_tensor_slices(segments[train_size:])
  validation_ds = validation_ds.batch(hparams.batch_size)

  hparams.steps_per_epoch = int(np.ceil(train_size / hparams.batch_size))

  return train_ds, validation_ds


class Summary(object):
  """ 
  Log tf.Summary to output_dir during training and output_dir/eval during 
  evaluation
  """

  def __init__(self, hparams):
    self._hparams = hparams
    self.train_writer = tf.summary.create_file_writer(hparams.output_dir)
    self.val_writer = tf.summary.create_file_writer(
        os.path.join(hparams.output_dir, 'validation'))
    tf.summary.trace_on(graph=True, profiler=False)

  def _get_writer(self, training):
    return self.train_writer if training else self.val_writer

  def scalar(self, tag, value, training=True):
    writer = self._get_writer(training)
    with writer.as_default():
      tf.summary.scalar(tag, value, step=self._hparams.global_step)

  def histogram(self, tag, values, training=True):
    writer = self._get_writer(training)
    with writer.as_default():
      tf.summary.histogram(tag, values, step=self._hparams.global_step)

  def _plot_to_image(self, figure):
    """
    Converts the matplotlib plot specified by 'figure' to a PNG image and
    returns it. The supplied figure is closed and inaccessible after this call.
    """
    buf = io.BytesIO()
    plt.savefig(buf, dpi=150, format='png')
    plt.close(figure)
    buf.seek(0)
    image = tf.image.decode_png(buf.getvalue(), channels=4)
    return image

  def plot(self, tag, values, training=True):
    writer = self._get_writer(training)

    images = []
    for i in range(values.shape[0]):
      value = values[i]
      figure = plt.figure()
      plt.plot(value)
      plt.xlabel('Time (ms)')
      plt.ylabel('Activity')
      image = self._plot_to_image(figure)
      images.append(image)

    images = tf.stack(images)

    with writer.as_default():
      tf.summary.image(
          tag,
          data=images,
          step=self._hparams.global_step,
          max_outputs=values.shape[0])

  def graph(self):
    writer = self._get_writer(training=True)
    with writer.as_default():
      tf.summary.trace_export(name='models', step=0)
