from abc import ABC, abstractmethod
from typing import Union, List
import tensorflow as tf
from .types import FloatTensor


class Distance(ABC):
    """
    Note: don't forget to add your distance to the DISTANCES list
    and add alias names in it.

    """
    def __init__(self, name: str, aliases: List[str] = []):
        self.name = name
        self.aliases = aliases

    @abstractmethod
    def call(self, embeddings: FloatTensor) -> FloatTensor:
        """Compute pairwise distances for a given batch.

        Args:
            embeddings: Embeddings to compute the pairwise one.

        Returns:
            FloatTensor: Pairwise distance tensor.
        """

    def __call__(self, embeddings: FloatTensor):
        return self.call(embeddings)

    def __str__(self) -> str:
        return self.name

    def get_config(self):
        return {}


@tf.keras.utils.register_keras_serializable(package="Similarity")
class InnerProductSimilarity(Distance):
    """Compute the pairwise inner product between embeddings.

    The [Inner product](https://en.wikipedia.org/wiki/Inner_product_space) is
    a measure of similarity where the more similar vectors have the largest
    values.

    NOTE! This is not a distance and is likely not what you want to use with
    the built in losses. At the very least this will flip the sign on the
    margin in many of the losses. This is likely meant to be used with custom
    loss functions that expect a similarity instead of a distance.
    """
    def __init__(self):
        "Init Inner product similarity"
        super().__init__('inner_product', ['ip'])

    @tf.function
    def call(self, embeddings: FloatTensor) -> FloatTensor:
        """Compute pairwise similarities for a given batch of embeddings.

        Args:
            embeddings: Embeddings to compute the pairwise one.

        Returns:
            FloatTensor: Pairwise distance tensor.
        """

        tensor = tf.linalg.matmul(embeddings, embeddings, transpose_b=True)
        sims: FloatTensor = tf.reduce_sum(tensor, axis=1, keepdims=True)
        return sims


@tf.keras.utils.register_keras_serializable(package="Similarity")
class CosineDistance(Distance):
    """Compute pairwise cosine distances between embeddings.

    The [Cosine Distance](https://en.wikipedia.org/wiki/Cosine_similarity) is
    an angular distance that varies from 0 (similar) to 1 (dissimilar).
    """
    def __init__(self):
        "Init Cosine distance"
        super().__init__('cosine')

    @tf.function
    def call(self, embeddings: FloatTensor) -> FloatTensor:
        """Compute pairwise distances for a given batch of embeddings.

        Args:
            embeddings: Embeddings to compute the pairwise one.

        Returns:
            FloatTensor: Pairwise distance tensor.
        """
        distances = 1 - tf.linalg.matmul(
                embeddings, embeddings, transpose_b=True)
        distances = tf.math.maximum(distances, 0.0)
        return distances


@tf.keras.utils.register_keras_serializable(package="Similarity")
class EuclideanDistance(Distance):
    """Compute pairwise euclidean distances between embeddings.

    The [Euclidean Distance](https://en.wikipedia.org/wiki/Euclidean_distance)
    is the standard distance to measure the line segment between two embeddings
    in the Cartesian point. The larger the distance the more dissimilar
    the embeddings are.

    **Alias**: L2 Norm, Pythagorean
    """
    def __init__(self):
        "Init Euclidean distance"
        super().__init__('euclidean', ['l2', 'pythagorean'])

    @tf.function
    def call(self, embeddings: FloatTensor) -> FloatTensor:
        """Compute pairwise distances for a given batch of embeddings.

        Args:
            embeddings: Embeddings to compute the pairwise one.

        Returns:
            FloatTensor: Pairwise distance tensor.
        """
        squared_norm = tf.math.square(embeddings)
        squared_norm = tf.math.reduce_sum(squared_norm, axis=1, keepdims=True)

        distances: FloatTensor = 2.0 * tf.linalg.matmul(
            embeddings, embeddings, transpose_b=True)
        distances = squared_norm - distances + tf.transpose(squared_norm)

        # Avoid NaN and inf gradients when back propagating through the sqrt.
        # values smaller than 1e-18 produce inf for the gradient, and 0.0
        # produces NaN. All values smaller than 1e-13 should produce a gradient
        # of 1.0.
        dist_mask = tf.math.greater_equal(distances, 1e-18)
        distances = tf.math.maximum(distances, 1e-18)
        distances = tf.math.sqrt(distances) * tf.cast(dist_mask, tf.float32)

        return distances


@tf.keras.utils.register_keras_serializable(package="Similarity")
class SquaredEuclideanDistance(Distance):
    """Compute pairwise squared Euclidean distance.

    The [Sequared Euclidean Distance](https://en.wikipedia.org/wiki/Euclidean_distance#Squared_Euclidean_distance) is
    a distance that varies from 0 (similar) to infinity (dissimilar).
    """
    def __init__(self):
        super().__init__('squared_euclidean', ['sql2', 'sqeuclidean'])

    @tf.function
    def call(self, embeddings: FloatTensor) -> FloatTensor:
        """Compute pairwise distances for a given batch of embeddings.

        Args:
            embeddings: Embeddings to compute the pairwise one.

        Returns:
            FloatTensor: Pairwise distance tensor.
        """
        squared_norm = tf.math.square(embeddings)
        squared_norm = tf.math.reduce_sum(squared_norm, axis=1, keepdims=True)

        distances: FloatTensor = 2.0 * tf.linalg.matmul(
            embeddings, embeddings, transpose_b=True)
        distances = squared_norm - distances + tf.transpose(squared_norm)
        distances = tf.math.maximum(distances, 0.0)

        return distances


@tf.keras.utils.register_keras_serializable(package="Similarity")
class ManhattanDistance(Distance):
    """Compute pairwise Manhattan distances between embeddings.

    The [Manhattan Distance](https://en.wikipedia.org/wiki/Euclidean_distance)
    is the sum of the lengths of the projections of the line segment between
    two embeddings onto the Cartesian axes. The larger the distance the more
    dissimilar the embeddings are.
    """
    def __init__(self):
        "Init Manhattan distance"
        super().__init__('manhattan', ['l1', 'taxicab'])

    @tf.function
    def call(self, embeddings: FloatTensor) -> FloatTensor:
        """Compute pairwise distances for a given batch of embeddings.

        Args:
            embeddings: Embeddings to compute the pairwise one.

        Returns:
            FloatTensor: Pairwise distance tensor.
        """
        x_rs = tf.reshape(embeddings, shape=[tf.shape(embeddings)[0], -1])
        deltas = tf.expand_dims(x_rs, axis=1) - tf.expand_dims(x_rs, axis=0)
        distances: FloatTensor = tf.norm(deltas, 1, axis=2)
        return distances


# List of implemented distances
DISTANCES = [
    InnerProductSimilarity(),
    EuclideanDistance(),
    SquaredEuclideanDistance(),
    ManhattanDistance(),
    CosineDistance()
]


def distance_canonicalizer(user_distance: Union[Distance, str]) -> Distance:
    """Normalize user requested distance to its matching Distance object.

    Args:
        user_distance: Requested distance either by name or by object

    Returns:
        Distance: Requested object name.
    """

    # just return Distance object
    if isinstance(user_distance, Distance):
        # user supplied distance function
        return user_distance

    mapping = {}
    name2fn = {}
    for distance in DISTANCES:
        # self reference
        mapping[distance.name] = distance.name
        name2fn[distance.name] = distance
        # aliasing
        for alias in distance.aliases:
            mapping[alias] = distance.name

    if isinstance(user_distance, str):
        user_distance = user_distance.lower().strip()
        if user_distance in mapping:
            user_distance = mapping[user_distance]
        else:
            raise ValueError('Metric not supported by the framework')

        return name2fn[user_distance]

    raise ValueError('Unknown distance: must either be a MetricDistance\
                     or a known distance function')
