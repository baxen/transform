<div itemscope itemtype="http://developers.google.com/ReferenceObject">
<meta itemprop="name" content="tft.vocabulary" />
<meta itemprop="path" content="Stable" />
</div>

# tft.vocabulary

``` python
tft.vocabulary(
    x,
    top_k=None,
    frequency_threshold=None,
    vocab_filename=None,
    store_frequency=False,
    weights=None,
    labels=None,
    use_adjusted_mutual_info=False,
    min_diff_from_avg=0.0,
    coverage_top_k=None,
    coverage_frequency_threshold=None,
    key_fn=None,
    fingerprint_shuffle=False,
    name=None
)
```

Computes the unique values of a `Tensor` over the whole dataset.

Computes The unique values taken by `x`, which can be a `Tensor` or
`SparseTensor` of any size.  The unique values will be aggregated over all
dimensions of `x` and all instances.

In case one of the tokens contains the '\n' or '\r' characters or is empty it
will be discarded since we are currently writing the vocabularies as text
files. This behavior will likely be fixed/improved in the future.

If an integer `Tensor` is provided, its semantic type should be categorical
not a continuous/numeric, since computing a vocabulary over a continuous
feature is not appropriate.

The unique values are sorted by decreasing frequency and then reverse
lexicographical order (e.g. [('a', 5), ('c', 3), ('b', 3)]).

For large datasets it is highly recommended to either set frequency_threshold
or top_k to control the size of the output, and also the run time of this
operation.

When labels are provided, we filter the vocabulary based on how correlated the
unique value is with a positive label (Mutual Information).


WARNING: The following is experimental and is still being actively worked on.

Supply `key_fn` if you would like to generate a vocabulary with coverage over
specific keys.

A "coverage vocabulary" is the union of two vocabulary "arms". The "standard
arm" of the vocabulary is equivalent to the one generated by the same function
call with no coverage arguments. Adding coverage only appends additional
entries to the end of the standard vocabulary.

The "coverage arm" of the vocabulary is determined by taking the
`coverage_top_k` most frequent unique terms per key. A term's key is obtained
by applying `key_fn` to the term. Use `coverage_frequency_threshold` to lower
bound the frequency of entries in the coverage arm of the vocabulary.

Note this is currently implemented for the case where the key is contained
within each vocabulary entry (b/117796748).

#### Args:

* <b>`x`</b>: A categorical/discrete input `Tensor` or `SparseTensor` with dtype
    tf.string or tf.int[8|16|32|64].
* <b>`top_k`</b>: Limit the generated vocabulary to the first `top_k` elements. If set
    to None, the full vocabulary is generated.
* <b>`frequency_threshold`</b>: Limit the generated vocabulary only to elements whose
    absolute frequency is >= to the supplied threshold. If set to None, the
    full vocabulary is generated.  Absolute frequency means the number of
    occurences of the element in the dataset, as opposed to the proportion of
    instances that contain that element.
* <b>`vocab_filename`</b>: The file name for the vocabulary file. If none, the
    "uniques" scope name in the context of this graph will be used as the file
    name. If not None, should be unique within a given preprocessing function.
    NOTE To make your pipelines resilient to implementation details please
    set `vocab_filename` when you are using the vocab_filename on a downstream
    component.
* <b>`store_frequency`</b>: If True, frequency of the words is stored in the
    vocabulary file. In the case labels are provided, the mutual
    information is stored in the file instead. Each line in the file
    will be of the form 'frequency word'.
* <b>`weights`</b>: (Optional) Weights `Tensor` for the vocabulary. It must have the
    same shape as x.
* <b>`labels`</b>: (Optional) Labels `Tensor` for the vocabulary. It must have dtype
    int64, have values 0 or 1, and have the same shape as x.
* <b>`use_adjusted_mutual_info`</b>: If true, use adjusted mutual information.
* <b>`min_diff_from_avg`</b>: Mutual information of a feature will be adjusted to zero
    whenever the difference between count of the feature with any label and
    its expected count is lower than min_diff_from_average.
* <b>`coverage_top_k`</b>: (Optional), (Experimental) The minimum number of elements
    per key to be included in the vocabulary.
* <b>`coverage_frequency_threshold`</b>: (Optional), (Experimental) Limit the coverage
    arm of the vocabulary only to elements whose absolute frequency is >= this
    threshold for a given key.
* <b>`key_fn`</b>: (Optional), (Experimental) A fn that takes in a single entry of `x`
    and returns the corresponding key for coverage calculation. If this is
    `None`, no coverage arm is added to the vocabulary.
* <b>`fingerprint_shuffle`</b>: (Optional), (Experimental) Whether to sort the
    vocabularies by fingerprint instead of counts. This is useful for load
    balancing on the training parameter servers. Shuffle only happens while
    writing the files, so all the filters above (top_k, frequency_threshold,
    etc) will still take effect.
* <b>`name`</b>: (Optional) A name for this operation.


#### Returns:

The path name for the vocabulary file containing the unique values of `x`.


#### Raises:

* <b>`ValueError`</b>: If `top_k` or `frequency_threshold` is negative.
    If `coverage_top_k` or `coverage_frequency_threshold` is negative.
    If either `coverage_top_k` or `coverage_frequency_threshold` is specified
      and `key_fn` is not.
    If `key_fn` is specified and neither `coverage_top_k`, nor