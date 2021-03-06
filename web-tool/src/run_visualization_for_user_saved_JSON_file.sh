#!/bin/bash
# --------------------------------------------------------------
# This script runs Visualization for the user saved JSON file
# --------------------------------------------------------------
#
USER_SAVED_JSON_DIR=$1
USER_SAMPLE=$2
USER_RESULT_DIR="$USER_SAVED_JSON_DIR/visualize_results_$USER_SAMPLE"
mkdir $USER_RESULT_DIR
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
#
#
# Copy the style_master to the visualize_results_rundir/
#
cp $SCRIPT_DIR/style_master.js $USER_RESULT_DIR/style.js
#
#
# Run Python code to extract min and max values from graph_json.json, to create the style.js code, 
# and to process the graph.js.
#
python $SCRIPT_DIR/create_style_code_for_visualization.py $USER_RESULT_DIR $USER_SAVED_JSON_DIR

# Make the HTML file that contains JavaScript code using the cytoscape.js library to be user-specific in that directory,
# so the HTML can be linked to a domain name and the user can access the weblink for their result
cp $SCRIPT_DIR/visualize_user_saved_JSON_file_with_CytoscapeJS_lib.html $USER_RESULT_DIR/visualize_OmicsIntegrator_results_with_CytoscapeJS_lib_$USER_SAMPLE.html

