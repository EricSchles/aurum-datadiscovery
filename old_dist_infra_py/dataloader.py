import signal
import time
import sys
import queue
import copy
from collections import OrderedDict

import config as C
import api as API
from inputoutput import serde
from dataanalysis import dataanalysis as da
from modelstore import mongomodelstore as MS
from inputoutput import inputoutput as iod
from conceptgraph import cgraph as cg
from conceptgraph import simrank as sr

# Capturing ctrl+C


def signal_handler(signal, frame):
    print('Finishing pending work...')
    goOn = False
    import time
    time.sleep(3)  # wait 3 secs before shutting down
    sys.exit(0)
signal.signal(signal.SIGINT, signal_handler)
#print('Press Ctrl+C')
#signal.pause()

# All load task types that are supported
loadtask_types = ["CSV"]

# Queue that keeps tasks to process
workqueue = queue.Queue()

# Control variable to keep working
goOn = True


def load_csv_file(filename):
    '''
    Given a CSV file it creates a task for the loader
    '''
    task = ("CSV", filename)
    workqueue.put(task)


def create_work_from_path_csv_files(path):
    '''
    Given a path full of CSV files it creates
    tasks for the loader
    '''
    all_files = iod.get_files_in_dir(path)
    for f in all_files:
        load_csv_file(f)


def process_csv_file(filename):
    '''
    Incorporates the filename to the model
    '''
    # Extract columns from file
    columns = iod.get_columns_from_csv_file(filename)
    concepts = []
    for column in columns.items():
        # Clean columns
        # clean_c is a dict with 1 key
        # c_type is the value of the types
        (clean_c, c_type) = API.clean_column(column)
        values = list(clean_c.values())[0]
        (f_name, c_name) = list(clean_c.keys())[0]
        concepts.append((f_name, c_name))
        # Extract signature
        sig = None
        num_data = []
        text_data = []
        if c_type is 'N':
            # num signature
            method = C.preferred_num_method
            sig = da.get_num_dist(values, method)
            num_data = values
        elif c_type is 'T':
            # text signature
            method = C.preferred_text_method
            sig = da.get_textual_dist(values, method)
            text_data = values
        # Load info to model store
        MS.new_column(f_name,
                      c_name,
                      c_type,
                      sig,
                      num_data,
                      text_data)
        # Add new concepts to graph


def load():
    '''
    Consumes load tasks from queue and process them
    '''
    total_tasks_processed = 0
    # TODO: change to goOn var once this is always living
    while(workqueue.qsize() > 0):
        task = workqueue.get()
        (t_type, resource) = task
        if t_type is "CSV":
            process_csv_file(resource)
        else:
            print("Unrecognized data type for column")
        # Keep count of processed tasks
        aprox_size = workqueue.qsize()
        total_tasks_processed = total_tasks_processed + 1
        print("Processed Tasks: "
              + str(total_tasks_processed) + "/" + str(aprox_size))
        print("Finished processing: " + str(resource))


def build_dict_values(values):
    d = dict()
    for v in values:
        if v not in d:
            d[v] = 0
        d[v] = d[v] + 1
    return d


def compute_overlap(values1, values2, th_overlap, th_cutoff):
    overlap = 0
    non_overlap = 0
    longest = None
    shortest = None
    if len(values1) > len(values2):
        longest = values1
        shortest = values2
    else:
        longest = values2
        shortest = values1

    for k, v in shortest.items():
        #print("is: " + str(k) + " in longest.keys?" + str(longest.keys()))
        if k in longest.keys():
            #overlap = overlap + (v * values1[k]) # cartesian product
            #overlap = overlap + v + values1[k]    # unique values only
            overlap = overlap + 1
        else:
            non_overlap = non_overlap + 1
        #print("ov: " + str(overlap) + " nonov: " + str(non_overlap))
        if overlap > th_overlap:
            #print("ov: "+str(overlap)+" cutoff: "+str(non_overlap))
            return True
        if non_overlap > th_cutoff:
            #print("nov: "+str(non_overlap)+" thcutoff: "+str(th_cutoff))
            return False


def jgraph_from_modelstore(concepts, jgraph):
    '''
    Creates a join graph reading from the store directly
    '''
    tit = len(concepts)
    it = 0
    for pconcept in concepts:
        print(str(it) + "/" + str(tit))
        it = it + 1
        jgraph[pconcept] = []
        pvalues = MS.get_values_of_concept(pconcept)
        pvals = build_dict_values(pvalues)
        for concept in concepts:
            values = MS.get_values_of_concept(concept)
            vals = build_dict_values(values)
            total_size = len(pvalues) + len(values)
            th_overlap = C.join_overlap_th * total_size
            th_cutoff = total_size - th_overlap
            overlap = compute_overlap(pvals, vals, th_overlap, th_cutoff)
            if overlap:
                jgraph[pconcept].append(concept)
    return jgraph


def refine_from_modelstore(concepts, cgraph):
    '''
    This method is an adaptation of api.refine_graph_with_csig
    to work with the store directly
    '''
    # Iterate over all nodes in the graph
    total_concepts = len(concepts)
    it = 0
    for concept in concepts:
        print(str(it) + "/" + str(total_concepts))
        it = it + 1
        cgraph[concept] = []
        sim_cols = API.columns_similar_to_DBCONN(concept)
        cgraph[concept].extend(sim_cols)
    return cgraph


def add_table_neighbors(concepts, cgraph):
    '''
    Add additional edges to the existent graph, those of columns
    that are in the same table
    '''
    for col in concepts:
        (fname1, _) = col
        for col2 in concepts:
            (fname2, _) = col2
            if fname2 is fname1:
                if col2 not in cgraph[col]:
                    cgraph[col].append(col2)
    return cgraph


def build_cgraph_cache():
    # First construct graph
    st = time.time()
    cgraph_cache = OrderedDict()
    concepts = MS.get_all_concepts()
    # figuring out bottleneck...
    #concepts = concepts[:600]
    print("Computing all similarities for graph...")
    cgraph_cache = refine_from_modelstore(concepts, cgraph_cache)
    print("Computing all similarities for graph...DONE")
    et = time.time()
    time_to_build_graph = et - st
    print("Time to build graph: " + str(time_to_build_graph))
    return concepts, cgraph_cache


def build_cgraph(concepts, cgraph_cache):
    print("Deep copying...")
    cgraph = copy.deepcopy(cgraph_cache)
    print("Deep copying...DONE")
    st = time.time()
    print("Refining graph with neighbors...")
    cgraph = add_table_neighbors(concepts, cgraph)
    print("Refining graph with neighbors...DONE")
    et = time.time()
    time_to_neighbors = et - st
    print("Time to add table neighbors: " + str(time_to_neighbors))
    return cgraph


def build_simrank(cgraph):
    # Then run simrank
    st = time.time()
    print("Computing SIMRANK...")
    simrank = sr.simrank(cgraph, C.sr_maxiter, C.sr_eps, C.sr_c)
    #simrank = concepts
    print("Computing SIMRANK...DONE")
    et = time.time()
    time_to_simrank = et - st
    print("Time to simrank: " + str(time_to_simrank))
    return simrank


def build_jgraph(concepts):
    st = time.time()
    jgraph = dict()
    jgraph = jgraph_from_modelstore(concepts, jgraph)
    #for k,v in jgraph.items():
    #    print(str(k)+" -> " + str(len(v)))
    et = time.time()
    time_to_jgraph = et - st
    print("Time to jgraph: " + str(time_to_jgraph))
    return jgraph


def build_graph_and_store(dataset):
    # Build cgraph_cache
    print("Building cgraph_cache...")
    concepts, cgraph_cache = build_cgraph_cache()
    print("Building cgraph_cache...DONE!")
    # Store cgraph_cache
    print("Storing graph (cache)...")
    serde.serialize_cached_graph(cgraph_cache, dataset)
    print("Storing graph (cache)...DONE!")

    # Build cgraph
    print("Building cgraph...")
    cgraph = build_cgraph(concepts, cgraph_cache)
    print("Building cgraph...")
    # Store cgraph
    print("Storing cgraph...")
    serde.serialize_graph(cgraph, dataset)
    print("Storing cgraph...DONE!")

    # Build jgraph
    print("Building jgraph...")
    jgraph = build_jgraph(concepts)
    print("Building jgraph...DONE!")
    # Store jgraph
    print("Storing jgraph...")
    serde.serialize_jgraph(jgraph, dataset)
    print("Storing jgraph...DONE!")

    print("SKIPPING SIMRANK")

    # Build simrank
    #simrank = build_simrank(cgraph)
    # Store simrank
    #print("Storing simrank matrix...")
    #serde.serialize_simrank_matrix(simrank, dataset)
    #print("Storing simrank matrix...DONE!")


def main():
    mode = sys.argv[2]
    dirOrDataset = sys.argv[3]
    arg = sys.argv[4]
    dataset = sys.argv[6]
    print("MODE: " + str(mode))
    print("DATASET: " + str(dataset))
    # Initialize model store
    MS.init(dataset)
    if mode == "ALL" or mode == "LOAD":
        if dirOrDataset == "--dir":
            print("Working on path: " + str(arg))
            create_work_from_path_csv_files(arg)
        load()
        print("FINISHED LOADING DATA TO STORE!")
        if mode == "ALL":
            build_graph_and_store(dataset)
            print("FINISHED MODEL CREATION!!")
    elif mode == "BGRAPH":
        build_graph_and_store(dataset)
        print("FINISHED MODEL CREATION!!")
    else:
        print("Unrecognized mode")
        exit()


if __name__ == "__main__":
    if len(sys.argv) is not 7:
        print("HELP")
        print("--mode <mode> : specifies ALL, LOAD, BGRAPH")
        print("--dir <path> to directory with CSV files")
        print("--dataset <name> of the db")
        print("USAGE")
        exit()
    main()
