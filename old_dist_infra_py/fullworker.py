from celery import Celery
from celery import Task

import celeryconfig as CC
import api as API
import config as C
from dataanalysis import dataanalysis as da
from modelstore import mongomodelstore as MS
from inputoutput import inputoutput as iod

app = Celery('fullworker', backend=CC.CELERY_RESULT_BACKEND,
             broker=CC.BROKER_URL)


@app.task()
def init_worker(dbname):
    MS.init(dbname, create_index=True)
    print("Initialized db: " + str(dbname))


@app.task()
def load_tables(batch_of_tasks):
    '''
    Loads each of the data columns in concepts, then 
    create a type-dependent signature, stores all data 
    in the store and sends the signature to the coordinator.  
    '''
    colsigs = []
    for task in batch_of_tasks:
        (source_input_type, arg, t) = task
        columns = []
        if source_input_type == "db":
            columns = iod.get_columns_from_db(t, arg)
        elif source_input_type == "csvfiles":
            columns = iod.get_columns_from_csv_file(t)
        # Limit values per column to max
        max_value = C.max_values_per_column
        for (k, v) in columns.items():
            v = v[:max_value]
            columns[k] = v

        for column in columns.items():
            # basic preprocess and clean columns
            #print(str(column[1]))
            (clean_c, c_type) = API.clean_column(column)
            values = list(clean_c.values())[0]
            #print(str(len(values)))
            (f_name, c_name) = list(clean_c.keys())[0]
            num_data = []
            text_data = []
            sig = None
            if c_type is 'N':
                # num signature
                method = C.preferred_num_method
                #sig = da.get_num_dist(values, method)
                sig = da.get_numerical_signature(values, C.sig_v_size)
                num_data = values
            elif c_type is 'T':
                # text signature
                method = C.preferred_text_method
                #sig = da.get_textual_dist(values, method)
                sig = da.get_textual_signature(values, C.sig_v_size)
                text_data = values
            # Load info to model store
            MS.new_column(f_name,
                          c_name,
                          c_type,
                          sig,
                          num_data,
                          text_data)
            key = (f_name, c_name)
            colsig = (key, c_type, sig)
            colsigs.append(colsig)
        #print("Processed signatures for: " + str(f_name))
    return colsigs
