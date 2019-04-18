# Copyright 2017 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""TF utils for computing information over given data."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function


# GOOGLE-INITIALIZATION
import tensorflow as tf

from tensorflow.contrib.proto.python.ops import encode_proto_op

_FLOATING_NAN = float('nan')


class VocabOrderingType(object):
  FREQUENCY = 1
  WEIGHTED_FREQUENCY = 2
  WEIGHTED_MUTUAL_INFORMATION = 3


def reduce_batch_vocabulary(x, vocab_ordering_type,
                            weights=None, labels=None):
  """Performs batch-wise reduction of vocabulary.

  Args:
    x: Input `Tensor` to compute a vocabulary over.
    vocab_ordering_type: VocabOrderingType enum.
    weights: (Optional) Weights input `Tensor`.
    labels: (Optional) Binary labels input `Tensor`.


  Returns:
    A tuple of 3 `Tensor`s:
      * unique values
      * total weights sum for unique values when labels and or weights is
        provided, otherwise, None.
      * sum of positive weights for unique values when labels is provided,
        otherwise, None.
  """
  if vocab_ordering_type == VocabOrderingType.FREQUENCY:
    # TODO(b/112916494): Always do batch wise reduction once possible.
    x = tf.reshape(x, [-1])
    return (x, None, None, None)

  if vocab_ordering_type == VocabOrderingType.WEIGHTED_MUTUAL_INFORMATION:
    tf.compat.v1.assert_type(labels, tf.int64)
    x = assert_same_shape(x, labels)
    if weights is None:
      weights = tf.ones_like(labels)
    labels = tf.reshape(labels, [-1])
  x = assert_same_shape(x, weights)
  weights = tf.reshape(weights, [-1])
  x = tf.reshape(x, [-1])
  return _reduce_vocabulary_inputs(x, weights, labels)


def _reduce_vocabulary_inputs(x, weights, labels=None):
  """Reduces vocabulary inputs.

  Args:
    x: Input `Tensor` for vocabulary analyzer.
    weights: Weights `Tensor` for vocabulary analyzer.
    labels: (optional) Binary Labels `Tensor` for vocabulary analyzer.

  Returns:
    A tuple of 3 `Tensor`s:
      * unique values
      * total weights sum for unique values
      * sum of positive weights for unique values when labels is provided,
        otherwise, None.
  """
  unique = tf.unique_with_counts(x, out_idx=tf.int64)

  summed_weights = tf.math.unsorted_segment_sum(weights, unique.idx,
                                                tf.size(input=unique.y))
  if labels is None:
    summed_positive_weights = None
    counts = None
  else:
    less_assert = tf.Assert(
        tf.less_equal(tf.reduce_max(input_tensor=labels), 1), [labels])
    greater_assert = tf.Assert(
        tf.greater_equal(tf.reduce_min(input_tensor=labels), 0), [labels])
    with tf.control_dependencies([less_assert, greater_assert]):
      labels = tf.identity(labels)
    positive_weights = (
        tf.cast(labels, tf.float32) * tf.cast(weights, tf.float32))
    summed_positive_weights = tf.math.unsorted_segment_sum(
        positive_weights, unique.idx, tf.size(input=unique.y))
    counts = unique.count

  return (unique.y, summed_weights, summed_positive_weights, counts)


def assert_same_shape(x, y):
  """Asserts two tensors have the same dynamic and static shape.

  Args:
    x: A `Tensor`.
    y: A `Tensor`

  Returns:
    The element `x`, the result must be used in order to ensure that the dynamic
    check is executed.
  """
  x.shape.assert_is_compatible_with(y.shape)
  assert_eq = tf.compat.v1.assert_equal(tf.shape(input=x), tf.shape(input=y))
  with tf.control_dependencies([assert_eq]):
    return tf.identity(x)


def reduce_batch_count(x, reduce_instance_dims):
  """Counts elements in the given tensor.

  Args:
    x: A `Tensor` or `SparseTensor`.
    reduce_instance_dims: A bool, if True - collapses the batch and instance
        dimensions to arrive at a single scalar output. Otherwise, only
        collapses the batch dimension and outputs a `Tensor` of the same shape
        as the input.

  Returns:
    The element count of `x`. The result is either a scalar if
    reduce_instance_dims is True, otherwise a `Tensor` of the same shape as `x`.
  """
  if isinstance(x, tf.SparseTensor):
    ones_like = tf.SparseTensor(
      indices=x.indices,
      values=tf.ones_like(x.values, tf.int64),
      dense_shape=x.dense_shape
    )
  else:
    ones_like = tf.where(tf.is_nan(tf.cast(x, tf.float32)), tf.zeros_like(x), tf.ones_like(x))

  return reduce_batch_sum(ones_like, reduce_instance_dims)


def reduce_batch_sum(x, reduce_instance_dims):
  """Sum elements in the given tensor.

  Args:
    x: A `Tensor` or `SparseTensor`.
    reduce_instance_dims: A bool, if True - collapses the batch and instance
        dimensions to arrive at a single scalar output. Otherwise, only
        collapses the batch dimension and outputs a `Tensor` of the same shape
        as the input.

  Returns:
    The element sum of `x`. The result is either a scalar if
    reduce_instance_dims is True, otherwise a `Tensor` of the same shape as `x`.
  """
  axis = None if reduce_instance_dims else 0

  if isinstance(x, tf.SparseTensor):
    return tf.sparse_reduce_sum(x, axis=axis)

  # If we have a dense tensor with nans, do not include in the sum
  x = tf.where(tf.is_nan(tf.cast(x, tf.float32)), tf.zeros_like(x), x)
  return tf.reduce_sum(x, axis=axis)


def reduce_batch_count_mean_and_var(x, reduce_instance_dims):
  """Computes element count, mean and var for the given tensor.

  Args:
    x: A `Tensor` or `SparseTensor`.
    reduce_instance_dims: A bool, if True - collapses the batch and instance
        dimensions to arrive at a single scalar output. Otherwise, only
        collapses the batch dimension and outputs a `Tensor` of the same shape
        as the input.

  Returns:
    A 3-tuple containing the `Tensor`s (count, mean, var).
  """
  if isinstance(x, tf.SparseTensor) and reduce_instance_dims:
    x = x.values

  x_count = tf.cast(reduce_batch_count(x, reduce_instance_dims), x.dtype)
  x_mean = reduce_batch_sum(x, reduce_instance_dims) / x_count

  if isinstance(x, tf.SparseTensor):
    # This means reduce_instance_dims=False.
    # TODO(b/112656428): Support SparseTensors with rank other than 2.
    if x.get_shape().ndims != 2:
      raise NotImplementedError(
          'Mean and var only support SparseTensors with rank 2')

    mean_values = tf.gather(x_mean, x.indices[:, 1])
    x_minus_mean = x.values - mean_values
  else:
    x_minus_mean = x - x_mean
  x_variance = reduce_batch_sum(tf.square(x_minus_mean), reduce_instance_dims) / x_count

  return (x_count, x_mean, x_variance)


# Code for serializing and example proto


_DEFAULT_VALUE_BY_DTYPE = {
    tf.string: '',
    tf.float32: 0,
    tf.int64: 0
}


def _encode_proto(values_dict, message_type):
  """A wrapper around encode_proto_op.encode_proto."""
  field_names = []
  sizes = []
  values = []
  for field_name, value in sorted(values_dict.items(), key=lambda x: x[0]):
    if isinstance(value, tf.SparseTensor):
      size = tf.sparse.reduce_sum(
          tf.SparseTensor(value.indices,
                          tf.ones_like(value.values, dtype=tf.int32),
                          value.dense_shape),
          axis=1)
      value = tf.sparse.to_dense(value, _DEFAULT_VALUE_BY_DTYPE[value.dtype])
    else:
      value = tf.reshape(value, [tf.shape(input=value)[0], -1])
      size = tf.fill((tf.shape(input=value)[0],), tf.shape(input=value)[1])
    field_names.append(field_name)
    values.append(value)
    sizes.append(size)

  sizes = tf.stack(sizes, axis=1)
  return encode_proto_op.encode_proto(sizes, values, field_names, message_type)


def _serialize_feature(values):
  """Serialize a Tensor or SparseTensor as `Feature` protos.

  `values` should be a Tensor of rank >=1 or SparseTensor of rank 2.  We will
  refer to the size of the first dimension as batch_size.

  This function encodes each row of the `Tensor` as a list of values (flattening
  the other dimensions) and each row of the `SparseTensor` as a list of values,
  where the indices within each row are ignored and assumed to be 0, 1, ....

  Args:
    values: A `Tensor` or `SparseTensor`.

  Returns:
    A tensor of shape (batch_size,) and type `tf.string` where each element is
        a serialized `Feature` proto.

  Raises:
    ValueError: If the dtype is of `values` is not `tf.string`, `tf.float32`
        or `tf.int64`.
  """
  values = tf.compat.v1.convert_to_tensor_or_sparse_tensor(values)
  if values.dtype == tf.string:
    values_dict = {
        'bytes_list': _encode_proto({'value': values}, 'tensorflow.BytesList')
    }
  elif values.dtype == tf.float32:
    values_dict = {
        'float_list': _encode_proto({'value': values}, 'tensorflow.FloatList')
    }
  elif values.dtype == tf.int64:
    values_dict = {
        'int64_list': _encode_proto({'value': values}, 'tensorflow.Int64List')
    }
  else:
    raise ValueError('Cannot encode values of dtype {}'.format(values.dtype))
  return _encode_proto(values_dict, 'tensorflow.Feature')


def serialize_example(features):
  """Serialized a dict of `Tensor` or `SparseTensor`s as example protos.

  `features` should be a dict where each value is a Tensor of rank >=1 or
  SparseTensor of rank 2.  The sizes of the first dimension of each value should
  be the same, and we refer to this size as batch_size.

  Args:
    features: A dictionary whose values are `Tensor`s or `SparseTensor`s.

  Returns:
    A tensor of shape (batch_size,) and type `tf.string` where each element is
        a serialized `Example` proto.
  """
  features_dict = []
  for key, value in sorted(features.items(), key=lambda x: x[0]):
    serialized_value = _serialize_feature(value)
    features_dict.append(
        _encode_proto({
            'key': tf.fill((tf.shape(input=serialized_value)[0],), key),
            'value': serialized_value,
        }, 'tensorflow.Features.FeatureEntry'))
  features_dict = tf.stack(features_dict, axis=1)
  features = _encode_proto({'feature': features_dict}, 'tensorflow.Features')
  return _encode_proto({'features': features}, 'tensorflow.Example')


def _sparse_minus_reduce_min_and_reduce_max(x):
  """Computes the -min and max of a SparseTensor x.

  It differs from sparse_reduce_max in that sparse_reduce_max returns 0 when all
  elements are missing along axis 0.
  We replace the 0 with NaN when x's dtype is float and dtype.min+1 when it's
  int.

  Args:
    x: A `SparseTensor`.

  Returns:
    Two `Tensors' which are the -min and max.

  Raises:
    TypeError: If the type of `x` is not supported.
  """
  if not isinstance(x, tf.SparseTensor):
    raise TypeError('Expected a SparseTensor, but got %r' % x)
  minus_x = tf.SparseTensor(
      indices=x.indices, values=0 - x.values, dense_shape=x.dense_shape)
  x_count = reduce_batch_count(x, reduce_instance_dims=False)
  batch_has_no_values = tf.equal(x_count, tf.constant(0, dtype=tf.int64))
  x_batch_max = tf.sparse.reduce_max(sp_input=x, axis=0)
  x_batch_minus_min = tf.sparse.reduce_max(sp_input=minus_x, axis=0)

  if x.dtype.is_floating:
    missing_value = tf.constant(_FLOATING_NAN, x.dtype)
  else:
    missing_value = tf.constant(x.dtype.min + 1, x.dtype)

  x_batch_max = tf.where(batch_has_no_values,
                         tf.fill(tf.shape(input=x_batch_max), missing_value),
                         x_batch_max)
  x_batch_minus_min = tf.where(
      batch_has_no_values,
      tf.fill(tf.shape(input=x_batch_minus_min), missing_value),
      x_batch_minus_min)
  return x_batch_minus_min, x_batch_max


def _inf_to_nan(tensor, output_dtype):
  if tensor.dtype.is_floating:
    nan = tf.constant(_FLOATING_NAN, output_dtype)
    return tf.where(tf.math.is_inf(tensor), tensor + nan, tensor)
  return tensor


def reduce_batch_minus_min_and_max(x, reduce_instance_dims):
  """Computes the -min and max of a tensor x.

  Args:
    x: A `tf.Tensor`.
    reduce_instance_dims: A bool indicating whether this should collapse the
      batch and instance dimensions to arrive at a single scalar output, or only
      collapse the batch dimension and outputs a vector of the same shape as the
      input.

  Returns:
    The computed `tf.Tensor`s (batch -min, batch max) pair.
  """
  output_dtype = x.dtype

  if x.dtype == tf.uint8 or x.dtype == tf.uint16:
    x = tf.cast(x, tf.int32)

  elif x.dtype == tf.uint32 or x.dtype == tf.uint64:
    raise TypeError('Tensor type %r is not supported' % x.dtype)

  if reduce_instance_dims:
    if isinstance(x, tf.SparseTensor):
      x = x.values

    x_batch_max = tf.reduce_max(input_tensor=x)
    x_batch_minus_min = tf.reduce_max(input_tensor=tf.zeros_like(x) - x)
    x_batch_minus_min = assert_same_shape(x_batch_minus_min, x_batch_max)
  elif isinstance(x, tf.SparseTensor):
    x_batch_minus_min, x_batch_max = (
        _sparse_minus_reduce_min_and_reduce_max(x))
  else:
    x_batch_max = tf.reduce_max(input_tensor=x, axis=0)
    x_batch_minus_min = tf.reduce_max(input_tensor=0 - x, axis=0)

  # TODO(b/112309021): tf.reduce_max of a tensor of all NaNs produces -inf.
  return (_inf_to_nan(x_batch_minus_min, output_dtype),
          _inf_to_nan(x_batch_max, output_dtype))
