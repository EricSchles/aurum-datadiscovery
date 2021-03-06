import pickle
import os

import config as C


def serialize_signature_collection(tcol_dist, ncol_dist, dataset):
    path = C.serdepath + "/" + str(dataset) + "/"
    if not os.path.exists(path):
        os.makedirs(path)
    path_to_serialize = path + "T_" + C.signcollectionfile
    with open(path_to_serialize, "wb+") as f:
        pickle.dump(tcol_dist, f)
    path_to_serialize = path + "N_" + C.signcollectionfile
    with open(path_to_serialize, "wb+") as f:
        pickle.dump(ncol_dist, f)
    print("Done serialization of signature collections!")


def serialize_cached_graph(obj, dataset):
    path = C.serdepath + "/" + str(dataset) + "/"
    if not os.path.exists(path):
        os.makedirs(path)
    path_to_serialize = path + C.graphcachedfile
    with open(path_to_serialize, "wb+") as f:
        pickle.dump(obj, f)
    print("Done serialization of graph!")


def serialize_graph(obj, dataset):
    path = C.serdepath + "/" + str(dataset) + "/"
    if not os.path.exists(path):
        os.makedirs(path)
    path_to_serialize = path + C.graphfile
    with open(path_to_serialize, "wb+") as f:
        pickle.dump(obj, f)
    print("Done serialization of graph!")


def serialize_jgraph(obj, dataset):
    path = C.serdepath + "/" + str(dataset) + "/"
    if not os.path.exists(path):
        os.makedirs(path)
    path_to_serialize = path + C.jgraphfile
    with open(path_to_serialize, "wb+") as f:
        pickle.dump(obj, f)
    print("Done serialization of jgraph!")


def serialize_dataset_columns(obj, dataset):
    path = C.serdepath + "/" + str(dataset) + "/"
    if not os.path.exists(path):
        os.makedirs(path)
    path_to_serialize = path + C.datasetcolsfile
    with open(path_to_serialize, "wb+") as f:
        pickle.dump(obj, f)
    print("Done serialization of dataset columns!")


def serialize_simrank_matrix(obj, dataset):
    path = C.serdepath + "/" + str(dataset) + "/"
    if not os.path.exists(path):
        os.makedirs(path)
    path_to_serialize = path + C.simrankfile
    with open(path_to_serialize, "wb+") as f:
        pickle.dump(obj, f)
    print("Done serialization of simrank matrix!")


def deserialize_signature_collections(dataset):
    path_to_deserialize = C.serdepath  \
        + "/" + str(dataset) + "/" \
        + "T_" + C.signcollectionfile
    with open(path_to_deserialize, "rb") as f:
        tcol_dist = pickle.load(f)
    path_to_deserialize = C.serdepath \
        + "/" + str(dataset) + "/" \
        + "N_" + C.signcollectionfile
    with open(path_to_deserialize, "rb") as f:
        ncol_dist = pickle.load(f)
    print("Done deserialization of signature collection!")
    return (tcol_dist, ncol_dist)


def deserialize_cached_graph(dataset):
    path_to_deserialize = C.serdepath \
        + "/" + str(dataset) + "/" \
        + C.graphcachedfile
    with open(path_to_deserialize, "rb") as f:
        graph = pickle.load(f)
    print("Done deserialization of cgraph_cache!")
    return graph


def deserialize_graph(dataset):
    path_to_deserialize = C.serdepath \
        + "/" + str(dataset) + "/" \
        + C.graphfile
    with open(path_to_deserialize, "rb") as f:
        graph = pickle.load(f)
    print("Done deserialization of cgraph!")
    return graph


def deserialize_jgraph(dataset):
    path_to_deserialize = C.serdepath \
        + "/" + str(dataset) + "/" \
        + C.jgraphfile
    with open(path_to_deserialize, "rb") as f:
        graph = pickle.load(f)
    print("Done deserialization of jgraph!")
    return graph


def deserialize_dataset_columns(dataset):
    path_to_deserialize = C.serdepath \
        + "/" + str(dataset) + "/" \
        + C.datasetcolsfile
    with open(path_to_deserialize, "rb") as f:
        dcols = pickle.load(f)
    print("Done deserialization of dataset columns!")
    return dcols


def deserialize_simrank_matrix(dataset):
    path_to_deserialize = C.serdepath \
        + "/" + str(dataset) + "/" \
        + C.simrankfile
    with open(path_to_deserialize, "rb") as f:
        dcols = pickle.load(f)
    print("Done deserialization of simrank matrix!")
    return dcols

if __name__ == "__main__":
    print("SERDE module")
