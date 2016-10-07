from modelstore.elasticstore import StoreHandler

from modelstore.elasticstore import KWType

from api.apiutils import compute_field_id as id_from
from api.apiutils import Operation
from api.apiutils import OP
from api.apiutils import Scope
from api.apiutils import Relation
from api.apiutils import DRS
from api.apiutils import DRSMode
from api.apiutils import Hit


class Algebra:

    def __init__(self, network, store_client):
        self._network = network
        self._store_client = store_client

    """
    Basic API
    """

    def keyword_search(self, kw: str, scope: Scope, max_results=10) -> DRS:
        """
        Performs a keyword search over the contents of the data.
        Scope specifies where elasticsearch should be looking for matches.
        i.e. table titles (SOURCE), columns (FIELD), or comment (SOURCE)

        :param kw: the keyword to serch
        :param max_results: maximum number of results to return
        :return: returns a DRS
        """

        kw_type = self._scope_to_kw_type(scope)
        hits = self._store_client.search_keyword(
            keywords=kw, elasticfieldname=kw_type, max_results=max_results)

        # materialize generator
        drs = DRS([x for x in hits], Operation(OP.KW_LOOKUP, params=[kw]))
        return drs

    # def neighbor_search(self,
    #                     node_or_hit: (str, str, str),
    #                     relation: Relation,
    #                     max_hops=None):

    #     i_hit = self._node_or_hit_to_hit(node_or_hit)
    #     hits = self._network.neighbor_id(i_hit, relation)

    """
    Helper Functions
    """

    def _scope_to_kw_type(self, scope: Scope) -> KWType:
        """
        Converts a relation scope to a keyword type for elasticsearch.
        """
        kw_type = None
        if scope == Scope.DB:
            raise ValueError('DB Scope is not implemeneted')
        elif scope == Scope.SOURCE:
            kw_type = KWType.KW_TABLE
        elif scope == Scope.FIELD:
            kw_type = KWType.KW_SCHEMA
        elif scope == Scope.CONTENT:
            kw_type = KWType.KW_TEXT

        return kw_type

    def _general_to_drs(self, general_input) -> DRS:
        """
        Given an nid, node, hit, or DRS and convert it to a DRS.
        :param nid: int
        :param node: (db_name, source_name, field_name)
        :param hit: Hit
        :param DRS: DRS
        :return: DRS
        """
        if isinstance(general_input, int):
            general_input = self._nid_to_hit(general_input)
        if isinstance(general_input, tuple):
            general_input = self._node_to_hit(general_input)
        if isinstance(general_input, Hit):
            general_input = self._hit_to_drs(general_input)
        if isinstance(general_input, DRS):
            return general_input
        else:
            raise ValueError(
                'Input is not an integer, field tuple, hit, or DRS')

    def _nid_to_hit(self, nid: int) -> Hit:
        """
        Given a node id, convert it to a Hit
        :param nid: int
        :return: DRS
        """
        nid, db, source, field = self._network.get_info_for([nid])
        hit = Hit(nid, db, source, field)
        return hit

    def _node_to_hit(self, node: (str, str, str)) -> Hit:
        """
        Given a field and source name, it returns a Hit with its representation
        :param node: a tuple with the name of the field,
            (db_name, source_name, field_name)
        :return: Hit
        """
        db, source, field = node
        nid = id_from(db, source, field)
        hit = Hit(nid, db, source, field, 0)
        return hit

    def _hit_to_drs(self, hit: Hit) -> DRS:
        """
        Given a Hit, return a DRS
        :param hit: Hit
        :return: DRS
        """
        drs = DRS([hit], Operation(OP.ORIGIN))
        return drs


class API(Algebra):
    def __init__(self, *args, **kwargs):
        super(API, self).__init__(*args, **kwargs)


if __name__ == '__main__':
    print("Aurum API")
