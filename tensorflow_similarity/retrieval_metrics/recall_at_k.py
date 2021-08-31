import tensorflow as tf

from .retrieval_metric import RetrievalMetric
from tensorflow_similarity.types import FloatTensor, IntTensor, BoolTensor


class RecallAtK(RetrievalMetric):
    r"""The metric learning version of Recall@K.

    A query is counted as a positive when ANY lookup in top K match the query
    class, 0 otherwise.

    Attributes:
        name: Name associated with the metric object, e.g., recall@5

        canonical_name: The canonical name associated with metric,
        e.g., recall@K

        k: The number of nearest neighbors over which the metric is computed.

        distance_threshold: The max distance below which a nearest neighbor is
        considered a valid match.

        average: {'micro'} Determines the type of averaging performed over the
        queries.

            'micro': Calculates metrics globally over all queries.

            'macro': Calculates metrics for each label and takes the unweighted
                     mean.
    """
    def __init__(self,
                 name: str = 'recall',
                 k: int = 1,
                 **kwargs) -> None:
        if 'canonical_name' not in kwargs:
            kwargs['canonical_name'] = 'recall@k'

        super().__init__(name=name, k=k, **kwargs)

    def compute(self,
                *,
                query_labels: IntTensor,
                match_mask: BoolTensor,
                **kwargs) -> FloatTensor:
        """Compute the metric

        Args:
            query_labels: A 1D tensor of the labels associated with the
            embedding queries.

            match_mask: A 2D mask where a 1 indicates a match between the
            jth query and the kth neighbor and a 0 indicates a mismatch.

            **kwargs: Additional compute args.

        Returns:
            metric results.
        """
        k_slice = match_mask[:, :self.k]
        match_indicator = tf.math.reduce_any(k_slice, axis=1)
        match_indicator = tf.cast(match_indicator, dtype='float')

        if self.average == 'micro':
            recall_at_k = tf.math.reduce_mean(match_indicator)
        elif self.average == 'macro':
            per_class_metrics = 0
            class_labels = tf.unique(query_labels)[0]
            # TODO(ovallis): potential slowness.
            for label in class_labels:
                idxs = tf.where(query_labels == label)
                c_slice = tf.gather(match_indicator, indices=idxs)
                per_class_metrics += tf.math.reduce_mean(c_slice)
            recall_at_k = tf.math.divide(per_class_metrics, len(class_labels))
        else:
            raise ValueError(f'{self.average} is not a supported average '
                             'option')
        result: FloatTensor = recall_at_k
        return result
