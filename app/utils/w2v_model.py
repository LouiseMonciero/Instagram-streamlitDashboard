import json
import pandas as pd
import numpy as np
import re
import matplotlib.pyplot as plt
from sklearn.cluster import KMeans
from collections import Counter

# Lazy loading de gensim - ne sera chargé que si nécessaire
_wv = None

def _load_word2vec_model():
    """Charge le modèle word2vec uniquement quand nécessaire"""
    global _wv
    if _wv is None:
        import gensim.downloader as api
        _wv = api.load('word2vec-google-news-300')
    return _wv

def generate_clusters(recommended_topics, n_clusters=10):
    # Charge le modèle seulement quand cette fonction est appelée
    wv = _load_word2vec_model()
    
    def preprocess_topic(topic):
        # Lowercase
        topic = topic.lower()
        topic = re.sub(r'[^a-z\s]', '', topic)  # Remove anything that's not a letter or space
        topic = topic.split(' ')
        return topic

    preprocessed_topics = [preprocess_topic(topic) for topic in recommended_topics]

    def get_average_vector(topic, wv):
        # If topic is already a list, use it directly
        if isinstance(topic, str):
            words = topic.split()
        else:
            words = topic
        
        word_vectors = []
        for word in words:
            try:
                word_vectors.append(wv[word])
            except KeyError:
                continue
        if word_vectors:
            return np.mean(word_vectors, axis=0)
        else:
            return np.zeros(wv.vector_size)

    topic_vectors = { " ".join(topic) if isinstance(topic, list) else topic: get_average_vector(topic, wv) for topic in preprocessed_topics }

    # Get the topic vectors as a list
    vectors = list(topic_vectors.values())

    # Apply KMeans clustering
    kmeans = KMeans(n_clusters=n_clusters, random_state=0).fit(vectors)

    # Get the cluster labels for each topic
    labels = kmeans.labels_

    # Map each topic to its cluster
    clusters = {i: [] for i in range(n_clusters)}
    for i, label in enumerate(labels):
        clusters[label].append(recommended_topics[i])

    def create_cluster_name(cluster_topics):

        # Split topics into words and count frequency of each word
        all_words = []
        for topic in cluster_topics:
            all_words.extend(topic.split())
        
        # Count word frequencies
        word_counts = Counter(all_words)
        
        # Get the 3 most common words as the cluster name
        most_common_words = [word for word, _ in word_counts.most_common(3)]

        # Remove '&' from the words.
        most_common_words = [x for x in most_common_words if x != '&']
        
        # Join the words to form a cluster name
        cluster_name = " & ".join(most_common_words)
        
        return cluster_name

    cluster_data = []

    for cluster_id, cluster_topics in clusters.items():
        cluster_name = create_cluster_name(cluster_topics)
        cluster_weight = len(cluster_topics)
        cluster_data.append({"cluster_name": cluster_name, "weights": cluster_weight})

    return (cluster_data, clusters)