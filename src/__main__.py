#!/usr/bin/env python3

# Core python modules
import sys, os

# Peripheral python modules
import argparse

import pandas as pd
import numpy as np
import networkx as nx

# import this module
# from . import Graph, output_networkx_graph_as_graphml_for_cytoscape, output_networkx_graph_as_json_for_cytoscapejs
from graph import Graph, output_networkx_graph_as_graphml_for_cytoscape, output_networkx_graph_as_json_for_cytoscapejs, output_networkx_graph_as_pickle, get_networkx_graph_as_node_edge_dataframes, get_networkx_subgraph_from_randomizations

parser = argparse.ArgumentParser(description="""
	Find multiple pathways within an interactome that are altered in a particular condition using
	the Prize Collecting Steiner Forest problem.""")

class FullPaths(argparse.Action):
	"""Expand user- and relative-paths"""
	def __call__(self,parser, namespace, values, option_string=None):
		setattr(namespace, self.dest, os.path.abspath(os.path.expanduser(values)))

def directory(dirname):
	if not os.path.isdir(dirname): raise argparse.ArgumentTypeError(dirname + " is not a directory")
	else: return dirname

# Input / Output parameters:
io_params = parser.add_argument_group("Input / Output Files")

io_params.add_argument("-e", "--edge", dest='edge_file', type=str, required=True,
	help ='(Required) Path to the text file containing the edges. Should be a tab delimited file (no header) with 3 columns: "nodeA\tnodeB\tcost"')
io_params.add_argument("-p", "--prize", dest='prize_file', type=str, required=True,
	help='(Required) Path to the text file containing the prizes. Should be a tab delimited file (*with* header) with lines: "nodeName(tab)prize"')
io_params.add_argument('-o', '--output', dest='output_dir', action=FullPaths, type=directory, required=True,
	help='(Required) Output directory path')

# Command parameters (specify what the algorithm does):
pcsf_params = parser.add_argument_group("PCSF Parameters")

pcsf_params.add_argument("-w", dest="w", nargs="*", type=float, required=False, default=[6],
	help="Omega: the weight of the edges connecting the dummy node to the nodes selected by dummyMode [default: 6]")
pcsf_params.add_argument("-b", dest="b", nargs="*", type=float, required=False, default=[1],
	help="Beta: scaling factor of prizes [default: 1]")
pcsf_params.add_argument("-g", dest="g", nargs="*", type=float, required=False, default=[20],
	help="Gamma: multiplicative edge penalty from degree of endpoints [default: 20]")
pcsf_params.add_argument("-noise", dest="noise", type=float, required=False, default=0.1,
	help="Standard Deviation of the gaussian noise added to edges in Noisy Edges Randomizations [default: 0.1]")

pcsf_params.add_argument("--noisy_edges", dest='noisy_edges_repetitions', type=int, default=0,
	help='An integer specifying how many times you would like to add noise to the given edge values and re-run the algorithm. Results of these runs will be merged together and written in files with the word "_noisy_edges_" added to their names. The noise level can be controlled using the configuration file. [default: 0]')
pcsf_params.add_argument("--random_terminals", dest='random_terminals_repetitions', type=int, default=0,
	help='An integer specifying how many times you would like to apply your given prizes to random nodes in the interactome (with a similar degree distribution) and re-run the algorithm. Results of these runs will be merged together and written in files with the word "_random_terminals_" added to their names. [default: 0]')
pcsf_params.add_argument("--knockout", dest='knockout', nargs='*', default=[],
	help='Protein(s) you would like to "knock out" of the interactome to simulate a knockout experiment. [default: []]')

pcsf_params.add_argument("--dummyMode", dest='dummy_mode', choices=("terminals", "other", "all"), required=False,
	help='Tells the program which nodes in the interactome to connect the dummy node to. "terminals"= connect to all terminals, "others"= connect to all nodes except for terminals, "all"= connect to all nodes in the interactome. [default: terminals]')
pcsf_params.add_argument("--excludeTerminals", action='store_true', dest='exclude_terminals', required=False,
	help='Flag to exclude terminals when calculating negative prizes. Use if you want terminals to keep exact assigned prize regardless of degree. [default: False]')
pcsf_params.add_argument("-s", "--seed", dest='seed', type=int, required=False,
	help='An integer seed for the pseudo-random number generators. If you want to reproduce exact results, supply the same seed. [default: None]')


def output_dataframe_to_tsv(dataframe, output_dir, filename):
	"""
	Output the dataframe to a csv.
	"""

	path = os.path.join(os.path.abspath(output_dir), filename)
	dataframe.to_csv(path, sep='\t', header=True, index=False)


def output_networkx_graph_as_files(nxgraph, project_dir, tag, subfolder=""): 
	"""
	Output networkx graph in various formats.
	"""

	os.makedirs(os.path.abspath(project_dir), exist_ok=True)
	output_dir = os.path.join(os.path.abspath(project_dir), subfolder)


	nxgraph_nodes_df, nxgraph_edges_df = get_networkx_graph_as_node_edge_dataframes(nxgraph)

	output_networkx_graph_as_pickle(nxgraph, output_dir, tag+".gpickle")
	output_dataframe_to_tsv(nxgraph_nodes_df, output_dir, tag+".nodes.tsv")
	output_dataframe_to_tsv(nxgraph_edges_df, output_dir, tag+".edges.tsv")
	output_networkx_graph_as_json_for_cytoscapejs(nxgraph, output_dir, "{}.{}.json".format(tag, subfolder.replace("/", "")))

	return output_dir


def get_summary_statistics_from_nxgraph(nxgraph, tag):

	nxgraph_nodes_df, nxgraph_edges_df = get_networkx_graph_as_node_edge_dataframes(nxgraph)

	steiners = nxgraph_nodes_df[nxgraph_nodes_df["type"] == "steiner"]
	prizes = nxgraph_nodes_df[nxgraph_nodes_df["type"] != "steiner"]

	num_all, num_steiner, num_prizes = nxgraph_nodes_df.shape[0], steiners.shape[0], prizes.shape[0]
	logDeg_all, logDeg_steiner, logDeg_prizes = np.log(nxgraph_nodes_df["degree"]).mean(), np.log(steiners["degree"]).mean(), np.log(prizes["degree"]).mean()
	connected_components = nx.nx.number_connected_components(nxgraph)
	singletons = len([len(x) for x in nx.connected_components(nxgraph) if len(x) == 1])

	return [tag, num_all, num_steiner, num_prizes, logDeg_all, logDeg_steiner, logDeg_prizes, connected_components, singletons]



def main():

	args = parser.parse_args()

	params = {"w":args.w, "b":args.b, "g":args.g, "noise":args.noise, "dummy_mode":args.dummy_mode, "exclude_terminals":args.exclude_terminals, "seed":args.seed,
			  "noisy_edges_repetitions": args.noisy_edges_repetitions, "random_terminals_repetitions": args.random_terminals_repetitions}
	params = {param: value for param, value in params.items() if value is not None}

	graph = Graph(args.edge_file, {})

	# Parameter search
	results = graph.grid_search_randomizations(args.prize_file, params)
	summary_stats = []

	for tag, forest, augmented_forest in results: 

		if augmented_forest.number_of_nodes() > 0: 

			if params["noisy_edges_repetitions"] == params["random_terminals_repetitions"] == 0: 
				# For single test runs
				output_networkx_graph_as_files(forest, args.output_dir, tag, subfolder="forest")
				summary_stats.append(get_summary_statistics_from_nxgraph(forest, tag))

			else: 
				# For randomizations
				robust_network = get_networkx_subgraph_from_randomizations(augmented_forest, max_size=400)

				output_networkx_graph_as_files(augmented_forest, args.output_dir, tag, subfolder="augmented_forest")
				output_networkx_graph_as_files(robust_network,   args.output_dir, tag, subfolder="robust_network")

		else: 

			print("{} is empty, results not printed.".format(tag))

	if len(summary_stats) > 0: 

		stats_df = pd.DataFrame(summary_stats, columns=["tag", "n_all", "n_steiner", "n_prizes", "logDeg_all", "logDeg_steiner", "logDeg_prizes", "n_components", "n_singletons"])
		stats_df.sort_values(by=["n_singletons", "n_all"], inplace=True)
		stats_df.to_csv(args.output_dir+"/summary_stats.tsv", sep='\t', index=False)


if __name__ == '__main__':
	main()