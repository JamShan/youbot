# minors.py - functions for computing minors of graphs
#
# Copyright 2015 Jeffrey Finkelstein <jeffrey.finkelstein@gmail.com>.
# Copyright 2010 Drew Conway <drew.conway@nyu.edu>
# Copyright 2010 Aric Hagberg <hagberg@lanl.gov>
#
# This file is part of NetworkX.
#
# NetworkX is distributed under a BSD license; see LICENSE.txt for more
# information.
"""Provides functions for computing minors of a graph."""
from itertools import chain
from itertools import combinations
from itertools import permutations
from itertools import product

import networkx as nx
from networkx import density
from networkx.exception import NetworkXException
from networkx.utils import arbitrary_element

__all__ = ['contracted_edge', 'contracted_nodes',
           'identified_nodes', 'quotient_graph', 'blockmodel']

chaini = chain.from_iterable


def equivalence_classes(iterable, relation):
    """Returns the set of equivalence classes of the given `iterable` under
    the specified equivalence relation.

    `relation` must be a Boolean-valued function that takes two argument. It
    must represent an equivalence relation (that is, the relation induced by
    the function must be reflexive, symmetric, and transitive).

    The return value is a set of sets. It is a partition of the elements of
    `iterable`; duplicate elements will be ignored so it makes the most sense
    for `iterable` to be a :class:`set`.

    """
    # For simplicity of implementation, we initialize the return value as a
    # list of lists, then convert it to a set of sets at the end of the
    # function.
    blocks = []
    # Determine the equivalence class for each element of the iterable.
    for y in iterable:
        # Each element y must be in *exactly one* equivalence class.
        #
        # Each block is guaranteed to be non-empty
        for block in blocks:
            x = arbitrary_element(block)
            if relation(x, y):
                block.append(y)
                break
        else:
            # If the element y is not part of any known equivalence class, it
            # must be in its own, so we create a new singleton equivalence
            # class for it.
            blocks.append([y])
    return {frozenset(block) for block in blocks}


def quotient_graph(G, partition, edge_relation=None, node_data=None,
                   edge_data=None, relabel=False, create_using=None):
    """Returns the quotient graph of `G` under the specified equivalence
    relation on nodes.

    Parameters
    ----------
    G : NetworkX graph
        The graph for which to return the quotient graph with the
        specified node relation.

    partition : function or list of sets
        If a function, this function must represent an equivalence
        relation on the nodes of `G`. It must take two arguments *u*
        and *v* and return True exactly when *u* and *v* are in the
        same equivalence class. The equivalence classes form the nodes
        in the returned graph.

        If a list of sets, the list must form a valid partition of
        the nodes of the graph. That is, each node must be in exactly
        one block of the partition.

    edge_relation : Boolean function with two arguments
        This function must represent an edge relation on the *blocks* of
        `G` in the partition induced by `node_relation`. It must
        take two arguments, *B* and *C*, each one a set of nodes, and
        return True exactly when there should be an edge joining
        block *B* to block *C* in the returned graph.

        If `edge_relation` is not specified, it is assumed to be the
        following relation. Block *B* is related to block *C* if and
        only if some node in *B* is adjacent to some node in *C*,
        according to the edge set of `G`.

    edge_data : function
        This function takes two arguments, *B* and *C*, each one a set
        of nodes, and must return a dictionary representing the edge
        data attributes to set on the edge joining *B* and *C*, should
        there be an edge joining *B* and *C* in the quotient graph (if
        no such edge occurs in the quotient graph as determined by
        `edge_relation`, then the output of this function is ignored).

        If the quotient graph would be a multigraph, this function is
        not applied, since the edge data from each edge in the graph
        `G` appears in the edges of the quotient graph.

    node_data : function
        This function takes one argument, *B*, a set of nodes in `G`,
        and must return a dictionary representing the node data
        attributes to set on the node representing *B* in the quotient graph.
        If None, the following node attributes will be set:

        * 'graph', the subgraph of the graph `G` that this block
          represents,
        * 'nnodes', the number of nodes in this block,
        * 'nedges', the number of edges within this block,
        * 'density', the density of the subgraph of `G` that this
          block represents.

    relabel : bool
        If True, relabel the nodes of the quotient graph to be
        nonnegative integers. Otherwise, the nodes are identified with
        :class:`frozenset` instances representing the blocks given in
        `partition`.

    create_using : NetworkX graph
        If specified, this must be an instance of a NetworkX graph
        class. The nodes and edges of the quotient graph will be added
        to this graph and returned. If not specified, the returned graph
        will have the same type as the input graph.

    Returns
    -------
    NetworkX graph
        The quotient graph of `G` under the equivalence relation
        specified by `partition`. If the partition were given as a
        list of :class:`set` instances and `relabel` is False,
        each node will be a :class:`frozenset` corresponding to the same
        :class:`set`.

    Raises
    ------
    NetworkXException
        If the given partition is not a valid partition of the nodes of
        `G`.

    Examples
    --------
    The quotient graph of the complete bipartite graph under the "same
    neighbors" equivalence relation is `K_2`. Under this relation, two nodes
    are equivalent if they are not adjacent but have the same neighbor set::

        >>> import networkx as nx
        >>> G = nx.complete_bipartite_graph(2, 3)
        >>> same_neighbors = lambda u, v: (u not in G[v] and v not in G[u]
        ...                                and G[u] == G[v])
        >>> Q = nx.quotient_graph(G, same_neighbors)
        >>> K2 = nx.complete_graph(2)
        >>> nx.is_isomorphic(Q, K2)
        True

    The quotient graph of a directed graph under the "same strongly connected
    component" equivalence relation is the condensation of the graph (see
    :func:`condensation`). This example comes from the Wikipedia article
    *`Strongly connected component`_*::

        >>> import networkx as nx
        >>> G = nx.DiGraph()
        >>> edges = ['ab', 'be', 'bf', 'bc', 'cg', 'cd', 'dc', 'dh', 'ea',
        ...          'ef', 'fg', 'gf', 'hd', 'hf']
        >>> G.add_edges_from(tuple(x) for x in edges)
        >>> components = list(nx.strongly_connected_components(G))
        >>> sorted(sorted(component) for component in components)
        [['a', 'b', 'e'], ['c', 'd', 'h'], ['f', 'g']]
        >>>
        >>> C = nx.condensation(G, components)
        >>> component_of = C.graph['mapping']
        >>> same_component = lambda u, v: component_of[u] == component_of[v]
        >>> Q = nx.quotient_graph(G, same_component)
        >>> nx.is_isomorphic(C, Q)
        True

    Node identification can be represented as the quotient of a graph under the
    equivalence relation that places the two nodes in one block and each other
    node in its own singleton block::

        >>> import networkx as nx
        >>> K24 = nx.complete_bipartite_graph(2, 4)
        >>> K34 = nx.complete_bipartite_graph(3, 4)
        >>> C = nx.contracted_nodes(K34, 1, 2)
        >>> nodes = {1, 2}
        >>> is_contracted = lambda u, v: u in nodes and v in nodes
        >>> Q = nx.quotient_graph(K34, is_contracted)
        >>> nx.is_isomorphic(Q, C)
        True
        >>> nx.is_isomorphic(Q, K24)
        True

    The blockmodeling technique described in [1]_ can be implemented as a
    quotient graph::

        >>> G = nx.path_graph(6)
        >>> partition = [{0, 1}, {2, 3}, {4, 5}]
        >>> M = nx.quotient_graph(G, partition, relabel=True)
        >>> list(M.edges())
        [(0, 1), (1, 2)]

    .. _Strongly connected component: https://en.wikipedia.org/wiki/Strongly_connected_component

    References
    ----------
    .. [1] Patrick Doreian, Vladimir Batagelj, and Anuska Ferligoj.
           *Generalized Blockmodeling*.
           Cambridge University Press, 2004.

    """
    # If the user provided an equivalence relation as a function compute
    # the blocks of the partition on the nodes of G induced by the
    # equivalence relation.
    if callable(partition):
        partition = equivalence_classes(G, partition)
    # Each node in the graph must be in exactly one block.
    if any(sum(1 for b in partition if v in b) != 1 for v in G):
        raise NetworkXException('each node must be in exactly one block')
    H = type(create_using)() if create_using is not None else type(G)()
    # By default set some basic information about the subgraph that each block
    # represents on the nodes in the quotient graph.
    if node_data is None:
        def node_data(b):
            S = G.subgraph(b)
            return dict(graph=S, nnodes=len(S), nedges=S.number_of_edges(),
                        density=density(S))
    # Each block of the partition becomes a node in the quotient graph.
    partition = [frozenset(b) for b in partition]
    H.add_nodes_from((b, node_data(b)) for b in partition)
    # By default, the edge relation is the relation defined as follows. B is
    # adjacent to C if a node in B is adjacent to a node in C, according to the
    # edge set of G.
    #
    # This is not a particularly efficient implementation of this relation:
    # there are O(n^2) pairs to check and each check may require O(log n) time
    # (to check set membership). This can certainly be parallelized.
    if edge_relation is None:
        def edge_relation(b, c):
            return any(v in G[u] for u, v in product(b, c))
    # By default, sum the weights of the edges joining pairs of nodes across
    # blocks to get the weight of the edge joining those two blocks.
    if edge_data is None:
        def edge_data(b, c):
            edgedata = (d for u, v, d in G.edges(b | c, data=True)
                        if (u in b and v in c) or (u in c and v in b))
            return {'weight': sum(d.get('weight', 1) for d in edgedata)}
    block_pairs = permutations(H, 2) if H.is_directed() else combinations(H, 2)
    # In a multigraph, add one edge in the quotient graph for each edge
    # in the original graph.
    if H.is_multigraph():
        edges = chaini(((b, c, G.get_edge_data(u, v, default={}))
                        for u, v in product(b, c) if v in G[u])
                       for b, c in block_pairs if edge_relation(b, c))
    # In a simple graph, apply the edge data function to each pair of
    # blocks to determine the edge data attributes to apply to each edge
    # in the quotient graph.
    else:
        edges = ((b, c, edge_data(b, c)) for (b, c) in block_pairs
                 if edge_relation(b, c))
    H.add_edges_from(edges)
    # If requested by the user, relabel the nodes to be integers,
    # numbered in increasing order from zero in the same order as the
    # iteration order of `partition`.
    if relabel:
        # Can't use nx.convert_node_labels_to_integers() here since we
        # want the order of iteration to be the same for backward
        # compatibility with the nx.blockmodel() function.
        labels = {b: i for i, b in enumerate(partition)}
        H = nx.relabel_nodes(H, labels)
    return H


def contracted_nodes(G, u, v, self_loops=True):
    """Returns the graph that results from contracting `u` and `v`.

    Node contraction identifies the two nodes as a single node incident to any
    edge that was incident to the original two nodes.

    Parameters
    ----------
    G : NetworkX graph
       The graph whose nodes will be contracted.

    u, v : nodes
       Must be nodes in `G`.

    self_loops : Boolean
       If this is True, any edges joining `u` and `v` in `G` become
       self-loops on the new node in the returned graph.

    Returns
    -------
    Networkx graph
       A new graph object of the same type as `G` (leaving `G` unmodified)
       with `u` and `v` identified in a single node. The right node `v`
       will be merged into the node `u`, so only `u` will appear in the
       returned graph.

    Examples
    --------
    Contracting two nonadjacent nodes of the cycle graph on four nodes `C_4`
    yields the path graph (ignoring parallel edges)::

        >>> import networkx as nx
        >>> G = nx.cycle_graph(4)
        >>> M = nx.contracted_nodes(G, 1, 3)
        >>> P3 = nx.path_graph(3)
        >>> nx.is_isomorphic(M, P3)
        True

    See also
    --------
    contracted_edge
    quotient_graph

    Notes
    -----
    This function is also available as `identified_nodes`.
    """
    H = G.copy()
    if H.is_directed():
        in_edges = ((w, u, d) for w, x, d in G.in_edges(v, data=True)
                    if self_loops or w != u)
        out_edges = ((u, w, d) for x, w, d in G.out_edges(v, data=True)
                     if self_loops or w != u)
        new_edges = chain(in_edges, out_edges)
    else:
        new_edges = ((u, w, d) for x, w, d in G.edges(v, data=True)
                     if self_loops or w != u)
    v_data = H.node[v]
    H.remove_node(v)
    H.add_edges_from(new_edges)
    if 'contraction' in H.node[u]:
        H.node[u]['contraction'][v] = v_data
    else:
        H.node[u]['contraction'] = {v: v_data}
    return H

identified_nodes = contracted_nodes


def contracted_edge(G, edge, self_loops=True):
    """Returns the graph that results from contracting the specified edge.

    Edge contraction identifies the two endpoints of the edge as a single node
    incident to any edge that was incident to the original two nodes. A graph
    that results from edge contraction is called a *minor* of the original
    graph.

    Parameters
    ----------
    G : NetworkX graph
       The graph whose edge will be contracted.

    edge : tuple
       Must be a pair of nodes in `G`.

    self_loops : Boolean
       If this is True, any edges (including `edge`) joining the
       endpoints of `edge` in `G` become self-loops on the new node in the
       returned graph.

    Returns
    -------
    Networkx graph
       A new graph object of the same type as `G` (leaving `G` unmodified)
       with endpoints of `edge` identified in a single node. The right node
       of `edge` will be merged into the left one, so only the left one will
       appear in the returned graph.

    Raises
    ------
    ValueError
       If `edge` is not an edge in `G`.

    Examples
    --------
    Attempting to contract two nonadjacent nodes yields an error::

        >>> import networkx as nx
        >>> G = nx.cycle_graph(4)
        >>> nx.contracted_edge(G, (1, 3))
        Traceback (most recent call last):
          ...
        ValueError: Edge (1, 3) does not exist in graph G; cannot contract it

    Contracting two adjacent nodes in the cycle graph on *n* nodes yields the
    cycle graph on *n - 1* nodes::

        >>> import networkx as nx
        >>> C5 = nx.cycle_graph(5)
        >>> C4 = nx.cycle_graph(4)
        >>> M = nx.contracted_edge(C5, (0, 1), self_loops=False)
        >>> nx.is_isomorphic(M, C4)
        True

    See also
    --------
    contracted_nodes
    quotient_graph

    """
    if not G.has_edge(*edge):
        raise ValueError('Edge {0} does not exist in graph G; cannot contract'
                         ' it'.format(edge))
    return contracted_nodes(G, *edge, self_loops=self_loops)


def blockmodel(G, partition, multigraph=False):
    """Returns a reduced graph constructed using the generalized block modeling
    technique.

    The blockmodel technique collapses nodes into blocks based on a
    given partitioning of the node set.  Each partition of nodes
    (block) is represented as a single node in the reduced graph.
    Edges between nodes in the block graph are added according to the
    edges in the original graph.  If the parameter multigraph is False
    (the default) a single edge is added with a weight equal to the
    sum of the edge weights between nodes in the original graph
    The default is a weight of 1 if weights are not specified.  If the
    parameter multigraph is True then multiple edges are added each
    with the edge data from the original graph.

    Parameters
    ----------
    G : graph
        A networkx Graph or DiGraph

    partition : list of lists, or list of sets
        The partition of the nodes.  Must be non-overlapping.

    multigraph : bool, optional
        If True return a MultiGraph with the edge data of the original
        graph applied to each corresponding edge in the new graph.
        If False return a Graph with the sum of the edge weights, or a
        count of the edges if the original graph is unweighted.

    Returns
    -------
    blockmodel : a Networkx graph object

    Examples
    --------
    >>> G = nx.path_graph(6)
    >>> partition = [[0,1],[2,3],[4,5]]
    >>> M = nx.blockmodel(G,partition)

    References
    ----------
    .. [1] Patrick Doreian, Vladimir Batagelj, and Anuska Ferligoj
           "Generalized Blockmodeling",Cambridge University Press, 2004.

    .. note:: Deprecated in NetworkX v1.11

        `blockmodel` will be removed in NetworkX 2.0. Instead use
        `quotient_graph` with keyword argument `relabel=True`, and
        `create_using=nx.MultiGraph()` for multigraphs.
    """
    if multigraph:
        return nx.quotient_graph(G, partition,
                                 create_using=nx.MultiGraph(), relabel=True)
    else:
        return nx.quotient_graph(G, partition, relabel=True)