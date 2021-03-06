import sys
import os
import time
from os import listdir
from os.path import isfile, join
import editdistance
from collections import OrderedDict
import operator

import config as C
from inputoutput import inputoutput as iod
from inputoutput import serde
from dataanalysis import dataanalysis as da
from dataanalysis import jointsignatureanalysis as jsa
from conceptgraph import cgraph as cg
from conceptgraph import simrank as sr
from modelstore import mongomodelstore as MS

cgraph = OrderedDict()
cgraph_cache = None
jgraph = OrderedDict()
simrank = None
dataset_columns = dict()
ncol_dist = dict()
tcol_dist = dict()

now = lambda: int(round(time.time()) * 1000)


class DB_adapted_API():
    '''
    This class is used to wrap up functions
    that need special treatment
    '''

    '''
    Primitives 
    '''

    def peek(self, concept, num):
        '''
        Peek 10 values of the column
        '''
        values = MS.peek_values(concept, num)
        return values

    def search_keyword(self, keyword):
        '''
        Returns [(dataset,column)] that contain the
        given keyword
        '''
        columns = MS.search_keyword(keyword)
        return columns

    def columns_like(self, concept):
        '''
        Returns all columns similar to the provided
        '''
        columns = neighbors_of(concept, cgraph_cache)
        return columns

    def columns_in_context_with(self, concept):
        '''
        Structural similarity
        '''
        columns = give_structural_sim_of(concept)
        return columns

    def columns_joinable_with(self, concept):
        '''
        Inclusion dependency
        '''
        columns = neighbors_of(concept, jgraph)
        return columns

    def search_schema(self, keyword, topk, includescore):
        '''
        Return list of tables-columns with similar column name
        '''
        res = attr_similar_to(keyword, topk, includescore)
        return res

    '''
    Functions: Functions use primitives for more refined output
    '''

    def tables_with_schema(self, list_keywords, topk):
        '''
        Return list of tables that contain the required schema
        '''
        all_res = []
        # First get results for each of the provided keywords
        # (input_keyword , [((table, column), score)]
        for keyword in list_keywords:
            res = attr_similar_to(keyword, 30, True)
            all_res.append((keyword, res))

        # Group by tables, and include the (kw, score) that matched
        group_by_table_keyword = dict()
        for (keyword, res) in all_res:
            for (n, score) in res:
                (fname, cname) = n
                if fname not in group_by_table_keyword:
                    group_by_table_keyword[fname] = []
                included = False
                for kw, score in group_by_table_keyword[fname]:
                    if keyword.lower() == kw.lower():
                        included = True  # don't include more than once
                if not included:
                    group_by_table_keyword[fname].append((keyword, score))
                else:
                    continue

        # Create final output
        toreturn = sorted(group_by_table_keyword.items(),
                          key=lambda x: len(x[1]),
                          reverse=True)
        return toreturn[:topk]

    def columns_of_table(self, table):
        '''
        Returns all columns of the given table
        '''
        columns = []
        for k, v in cgraph_cache.items():
            fn, cn = k
            if fn == table:
                columns.append(cn)
        return columns

    def may_join_path(self, table1, table2, maxdepth):
        '''
        Given two tables and max depth returns join paths if exist
        '''
        def is_join_path_included(joinpaths, joinpath):
            first_joinpath = joinpath[0]
            last_joinpath = joinpath[len(joinpath) - 1]
            for jp in joinpaths:
                first_jp = jp[0]
                last_jp = jp[len(jp) - 1]
                if first_jp == first_joinpath and last_jp == last_joinpath:
                    return True
            return False

        def parent_of(fname, cname, visited):
            for column, parent in visited:
                fn, cn = column
                if fn == fname and cn == cname:
                    return parent

        # get columns from tables
        cols1 = DB_adapted_API.columns_of_table(self, table1)
        cols1 = [(table1, c) for c in cols1]

        #print("all columns of the first table")
        #for c in cols1:
        #    print(str(c))

        # comparison structure
        # [(colname, parentcol)]
        # keep intermediate structure to
        visited = []
        visiting = [(c, None) for c in cols1]

        it = 0
        while maxdepth > 0:
            #print("IT: " + str(it))
            #it = it + 1
            #print("VISITING: ")
            #for v in visiting:
            #    print(str(v))
            # create temporal structure for joins
            neighbors = []
            # go through visiting and get new joins
            for son, father in visiting:
                joins = []
                try:
                    joins = DB_adapted_API.columns_like(self, son)
                except KeyError:
                    continue
                # prepare these in the right format
                joins = [(j, son) for j in joins if j != son]
                #print("JOINS to: " + str(son))
                #print (str(joins))
                # extend neighbors with these
                neighbors.extend(joins)
            #print("visiting: " + str(son))
            #print(str(neighbors))
            # push visiting to visited and neighbors to visiting
            visited.extend(visiting)
            visiting = neighbors
            maxdepth = maxdepth - 1
        visited.extend(visiting)

        #print("VISITED:")
        #for v in visited:
        #    print(str(visited))

        # does any col1 join cols2
        joinpaths = []
        for column, parent in visited:
            joinpath = []
            fname, cname = column
            if fname == table2:
                joinpath.append(column)
                found_root = False
                while not found_root:
                    p = parent_of(fname, cname, visited)
                    pfname, pcname = p
                    joinpath.append(p)
                    if pfname == table1:
                        found_root = True
                    else:
                        fname, cname = pfname, pcname
                # Check for repetition
                if not is_join_path_included(joinpaths, joinpath):
                    joinpaths.append(joinpath)

        return joinpaths

    def join_path(self, table1, table2, maxdepth):
        '''
        Given two tables and max depth returns join paths if exist
        '''
        def is_join_path_included(joinpaths, joinpath):
            first_joinpath = joinpath[0]
            last_joinpath = joinpath[len(joinpath) - 1]
            for jp in joinpaths:
                first_jp = jp[0]
                last_jp = jp[len(jp) - 1]
                if first_jp == first_joinpath and last_jp == last_joinpath:
                    return True
            return False

        def parent_of(fname, cname, visited):
            for column, parent in visited:
                fn, cn = column
                if fn == fname and cn == cname:
                    return parent

        # get columns from tables
        cols1 = DB_adapted_API.columns_of_table(self, table1)
        cols1 = [(table1, c) for c in cols1]

        #print("all columns of the first table")
        #for c in cols1:
        #    print(str(c))

        # comparison structure
        # [(colname, parentcol)]
        # keep intermediate structure to
        visited = []
        visiting = [(c, None) for c in cols1]

        it = 0
        while maxdepth > 0:
            #print("IT: " + str(it))
            #it = it + 1
            #print("VISITING: ")
            #for v in visiting:
            #    print(str(v))
            # create temporal structure for joins
            neighbors = []
            # go through visiting and get new joins
            for son, father in visiting:
                joins = []
                try:
                    joins = DB_adapted_API.columns_joinable_with(self, son)
                except KeyError:
                    continue
                # prepare these in the right format
                joins = [(j, son) for j in joins if j != son]
                #print("JOINS to: " + str(son))
                #print (str(joins))
                # extend neighbors with these
                neighbors.extend(joins)
            #print("visiting: " + str(son))
            #print(str(neighbors))
            # push visiting to visited and neighbors to visiting
            visited.extend(visiting)
            visiting = neighbors
            maxdepth = maxdepth - 1
        visited.extend(visiting)

        #print("VISITED:")
        #for v in visited:
        #    print(str(visited))

        # does any col1 join cols2
        joinpaths = []
        for column, parent in visited:
            joinpath = []
            fname, cname = column
            if fname == table2:
                joinpath.append(column)
                found_root = False
                while not found_root:
                    p = parent_of(fname, cname, visited)
                    pfname, pcname = p
                    joinpath.append(p)
                    if pfname == table1:
                        found_root = True
                    else:
                        fname, cname = pfname, pcname
                # Check for repetition
                if not is_join_path_included(joinpaths, joinpath):
                    joinpaths.append(joinpath)

        return joinpaths

    def print(self, results):
        print_result(results)

    def entity_complement(table_to_enrich, tables):
        '''
        Given a table of reference (table_to_enrich) it uses information from
        other available tables (tables) to add entities
        '''
        print("TODO")

    def schema_complement(table_to_enrich, tables):
        '''
        Given a table of reference (table_to_enrich) it uses information from
        other available tables (tables) to enrich the schema
        '''
        print("TODO")

    def reduce_to_view(tables):
        '''
        Given a bunch of tables it tries a best-effort approach to reconcile
        them into the minimum number of tables. Naively, it tries to enrich each
        individual table until it reduces the total number
        '''
        print("TODO")

# Instantiate class to make it importable
p = DB_adapted_API()


def attr_similar_to(keyword, topk, score):
    '''
    Returns k most similar (levenhstein) attributes to the 
    one provided
    '''
    # TODO: handle multiple input keywords
    similarity_map = dict()
    kw = keyword.lower()
    for (fname, cname) in concepts:
        p = cname.lower()
        p_tokens = p.split(' ')
        for tok in p_tokens:
            # compute similarity and put in dict if beyond a
            distance = editdistance.eval(kw, tok)
            # minimum threshold
            if distance < C.max_distance_schema_similarity:
                similarity_map[(fname, cname)] = distance
                break  # to avoid potential repetitions
    sorted_sim_map = sorted(similarity_map.items(),
                            key=operator.itemgetter(1))
    if score:
        return sorted_sim_map[:topk]
    else:
        noscore_res = [n for (n, score) in sorted_sim_map[:topk]]
        return noscore_res


def format_output_for_webclient_ss(raw_output, consider_col_sel):
    '''
    Format raw output into something client understands.
    The output in this case is the result of a table search.
    '''
    def get_repr_columns(fname, columns, consider_col_sel):
        def set_selected(c):
            if consider_col_sel:
                if c in columns:
                    return 'Y'
            return 'N'
        # Get all columns of fname
        allcols = p.columns_of_table(fname)
        for myc in columns:
            allcols.append(myc)
        colsrepr = []
        for c in allcols:
            colrepr = {
                'colname': c,
                'samples': p.peek((fname, c), 15),
                'selected': set_selected(c)
            }
            colsrepr.append(colrepr)
        return colsrepr

    entries = []

    # Create entry per filename
    #for fname, columns in group_by_file.items():
    for fname, column_scores in raw_output:
        columns = [c for (c, _) in column_scores]
        entry = {'filename': fname,
                 'schema': get_repr_columns(
                     fname,
                     columns,
                     consider_col_sel)
                 }
        entries.append(entry)
    return entries


def format_output_for_webclient(raw_output, consider_col_sel):
    '''
    Format raw output into something client understands,
    mostly, enrich the data with schema and samples
    '''
    def get_repr_columns(fname, columns, consider_col_sel):
        def set_selected(c):
            if consider_col_sel:
                if c in columns:
                    return 'Y'
            return 'N'
        # Get all columns of fname
        allcols = p.columns_of_table(fname)
        colsrepr = []
        for c in allcols:
            colrepr = {
                'colname': c,
                # ['fake1', 'fake2'], p.peek((fname, c), 15),
                'samples': p.peek((fname, c), 15),
                'selected': set_selected(c)
            }
            colsrepr.append(colrepr)
        return colsrepr

    entries = []
    # Group results into a dict with file -> [column]
    group_by_file = dict()
    for (fname, cname) in raw_output:
        if fname not in group_by_file:
            group_by_file[fname] = []
        group_by_file[fname].append(cname)
    # Create entry per filename
    for fname, columns in group_by_file.items():
        entry = {'filename': fname,
                 'schema': get_repr_columns(
                     fname,
                     columns,
                     consider_col_sel)
                 }
        entries.append(entry)
    return entries


def get_dataset_files(dataset_path):
    '''
        Get all non-hidden files in a given directory
    '''
    files = iod.get_files_in_dir(dataset_path)
    print("Dataset with: " + str(len(files)) + " files")
    return files


def get_dataset_columns_from_files(files):
    ''' 
        Extracts all columns from dataset provided as 
        list of filepaths 
    '''
    #global dataset_columns
    cols = iod.get_column_iterator_csv(files)
    dataset_columns = process_columns_types(cols)
    print("Extracted " +
          str(len(dataset_columns.items())) +
          " columns")
    return dataset_columns


def clean_column(column):
    '''
    TODO: will become a complex process, move to a dif module
    '''
    clean_c = dict()
    column_type = None
    (key, value) = column
    # column may be null in some cases, change it if so
    (fname, cname) = key
    if cname == None:
         cname = "None"
         key = (fname, cname)
    if utils.is_column_num(value):
        newvalue = utils.cast_list_to_float(value)
        clean_c[key] = newvalue
        column_type = 'N'
    else:
        clean_c[key] = value
        column_type = 'T'
    return (clean_c, column_type)


def process_columns_types(cols):
    toret = dict()
    for col in cols.items():
        (clean_c, column_type) = clean_column(col)
        toret.update(clean_c)
    return toret


def dataset_columns(path):
    '''
       Parses all files in the path and return columns in the dataset 
    '''
    files = get_dataset_files(path)
    columns = get_dataset_columns_from_files(files)
    return columns


def show_columns_of(filename, dataset_columns):
    '''
        Returns the columns of a given file
    '''
    columns = []
    for (fname, cname) in dataset_columns.keys():
        if fname == filename:
            columns.append(cname)
    return columns


def get_column(filename, columname, dataset_columns):
    ''' 
        Return the column values
    '''
    key = (filename, columname)
    if key in dataset_columns:
        return dataset_columns[key]


def get_signature_for(column, method):
    ''' 
        Return the distribution for the indicated column,
        according to the provided method
    '''
    return da.get_column_signature(column, method)


def get_jsignature_for(fileA, columnA, fileB, columnB, method):
    '''
        Return the joint signature for the indicated columns
    '''
    columnA = dataset_columns[(fileA, columnA)]
    columnB = dataset_columns[(fileB, columnB)]
    if utils.is_column_num(columnA) and utils.is_column_num(columnB):
        return jsa.get_jsignature(columnA, columnB, method)
    else:
        print("Column types not supported")


def get_similarity_columns(columnA, columnB, method):
    '''
        Return similarity metric given a method (ks)
    '''
    if method == "ks":
        return da.compare_num_columns_dist_ks(columnA, columnB)
    elif method == "odsvm":
        return da.compare_num_columns_dist_odsvm(columnA, columnB)


def pairs_similar_to_pair(X, Y, method):
    '''
        Given two columns, it finds a jsignature for them and then 
        returns all pairs with similar score.
    '''
    (fileA, columnA) = X
    (fileB, columnB) = Y
    jsig = get_jsignature_for(fileA, columnA, fileB, columnB, method)
    if jsig is False:
        print("Could not compute joint signature for the provided columns")
        return False
    return pairs_similar_to_jsig(jsig, method)


def pairs_similar_to_jsig(jsignature, method):
    '''
        Return all pairs whose jsignature is similar to the provided.
    '''
    return jsa.get_similar_pairs(jsignature, dataset_columns, method)


def columns_similar_to_jsig(filename, column, jsignature, method):
    '''
        Return columns similar to the given joint signature
    '''
    key = (filename, column)
    column_data = dataset_columns[key]
    sim = jsa.get_columns_similar_to_jsignature(
        column_data,
        jsignature,
        dataset_columns,
        method)
    return sim


def columns_similar_to_DBCONN(concept):
    '''
    Iterate over entire db to find similar cols
    '''
    sim_cols = []
    (c_type, sig) = MS.get_fields_from_concept(concept,
                                               "type",
                                               "signature")
    if c_type is 'N':
        ncol_cursor = MS.get_all_num_cols_for_comp()
        for el in ncol_cursor:
            are_sim = da.compare_pair_num_columns(sig,
                                                  el["signature"])
            if are_sim:
                key = (el["filename"], el["column"])
                sim_cols.append(key)
    elif c_type is 'T':
        tcol_cursor = MS.get_all_text_cols_for_comp()
        for el in tcol_cursor:
            are_sim = da.compare_pair_text_columns(sig,
                                                   el["signature"])
            if are_sim:
                key = (el["filename"], el["column"])
                sim_cols.append(key)
    return sim_cols


def columns_similar_to(filename, column, similarity_method):
    '''
        Return columns similar to the provided one,
        according to some notion of similarity
    '''
    key = (filename, column)
    sim_vector = None
    sim_columns = []
    if key in ncol_dist:  # numerical
        #print("Numerical search")
        if similarity_method is "ks":
            sim_items = da.get_sim_items_ks(key, ncol_dist)
            sim_columns.extend(sim_items)
    elif key in tcol_dist:  # text
        #print("Textual search")
        sim_vector = da.get_sim_vector_text(key, tcol_dist)
        for (filekey, sim) in sim_vector.items():
            #print(str(sim) + " > " + str(C.cosine["threshold"]))
            if sim > C.cosine["threshold"]:  # right threshold?
                sim_columns.append(filekey)
    return sim_columns


def neighbors_of(concept, cgraph):
    '''
        Returns all concepts that are neighbors
        of concept
    '''
    return cg.give_neighbors_of(concept, cgraph)


def give_structural_sim_of(concept):
    '''
        Returns all concepts that are similar (structure)
        to concept after a given threshold
    '''
    return cg.give_structural_sim_of(concept, cgraph, simrank)


def analyze_dataset(list_path, signature_method, modelname):
    ''' Gets files from directory, columns from 
        dataset, and distribution for each column 
    '''
    all_files_in_dir = iod.get_files_in_dir(list_path)
    print("FILES:")
    for f in all_files_in_dir:
        print(str(f))
    print("Processing " + str(len(all_files_in_dir)) + " files")
    st = now()
    global dataset_columns
    dataset_columns = get_dataset_columns_from_files(all_files_in_dir)
    et = now()
    t_to_extract_cols = str(et - st)

    # Form graph skeleton
    st = now()
    global cgraph
    cgraph = cg.build_graph_skeleton(list(dataset_columns.keys()),
                                     cgraph)
    et = now()
    t_to_build_graph_skeleton = str(et - st)

    # Store dataset info in mem
    st = now()
    global ncol_dist
    global tcol_dist
    (ncol_dist, tcol_dist) = da.get_columns_signature(
        dataset_columns,
        signature_method)
    et = now()
    t_to_extract_signatures = str(et - st)
    # Refine concept graph
    st = now()
    cgraph = cg.refine_graph_with_columnsignatures(
        ncol_dist,
        tcol_dist,
        cgraph
    )
    et = now()
    t_to_refine_graph = str(et - st)
    st = now()
    global simrank
    simrank = sr.simrank(cgraph, C.sr_maxiter, C.sr_eps, C.sr_c)
    et = now()
    t_to_simrank = str(et - st)
    print("Took: " + t_to_extract_cols + "ms to extract columns")
    print("Took: " + t_to_build_graph_skeleton + "ms to build cgraph skeleton")
    print("Took: " + t_to_extract_signatures +
          "ms to extract column signatures")
    print("Took: " + t_to_refine_graph + "ms to refine concept graph")
    print("Took: " + t_to_simrank + "ms to compute simrank")
    return (ncol_dist, tcol_dist)


def store_precomputed_model(modelname):
    '''
    Store dataset columns, signature collection (2 files) and
    graph
    '''
    print("Storing signatures...")
    serde.serialize_signature_collection(tcol_dist,
                                         ncol_dist,
                                         modelname)
    print("Storing signatures...DONE!")
    print("Storing graph...")
    serde.serialize_graph(cgraph, modelname)
    print("Storing graph...DONE!")
    print("Storing simrank matrix...")
    serde.serialize_simrank_matrix(simrank, modelname)
    print("Storing simrank matrix...DONE!")
    print("Storing dataset columns...")
    serde.serialize_dataset_columns(dataset_columns, modelname)
    print("Storing dataset columns...DONE!")


def load_precomputed_model_DBVersion(modelname):
    print("Loading (cache) graph...")
    global cgraph_cache
    cgraph_cache = serde.deserialize_cached_graph(modelname)
    print("Loading (cache) graph...DONE!")
    print("Loading graph...")
    global cgraph
# lsh - nolsh
    #cgraph = serde.deserialize_graph(modelname)
    print("Loading graph...DONE!")
    print("Loading jgraph...")
    global jgraph
# lsh - nolsh
    #jgraph = serde.deserialize_jgraph(modelname)
    print("Loading jgraph...DONE!")
    print("Loading simrank matrix...")

    #global simrank
    #simrank = serde.deserialize_simrank_matrix(modelname)
    #print("Loading simrank matrix...DONE!")

    # Initialize the model DB
    MS.init(modelname)
    global concepts
    print("Loading concepts for schema primitives...")
    concepts = MS.get_all_concepts()
    print("Loading concepts for schema primitives...DONE")


def load_precomputed_model(modelname):
    print("Loading signature collections...")
    global tcol_dist
    global ncol_dist
    (tcol_dist, ncol_dist) = serde.deserialize_signature_collections(modelname)
    print("Loading signature collections...DONE!")
    print("Loading graph...")
    global cgraph
    cgraph = serde.deserialize_graph(modelname)
    print("Loading graph...DONE!")
    print("Loading simrank matrix...")
    global simrank
    simrank = serde.deserialize_simrank_matrix(modelname)
    print("Loading simrank matrix...DONE!")
    print("Loading dataset columns...")
    global dataset_columns
    dataset_columns = serde.deserialize_dataset_columns(modelname)
    print("Loading dataset columns...DONE!")


def process_files(files, signature_method, similarity_method):
    dataset_columns = get_dataset_columns_from_files(files)

    (ncol_dist, tcol_dist) = da.get_columns_signature(
        dataset_columns,
        signature_method)
    sim_matrix_num = da.get_sim_matrix_numerical(
        ncol_dist,
        similarity_method
    )
    sim_matrix_text = da.get_sim_matrix_text(tcol_dist)
    print("")
    print("Similarity for numerical columns")
    utils.print_dict(sim_matrix_num)
    print("")
    print("Similarity for textual columns")
    utils.print_dict(sim_matrix_text)


def print_result(result):
    from IPython.display import Markdown, display

    def printmd(string):
        display(Markdown(string))
    grouped_by_dataset = dict()
    for dataset, column in result:
        if dataset not in grouped_by_dataset:
            grouped_by_dataset[dataset] = []
        grouped_by_dataset[dataset].append(column)
    for key, value in grouped_by_dataset.items():
        printmd("**" + str(key) + "**")
        for v in value:
            print("   " + str(v))


def main():
    # Parse input parameters
    mode = sys.argv[1]
    arg = sys.argv[2]
    signature_method = sys.argv[3]
    similarity_method = sys.argv[4]
    # Container for files to parse
    files = []
    if mode == "-p":
        print('Working on path: ' + str(arg))
        all_files_in_dir = iod.get_files_in_dir(arg)
        for f in all_files_in_dir:
            print(str(f))
        files.extend(all_files_in_dir)
    elif mode == "-f":
        print('Working on file: ' + str(arg))
        files.append(arg)
    print("Processing " + str(len(files)) + " files")
    process_files(files, signature_method, similarity_method)


if __name__ == "__main__":
    if len(sys.argv) is not 5:
        print("HELP")
        print("-p  <path> to directory with CSV files")
        print("-f  <path> to CSV file")
        print("USAGE")
        print("python main.py -p/-f <path> " +
              "<numerical_signature_method> \
                <numerical_similarity_method>")
        exit()
    main()
