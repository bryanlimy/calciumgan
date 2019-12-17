import h5py
import numpy as np
from time import sleep


def open_h5(filename, *args, **kwargs):
  while True:
    try:
      file = h5py.File(filename, *args, **kwargs)
      break
    except OSError:
      sleep(1)
  return file


def append_h5(ds, value):
  """ append value to a H5 dataset """
  if type(value) != np.ndarray:
    value = np.array(value, dtype=np.float32)
  ds.resize((ds.shape[0] + value.shape[0]), axis=0)
  ds[-value.shape[0]:] = value


def create_or_append_h5(file, name, value):
  """ create or append value to a H5 dataset """
  if name in file:
    append_h5(file[name], value)
  else:
    file.create_dataset(
        name,
        dtype=np.float32,
        data=value,
        chunks=True,
        maxshape=(None, value.shape[1], value.shape[2]))